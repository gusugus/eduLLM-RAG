#!/usr/bin/env python
import sys
from pathlib import Path
from core.logging_config import setup_logging
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService
from services.indexer_service import IndexerService
from loguru import logger
import argparse

# Obtener la raíz del proyecto buscando el archivo main.py
def get_project_root():
    current = Path(__file__).resolve()
    # Sube hasta encontrar main.py o llegar a /
    while current != current.parent:
        if (current / "main.py").exists():
            return current
        current = current.parent
    raise RuntimeError("No se encontró main.py en la jerarquía")

PROJECT_ROOT = get_project_root()
sys.path.insert(0, str(PROJECT_ROOT))  # Añadir al path



def get_default_json_path():
    return str(PROJECT_ROOT / "corpus" / "secciones_completas.json")

def main():
    parser = argparse.ArgumentParser(description="Cargar secciones a Qdrant")
    parser.add_argument("--json", default=get_default_json_path(), help="Ruta del archivo JSON")
    parser.add_argument("--recreate", action="store_true", default=True)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        logger.error(f"Archivo no encontrado: {json_path}")
        sys.exit(1)

    setup_logging()
    logger.info(f"Raíz del proyecto: {PROJECT_ROOT}")
    logger.info(f"Cargando desde: {json_path}")

    qdrant = QdrantService()
    embedder = EmbeddingService()
    indexer = IndexerService(qdrant, embedder)
    indexer.load_from_json(str(json_path), args.recreate, args.batch_size)

if __name__ == "__main__":
    main()