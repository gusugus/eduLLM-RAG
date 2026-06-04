[← Volver al índice](INDEX.md)

# Dependencias — RAG Service

Este documento detalla las librerías externas utilizadas por el servicio y su propósito dentro del sistema.

---

## Dependencias de Producción

Todas las dependencias están especificadas en [requirements.txt](file:///home/gusgus/Documentos/rag/requirements.txt).

| Dependencia | Versión mínima/específica | Propósito |
|-------------|----------------------------|-----------|
| `fastapi` | Reciente | Framework web de alto rendimiento para exponer los endpoints REST. |
| `uvicorn` | Reciente | Servidor ASGI rápido que ejecuta la aplicación FastAPI. |
| `qdrant-client[fastembed]` | Reciente | Cliente oficial de Qdrant. La especificación `[fastembed]` incluye la librería para generar embeddings semánticos localmente. |
| `pyyaml` | Reciente | Parser para leer el archivo de configuración `config.yml`. |
| `loguru` | Reciente | Librería para la escritura limpia y estructurada de logs locales. |
| `pywebguard` | `>=1.0.26` | Middleware de seguridad para FastAPI que implementa whitelist/blacklist de IP y control de flujo/tasa (rate limiting). |
| `structlog` | `>=24.1.0` | Logging estructurado avanzado para producción. |

---

## Telemetría y Observabilidad (OpenTelemetry)

Se utilizan las siguientes dependencias de OpenTelemetry para capturar métricas, logs y trazas distribuidas, enviándolos al colector de Grafana Alloy:

| Dependencia | Versión específica | Propósito |
|-------------|---------------------|-----------|
| `opentelemetry-distro` | `0.48b0` | Distribución base para iniciar OpenTelemetry en aplicaciones Python. |
| `opentelemetry-sdk` | `1.27.0` | Kit de desarrollo de software para configurar trazadores y proveedores de telemetría. |
| `opentelemetry-exporter-otlp-proto-http` | `1.27.0` | Exportador para enviar señales OTLP a través de peticiones HTTP POST (JSON/Protobuf). |
| `opentelemetry-exporter-otlp-proto-grpc` | `1.27.0` | Exportador para enviar trazas y logs de alto rendimiento vía gRPC (hacia Alloy en `alloy:4317`). |
| `opentelemetry-instrumentation-fastapi` | `0.48b0` | Instrumentación automática para interceptar peticiones entrantes/salientes de FastAPI. |
| `opentelemetry-instrumentation-logging` | `0.48b0` | Instrumentación para inyectar IDs de trazas dentro del sistema de logs nativo de Python. |
| `opentelemetry-semantic-conventions` | `0.48b0` | Definición de atributos estandarizados según la especificación OpenTelemetry. |

---

## Última revisión

- **Fecha:** 2026-05-24
- **Commit:** `5cfbd82`

## Instrucciones para actualizar este doc

- Si añades o eliminas una línea en `requirements.txt`, actualiza esta tabla indicando su propósito.
- Si se actualizan las versiones críticas de OpenTelemetry, refleja los cambios aquí.
- Si cambia la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
