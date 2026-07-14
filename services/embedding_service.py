from fastembed import TextEmbedding
from loguru import logger
from core.config import settings

class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            logger.info(f"Cargando modelo de embeddings: {settings.embedding_model_name}")
            self.model = TextEmbedding(model_name=settings.embedding_model_name)
            self._initialized = True

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para una lista de textos. Retorna lista de vectores."""
        return [list(vec) for vec in self.model.embed(texts)]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]