# services/indexer_service.py
import json
import uuid
from pathlib import Path
from qdrant_client.models import PointStruct
from loguru import logger
from .embedding_service import EmbeddingService
from .qdrant_service import QdrantService

class IndexerService:
    def __init__(self, qdrant_service: QdrantService, embedding_service: EmbeddingService):
        self.qdrant = qdrant_service
        self.embedder = embedding_service

    def load_from_json(self, json_path: str, recreate_collection: bool = True, batch_size: int = 100):
        """Carga datos desde un archivo JSON a Qdrant"""
        
        json_file = Path(json_path)
        if not json_file.exists():
            raise FileNotFoundError(f"No se encuentra el archivo: {json_file.absolute()}")
        
        logger.info(f"Cargando datos desde {json_file.absolute()}")
        
        # Recrear colección si se solicita
        if recreate_collection:
            if self.qdrant.collection_exists():
                self.qdrant.delete_collection()
                logger.info("Colección eliminada para recreación")
            
            # Obtener tamaño del vector con un texto de prueba
            test_embedding = self.embedder.embed_one("test")
            vector_size = len(test_embedding)
            self.qdrant.create_collection(vector_size=vector_size)
            logger.info(f"Colección recreada con tamaño {vector_size}")
        
        # Cargar datos
        with open(json_file, 'r', encoding='utf-8') as f:
            secciones = json.load(f)
        
        points = []
        for sec in secciones:
            texto_indexable = f"{sec['titulo']}\n{sec.get('texto_completo', '')}"
            if sec.get('resumen'):
                texto_indexable += f"\nResumen: {sec['resumen']}"
            
            embedding = self.embedder.embed_one(texto_indexable)
            
            payload = {
                "document": texto_indexable,
                "codigo": sec.get('codigo', ''),
                "titulo": sec.get('titulo', ''),
                "keywords_nlp": sec.get('metadatos', {}).get('palabras_clave_nlp', []),
                "topic_id": sec.get('topic_id', -1),
                "curriculum_tema": sec.get('curriculum', {}).get('tema', ''),
                "curriculum_seccion": sec.get('curriculum', {}).get('seccion', ''),
                "curriculum_conceptos_seleccionados": sec.get('curriculum', {}).get('conceptos_seleccionados', [])
            }
            
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            ))
        
        # Insertar en lotes
        self.qdrant.upsert_points(points, batch_size=batch_size)
        logger.success(f"Carga completada: {len(points)} puntos insertados")