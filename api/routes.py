# api/routes.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from core.models import QueryRequest, ResultItem, TemaSubtemas, TemaQueryRequest, SubtemaQueryRequest, DocumentoItem, SubtemaDocumentos
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from services.indexer_service import IndexerService
from typing import List, Optional, Dict
from pathlib import Path
from pydantic import BaseModel
import os
from fastapi import Header, HTTPException, status
from core.config import settings  # Importar settings directamente
from qdrant_client.models import Filter, FieldCondition, MatchValue, MinShould
import logging
from typing import List, Dict, Set
from fastapi import Depends, HTTPException

router = APIRouter()

logger = logging.getLogger(__name__)


# Obtener raíz del proyecto buscando main.py
def get_project_root():
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / "main.py").exists():
            return current
        current = current.parent
    return Path("/app")  # fallback para Docker

PROJECT_ROOT = get_project_root()

# Modelo para la petición de carga
class LoadRequest(BaseModel):
    json_path: Optional[str] = None  # Si es None, usa el default
    recreate: bool = True
    batch_size: int = 100

# API Key para proteger el endpoint (configurable por variable de entorno)
API_KEY = os.getenv("ADMIN_API_KEY", "")


# Dependencias
def get_embedding_service():
    return EmbeddingService()

def get_qdrant_service():
    return QdrantService()

def get_indexer_service(
    qdrant: QdrantService = Depends(get_qdrant_service),
    embedder: EmbeddingService = Depends(get_embedding_service)
):
    return IndexerService(qdrant, embedder)

# ============ ENDPOINTS DE BÚSQUEDA ============

@router.post("/query", response_model=List[ResultItem])
async def query_rag(
    request: QueryRequest,
    embedder: EmbeddingService = Depends(get_embedding_service),
    qdrant: QdrantService = Depends(get_qdrant_service)
):
    if not request.text.strip():
        logger.warning("Petición con texto vacío")
        raise HTTPException(status_code=400, detail="Texto de consulta vacío")

    logger.debug(f"Consulta: {request.text[:50]}...")

    query_vector = embedder.embed_one(request.text)
    results = qdrant.search(vector=query_vector, limit=request.n_results)

    filtered_results = [r for r in results if r.score >= request.min_score]

    if not filtered_results:
        logger.warning(f"No hay resultados que cumplan el umbral mínimo de similitud (min_score={request.min_score})")
        raise HTTPException(status_code=400, detail="No hay resultados que cumplan el umbral mínimo de similitud")

    return [
        ResultItem(
            id=str(r.id),
            document=r.payload.get("document", ""),
            metadata={k: v for k, v in r.payload.items() if k != "document"},
            score=r.score
        ) for r in filtered_results
    ]

@router.get("/health")
async def health(qdrant: QdrantService = Depends(get_qdrant_service)):
    info = qdrant.get_collection_info()
    return {
        "status": "ok",
        "collection": qdrant.collection_name,
        "points": info.points_count
    }

@router.get("/temas", response_model=List[TemaSubtemas])
async def listar_temas(qdrant: QdrantService = Depends(get_qdrant_service)):
    records = qdrant.scroll_all()
    temas_dict: Dict[str, set] = {}
    for r in records:
        tema = r.payload.get("curriculum_tema", "") or ""
        conceptos = r.payload.get("curriculum_conceptos_seleccionados", []) or []
        if not tema:
            continue
        if tema not in temas_dict:
            temas_dict[tema] = set()
        for c in conceptos:
            if c:
                temas_dict[tema].add(c)
    return [
        TemaSubtemas(tema=t, subtemas=sorted(list(s)))
        for t, s in sorted(temas_dict.items())
    ]




@router.post("/query-by-subtema", response_model=List[SubtemaDocumentos])
async def query_by_subtema(
    request: SubtemaQueryRequest,
    qdrant: QdrantService = Depends(get_qdrant_service) ):
    try:
        if not request.subtemas:
            raise HTTPException(status_code=400, detail="Lista de subtemas vacía")

        filter_obj = Filter(
            should=[
                FieldCondition(key="curriculum_conceptos_seleccionados", match=MatchValue(value=sub))
                for sub in request.subtemas
            ],
            min_should=MinShould(
            conditions=[
                FieldCondition(key="curriculum_conceptos_seleccionados", match=MatchValue(value=sub))
                for sub in request.subtemas
            ],
            min_count=1
        )
        )

        records = qdrant.scroll_with_filter(filter_obj)

        subtema_docs: Dict[str, list] = {sub: [] for sub in request.subtemas}
        assigned_ids: Set[str] = set()

        for point in records:
            doc_id = str(point.id)
            if doc_id in assigned_ids:
                continue

            concepts = point.payload.get("curriculum_conceptos_seleccionados", []) or []
            for sub in request.subtemas:
                if sub in concepts:
                    subtema_docs[sub].append(DocumentoItem(
                        id=doc_id,
                        document=point.payload.get("document", "")
                    ))
                    assigned_ids.add(doc_id)
                    break

        return [
            SubtemaDocumentos(subtema=sub, documentos=subtema_docs[sub])
            for sub in request.subtemas
        ]

    except HTTPException as http_exc:
        # Relanzar las HTTPException que nosotros mismos creamos (como la de subtemas vacíos)
        raise http_exc
    except Exception as e:
        logger.error(f"Error en query-by-subtema: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar los documentos por subtema"
        )

# ============ FUNCIÓN DE BACKGROUND ============

async def run_load_task(indexer: IndexerService, json_path: str, recreate: bool, batch_size: int):
    """
    Tarea asíncrona que ejecuta la carga real en segundo plano
    """
    try:
        logger.info(f"🔃 [Background] Iniciando carga desde {json_path}")
        
        indexer.load_from_json(
            json_path=json_path,
            recreate_collection=recreate,
            batch_size=batch_size
        )
        
        logger.success(f"✅ [Background] Carga completada exitosamente desde {json_path}")
        
    except Exception as e:
        logger.error(f"❌ [Background] Error en carga: {str(e)}")
        # Aquí podrías enviar una notificación, guardar en base de datos, etc.