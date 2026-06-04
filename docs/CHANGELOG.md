[← Volver al índice](INDEX.md)

# Registro de Cambios (Changelog) — RAG Service

Todos los cambios notables realizados en este proyecto serán documentados en este archivo. El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/).

---

## [1.2.0] - 2026-05-21

### Añadido
- Integración completa con **OpenTelemetry** para el envío de trazas y logs estructurados al colector de Grafana Alloy mediante OTLP/gRPC en el puerto `4317`.
- Inclusión del middleware de seguridad `pywebguard` en `main.py` para control de flujo (`rate limiting`), filtrado de IPs (whitelist/blacklist) y detección básica de penetración (XSS, inyección SQL).
- Endpoint administrativo `/api/rag/admin/info` para consulta de diagnóstico sobre la conexión con Qdrant y el estado de los archivos del corpus.
- Workflow en GitHub Actions `.github/workflows/telegram-notify.yml` para enviar notificaciones en tiempo real a Telegram en eventos de Pull Request (apertura, cierre y solicitud de revisiones).

### Cambiado
- Refactorización completa de la arquitectura a un **diseño modular por capas** (`api/`, `core/`, `services/`), separando las responsabilidades de enrutamiento HTTP, la inicialización de configuraciones y la lógica de negocio (embeddings, indexador y base de datos vectorial).
- Uso de FastEmbed integrado directamente con `qdrant-client` para la generación local de embeddings con el modelo `BAAI/bge-small-en-v1.5`.

---

## [1.1.0] - 2026-05-19

### Añadido
- Documentación inicial técnica y guías detalladas para desarrolladores.
- Soporte para contenedores Docker con `Dockerfile` y configuración multicontenedor con `docker-compose.yml` para levantar la API de RAG y el servidor Qdrant.

---

## [1.0.0] - 2026-05-12

### Añadido
- Estructura básica de la aplicación Flask/FastAPI para responder consultas iniciales RAG.
- Script de carga inicial para ingerir el archivo del corpus de biología (`corpus/secciones_completas.json`) a Qdrant.

---

## Última revisión

- **Fecha:** 2026-05-24
- **Commit:** `5cfbd82`

## Instrucciones para actualizar este doc

- Cada vez que completes un cambio o una tarea relevante en el código, añade una línea en la versión correspondiente o crea una nueva sección de versión.
- Sigue las categorías estándar: `Añadido`, `Cambiado`, `Deprecado`, `Eliminado`, `Corregido`, `Seguridad`.
- Si cambia la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
