# RAG EduLLM

Microservicio de búsqueda semántica (**RAG — Retrieval-Augmented Generation**) para contenido educativo de Biología.  
Parte del ecosistema **EduLLM / MindBuzz**.

> **El servicio no genera texto.** Solo recupera los fragmentos de contenido más relevantes para inyectarlos en el prompt de un LLM. La generación la hace el modelo de lenguaje.

---

## Stack Tecnológico

| Capa | Tecnología | Versión / Detalle |
|---|---|---|
| **Framework web** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) | Python 3.11, servidor ASGI |
| **Base de datos vectorial** | [Qdrant](https://qdrant.tech/) | Imagen Docker `qdrant/qdrant:latest` |
| **Embeddings** | [fastembed](https://github.com/qdrant/fastembed) — `BAAI/bge-small-en-v1.5` | 384 dimensiones, ONNX, sin GPU |
| **Seguridad** | [pywebguard](https://pypi.org/project/pywebguard/) ≥1.0.26 | Rate limiting, IP filtering, protección anti-penetración |
| **Observabilidad** | [OpenTelemetry](https://opentelemetry.io/) SDK 1.27.0 | Trazas + logs → Grafana Alloy (OTLP/gRPC) |
| **Logging** | [Loguru](https://github.com/Delgan/loguru) + [structlog](https://www.structlog.org/) | Rotación automática, consola + archivo |
| **Infraestructura** | Docker + Docker Compose | Orquestación de `rag-api` + `qdrant-server` |
| **CI/CD** | GitHub Actions | Notificaciones Telegram en PRs |

---

## Requisitos Previos

- [Docker](https://docs.docker.com/get-docker/) instalado y corriendo
- [Docker Compose](https://docs.docker.com/compose/install/) (incluido en Docker Desktop)
- Red Docker `observability-net` creada manualmente (para telemetría):
  ```bash
  docker network create observability-net
  ```
- Python 3.11+ (solo para scripts de carga local, no necesario en producción)

---

## Inicio Rápido

### 1. Levantar el sistema completo

```bash
docker compose up --build -d
```

Esto construye la imagen del servicio RAG y levanta:
- `qdrant-server` en el puerto `6333`
- `rag-api` en el puerto `8002`

### 2. Cargar el contenido educativo (primera vez)

El sistema incluye un endpoint admin para cargar datos sin salir del contenedor:

```bash
curl -X POST http://localhost:8002/admin/load \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mi-clave-secreta-para-cargar-datos" \
  -d '{"recreate": true, "batch_size": 100}'
```

> **Alternativa CLI:** También puedes cargar datos con el script:
> ```bash
> docker compose exec rag-api python scripts/load_to_qdrant.py
> ```

### 3. Verificar que funciona

```bash
# Healthcheck
curl http://localhost:8002/health
# → {"status":"ok","collection":"rag_biologia","points":142}

# Consulta de prueba
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"text": "clasificación de los seres vivos", "n_results": 3}'
```

---

## Uso Normal (día a día)

```bash
# Levantar
docker compose up -d

# Detener
docker compose down
```

---

## Estructura del Proyecto

```
rag/
├── main.py                     # Punto de entrada: FastAPI app + middlewares + telemetría
├── config.yml                  # Configuración de Qdrant, embeddings y logging
├── requirements.txt            # Dependencias Python
├── Dockerfile                  # Imagen Docker (python:3.11-slim)
├── docker-compose.yml          # Orquestación: rag-api + qdrant-server
│
├── api/                        # Capa de presentación (endpoints)
│   ├── __init__.py
│   └── routes.py               # Endpoints: /query, /health, /admin/*
│
├── core/                       # Configuración y modelos transversales
│   ├── __init__.py
│   ├── config.py               # Clase Settings (YAML + env vars)
│   ├── logging_config.py       # Setup de Loguru
│   └── models.py               # Schemas Pydantic (QueryRequest, ResultItem)
│
├── services/                   # Lógica de negocio
│   ├── __init__.py
│   ├── embedding_service.py    # Singleton — genera embeddings con fastembed
│   ├── qdrant_service.py       # Cliente Qdrant (CRUD de colecciones y puntos)
│   └── indexer_service.py      # Orquesta carga JSON → embeddings → Qdrant
│
├── scripts/                    # Utilidades CLI
│   └── load_to_qdrant.py       # Script de carga independiente (argparse)
│
├── corpus/                     # Datos fuente
│   └── secciones_completas.json  # Contenido educativo (84 KB, ~142 secciones)
│
├── qdrant_storage/             # Volumen persistente de Qdrant (NO editar)
├── logs/                       # Logs con rotación automática
│
└── .github/
    └── workflows/
        └── telegram-notify.yml # Notificaciones Telegram para PRs
```

---

## Endpoints de la API

**Base URL:** `http://localhost:8002`

### Endpoints Públicos

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/query` | Busca fragmentos relevantes por texto |
| `GET` | `/health` | Estado del servicio y conteo de vectores |

### Endpoints de Administración (requieren `X-API-Key`)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/admin/load` | Carga datos desde JSON a Qdrant (background task) |
| `GET` | `/admin/load/status` | Estado del endpoint de carga |
| `GET` | `/admin/info` | Info del sistema: paths, Qdrant, corpus |

> Ver [DOCUMENTACION.md](DOCUMENTACION.md) para detalles completos de request/response de cada endpoint.

---

## Puertos

| Servicio | Puerto Host | Puerto Interno | Protocolo |
|---|---|---|---|
| RAG API (FastAPI) | `8002` (solo localhost) | `8000` | HTTP/REST |
| Qdrant REST | `6333` | `6333` | HTTP/REST ([Dashboard](http://localhost:6333/dashboard)) |
| Qdrant gRPC | `6334` | `6334` | gRPC |

---

## Variables de Entorno

Las variables de entorno **sobreescriben** los valores de `config.yml`.

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `QDRANT_HOST` | `qdrant-server` | Host del servidor Qdrant |
| `QDRANT_PORT` | `6333` | Puerto REST de Qdrant |
| `COLLECTION_NAME` | `rag_biologia` | Nombre de la colección vectorial |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Modelo de embeddings |
| `ADMIN_API_KEY` | `mi-clave-secreta-para-cargar-datos` | API key para endpoints admin |
| `CONFIG_PATH` | `config.yml` | Ruta al archivo de configuración |

> ⚠️ **Cambiar `ADMIN_API_KEY` en producción** — el valor por defecto es solo para desarrollo.

---

## Documentación Adicional

| Documento | Contenido |
|---|---|
| [DOCUMENTACION.md](DOCUMENTACION.md) | Documentación técnica completa: arquitectura, API detallada, modelo de datos, flujos, extensibilidad |
| [wiki_github.md](wiki_github.md) | Contenido para la Wiki de GitHub (5 páginas) |

---

## Licencia

Proyecto open-source del ecosistema EduLLM.