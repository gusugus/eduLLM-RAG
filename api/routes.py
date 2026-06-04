# api/routes.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from core.models import QueryRequest, ResultItem
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from services.indexer_service import IndexerService
from loguru import logger
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel
import os
from fastapi import Header, HTTPException, status
from core.config import settings  # Importar settings directamente

router = APIRouter()

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
API_KEY = os.getenv("ADMIN_API_KEY", "mi-clave-secreta-para-cargar-datos")

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

    return [
        ResultItem(
            id=str(r.id),
            document=r.payload.get("document", ""),
            metadata={k: v for k, v in r.payload.items() if k != "document"},
            score=r.score
        ) for r in results
    ]

@router.get("/health")
async def health(qdrant: QdrantService = Depends(get_qdrant_service)):
    info = qdrant.get_collection_info()
    return {
        "status": "ok",
        "collection": qdrant.collection_name,
        "points": info.points_count
    }

@router.get("/admin/info")
async def admin_info(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")  # ← Opcional
):
    """
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o no proporcionada"
        )
    """
    qdrant_service = get_qdrant_service()
    collection_info = qdrant_service.get_collection_info()
    
    return {
        "project_root": str(PROJECT_ROOT),
        "qdrant": {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
            "collection": qdrant_service.collection_name,
            "points_count": collection_info.points_count
        },
        "default_corpus": {
            "path": str(PROJECT_ROOT / "corpus" / "secciones_completas.json"),
            "exists": (PROJECT_ROOT / "corpus" / "secciones_completas.json").exists()
        }
    }

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