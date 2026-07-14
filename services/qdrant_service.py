from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MinShould
import logging
from core.config import settings
from typing import List, Dict, Any, Optional
logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=False
        )
        self.collection_name = settings.collection_name
        logger.info(f"Conectado a Qdrant en {settings.qdrant_host}:{settings.qdrant_port}")

    def collection_exists(self) -> bool:
        return self.client.collection_exists(self.collection_name)

    def create_collection(self, vector_size: int = 384):
        if self.collection_exists():
            logger.warning(f"La colección {self.collection_name} ya existe. No se crea.")
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        logger.info(f"Colección '{self.collection_name}' creada con tamaño {vector_size}")

    def delete_collection(self):
        if self.collection_exists():
            self.client.delete_collection(self.collection_name)
            logger.info(f"Colección '{self.collection_name}' eliminada")

    def upsert_points(self, points: List[PointStruct], batch_size: int = 100):
        total = len(points)
        for i in range(0, total, batch_size):
            batch = points[i:i+batch_size]
            self.client.upsert(collection_name=self.collection_name, points=batch)
            logger.debug(f"Subidos {min(i+batch_size, total)}/{total} puntos")
        logger.info(f"Upsert completado: {total} puntos")

    def search(self, vector: List[float], limit: int = 5, with_payload: bool = True):
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            with_payload=with_payload
        ).points
        return results

    def scroll_with_filter(self, filter_obj: Filter, batch_size: int = 100):
        all_records = []
        next_offset = None
        while True:
            records, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
                scroll_filter=filter_obj,
            )
            all_records.extend(records)
            if next_offset is None:
                break
        return all_records

    def get_collection_info(self):
        return self.client.get_collection(self.collection_name)

    def scroll_all(self, batch_size: int = 100):
        all_records = []
        next_offset = None
        while True:
            records, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
            )
            all_records.extend(records)
            if next_offset is None:
                break
        return all_records