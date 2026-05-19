import os
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
from loguru import logger

# ---------- Configuración ----------
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yml")
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

QDRANT_HOST = os.getenv("QDRANT_HOST", config.get('qdrant', {}).get('host', 'localhost'))
QDRANT_PORT = int(os.getenv("QDRANT_PORT", config.get('qdrant', {}).get('port', 6333)))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", config.get('qdrant', {}).get('collection_name', 'rag_biologia'))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", config.get('embedding', {}).get('model_name', 'BAAI/bge-small-en-v1.5'))

# ---------- Configuración de logging con loguru ----------
log_config = config.get('logging', {})
log_level = log_config.get('level', 'INFO')
log_file = log_config.get('file')
log_rotation = log_config.get('rotation', '10 MB')
log_retention = log_config.get('retention', '30 days')
log_compression = log_config.get('compression', 'gz')
log_console = log_config.get('console', True)

# Eliminar configuración previa por defecto
logger.remove()
# Añadir salida a consola si se pide
if log_console:
    logger.add(lambda msg: print(msg, end=''), level=log_level, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
# Añadir archivo con rotación
if log_file:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(
        log_file,
        rotation=log_rotation,
        retention=log_retention,
        compression=log_compression,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}"
    )

logger.info(f"Iniciando servicio RAG con colección '{COLLECTION_NAME}' en {QDRANT_HOST}:{QDRANT_PORT}")

# ---------- Modelo de embeddings ----------
logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)

# ---------- Cliente Qdrant ----------
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, prefer_grpc=False)
try:
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    logger.info(f"Colección '{COLLECTION_NAME}' encontrada. Puntos: {collection_info.points_count}")
except Exception as e:
    logger.error(f"No se encontró la colección '{COLLECTION_NAME}': {e}")
    raise

# ---------- FastAPI ----------
app = FastAPI(title="RAG Service")

class QueryRequest(BaseModel):
    text: str
    n_results: int = 5

class ResultItem(BaseModel):
    id: str
    document: str
    metadata: dict
    score: float

@app.post("/query", response_model=List[ResultItem])
async def query_rag(request: QueryRequest):
    if not request.text.strip():
        logger.warning("Petición con texto vacío")
        raise HTTPException(status_code=400, detail="Texto de consulta vacío")
    
    logger.debug(f"Consulta: {request.text[:50]}...")
    
    # Generar embedding
    query_embedding = list(embedding_model.embed([request.text]))[0]
    
    # Búsqueda
    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        limit=request.n_results,
        with_payload=True
    ).points
    
    logger.info(f"Búsqueda exitosa: {len(results)} resultados")
    
    return [
        ResultItem(
            id=str(r.id),
            document=r.payload.get("document", "") if r.payload else "",
            metadata={k: v for k, v in r.payload.items() if k != "document"} if r.payload else {},
            score=r.score
    ) for r in results
]

@app.get("/health")
async def health():
    return {"status": "ok", "collection": COLLECTION_NAME, "points": collection_info.points_count}