import os
import yaml
from pathlib import Path

class Settings:
    def __init__(self):
        config_path = os.getenv("CONFIG_PATH", "config.yml")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Qdrant
        self.qdrant_host = os.getenv("QDRANT_HOST", config.get('qdrant', {}).get('host', 'localhost'))
        self.qdrant_port = int(os.getenv("QDRANT_PORT", config.get('qdrant', {}).get('port', 6333)))
        self.collection_name = os.getenv("COLLECTION_NAME", config.get('qdrant', {}).get('collection_name', 'rag_biologia'))

        # Embedding
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", config.get('embedding', {}).get('model_name', 'BAAI/bge-small-en-v1.5'))

        # Logging
        log_cfg = config.get('logging', {})
        self.log_level = log_cfg.get('level', 'INFO')
        self.log_file = log_cfg.get('file')
        self.log_rotation = log_cfg.get('rotation', '10 MB')
        self.log_retention = log_cfg.get('retention', '30 days')
        self.log_compression = log_cfg.get('compression', 'gz')
        self.log_console = log_cfg.get('console', True)

settings = Settings()