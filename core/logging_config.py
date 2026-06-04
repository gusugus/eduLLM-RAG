from loguru import logger
import sys
from .config import settings

def setup_logging():
    logger.remove()  # Remove default handler

    if settings.log_console:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
        )

    if settings.log_file:
        from pathlib import Path
        Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            settings.log_file,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression=settings.log_compression,
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}"
        )

    logger.info("Logging configurado correctamente")