# Documentación Técnica — RAG EduLLM

> **Repositorio:** `rag/`  
> **Propósito:** Microservicio de Retrieval-Augmented Generation (RAG) para contenido educativo de Biología. Expone una API REST que, dada una consulta en texto libre, devuelve los fragmentos más relevantes del material de estudio para inyectarlos en el prompt de un LLM.

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Estructura de Archivos](#3-estructura-de-archivos)
4. [Componentes Principales](#4-componentes-principales)
5. [API REST — Endpoints](#5-api-rest--endpoints)
6. [Modelo de Datos](#6-modelo-de-datos)
7. [Flujo de Datos](#7-flujo-de-datos)
8. [Seguridad](#8-seguridad)
9. [Observabilidad (OpenTelemetry)](#9-observabilidad-opentelemetry)
10. [Configuración y Variables de Entorno](#10-configuración-y-variables-de-entorno)
11. [Despliegue con Docker](#11-despliegue-con-docker)
12. [Dependencias](#12-dependencias)
13. [Cómo Extender el Sistema](#13-cómo-extender-el-sistema)
14. [CI/CD — GitHub Actions](#14-cicd--github-actions)
15. [Glosario](#15-glosario)

---

## 1. Visión General

Este repositorio implementa el **módulo de búsqueda semántica** de la plataforma educativa EduLLM/MindBuzz.

> Dado un texto de consulta, busca en Qdrant los fragmentos de contenido educativo más relevantes y los devuelve con su puntuación de similitud.

El servicio **no genera texto** — eso lo hace el LLM. Solo recupera contexto relevante.

**Stack tecnológico resumido:**

| Capa | Tecnología |
|---|---|
| Framework web | FastAPI + Uvicorn (Python 3.11) |
| Base vectorial | Qdrant (Docker) |
| Embeddings | fastembed — `BAAI/bge-small-en-v1.5` (384 dims, ONNX, sin GPU) |
| Seguridad | pywebguard (rate limiting, IP filtering) |
| Observabilidad | OpenTelemetry SDK → Grafana Alloy (OTLP/gRPC) |
| Logging | Loguru + structlog (rotación automática) |
| Infraestructura | Docker + Docker Compose |

---

## 2. Arquitectura del Sistema

```
                     ┌─────────────────────────────────────┐
                     │     Cliente / Proxy LLM Backend     │
                     └──────────────┬──────────────────────┘
                                    │ POST /query
                                    ▼
                ┌───────────────────────────────────────────┐
                │          main.py (FastAPI App)             │
                │                                           │
                │  Middlewares:                              │
                │   ├─ TrustedHostMiddleware                 │
                │   ├─ FastAPIGuard (pywebguard)             │
                │   └─ FastAPIInstrumentor (OpenTelemetry)   │
                │                                           │
                │  Router: api/routes.py                    │
                │   ├─ POST /query         (público)        │
                │   ├─ GET  /health        (público)        │
                │   ├─ POST /admin/load    (API key)        │
                │   ├─ GET  /admin/load/status (API key)    │
                │   └─ GET  /admin/info    (API key)        │
                └──────────────┬────────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼                     ▼
          ┌──────────────────┐  ┌──────────────────┐
          │ EmbeddingService │  │  QdrantService    │
          │ (fastembed)      │  │  (qdrant-client)  │
          │ Singleton        │  └────────┬──────────┘
          └──────────────────┘           │ HTTP :6333
                                         ▼
                              ┌──────────────────────┐
                              │   Qdrant Server      │
                              │   :6333 / :6334      │
                              │   Col: rag_biologia  │
                              │   384 dims (coseno)  │
                              └──────────────────────┘
```

Ambos servicios (`rag-api` y `qdrant-server`) corren como contenedores Docker orquestados por `docker-compose.yml`.

---

## 3. Estructura de Archivos

```
rag/
├── main.py                        ← App FastAPI + middlewares + telemetría
├── config.yml                     ← Config: Qdrant, embedding, logging
├── requirements.txt               ← Dependencias Python
├── Dockerfile                     ← Imagen (python:3.11-slim)
├── docker-compose.yml             ← Orquestación: rag-api + qdrant-server
│
├── api/                           ← Capa de presentación
│   ├── __init__.py
│   └── routes.py                  ← Todos los endpoints (query, health, admin)
│
├── core/                          ← Configuración y modelos
│   ├── __init__.py
│   ├── config.py                  ← Clase Settings (YAML + env vars)
│   ├── logging_config.py          ← Setup de Loguru
│   └── models.py                  ← Schemas Pydantic
│
├── services/                      ← Lógica de negocio
│   ├── __init__.py
│   ├── embedding_service.py       ← Singleton para generar embeddings
│   ├── qdrant_service.py          ← Cliente Qdrant (CRUD)
│   └── indexer_service.py         ← Orquesta: JSON → embeddings → Qdrant
│
├── scripts/
│   └── load_to_qdrant.py          ← Script CLI de carga (argparse)
│
├── corpus/
│   └── secciones_completas.json   ← Contenido educativo fuente (84 KB)
│
├── qdrant_storage/                ← Volumen persistente Qdrant (NO editar)
├── logs/                          ← Logs con rotación automática
│
└── .github/workflows/
    └── telegram-notify.yml        ← Notificaciones Telegram en PRs
```

---

## 4. Componentes Principales

### `main.py` — Punto de Entrada

Crea la app FastAPI y configura en orden:

1. **Logging** (`setup_logging()`) — Loguru con consola + archivo.
2. **Telemetría** (`configure_telemetry()`) — OpenTelemetry: trazas y logs → Alloy vía OTLP/gRPC en `alloy:4317`.
3. **Seguridad** — `FastAPIGuard` (pywebguard): IP whitelist, rate limiting (100 req/min, burst 20).
4. **Hosts confiables** — `TrustedHostMiddleware`: solo acepta `localhost`, `127.0.0.1`, `rag-api`, `auth-ms`, `*.internal.local`.
5. **Router** — Incluye `api/routes.py`.

### `core/config.py` — Settings

Clase `Settings` que lee `config.yml` y permite sobreescritura por variables de entorno.

```python
settings.qdrant_host           # QDRANT_HOST o config.yml → qdrant.host
settings.qdrant_port           # QDRANT_PORT o config.yml → qdrant.port
settings.collection_name       # COLLECTION_NAME o config.yml → qdrant.collection_name
settings.embedding_model_name  # EMBEDDING_MODEL o config.yml → embedding.model_name
settings.log_level             # config.yml → logging.level
settings.log_file              # config.yml → logging.file
```

### `core/models.py` — Schemas Pydantic

| Clase | Campos | Uso |
|---|---|---|
| `QueryRequest` | `text: str`, `n_results: int = 5` | Body de `POST /query` |
| `ResultItem` | `id: str`, `document: str`, `metadata: dict`, `score: float` | Cada resultado |

### `services/embedding_service.py` — EmbeddingService (Singleton)

- Carga `BAAI/bge-small-en-v1.5` una sola vez (patrón Singleton con `__new__`).
- `embed(texts)` → lista de vectores. `embed_one(text)` → un vector.
- Usa ONNX Runtime internamente (sin GPU, sin PyTorch).

### `services/qdrant_service.py` — QdrantService

Cliente wrapper de `qdrant-client`:
- `create_collection(vector_size)` — crea colección con distancia coseno.
- `delete_collection()` — elimina la colección.
- `upsert_points(points, batch_size)` — inserta vectores en lotes.
- `search(vector, limit)` — búsqueda por similitud (`query_points`).
- `get_collection_info()` — metadata de la colección (conteo de puntos, etc.).

### `services/indexer_service.py` — IndexerService

Orquesta la carga de datos:
1. Lee JSON de secciones.
2. Opcionalmente elimina y recrea la colección.
3. Construye texto indexable: `titulo + texto_completo + resumen`.
4. Genera embedding por sección.
5. Inserta en Qdrant en lotes.

### `api/routes.py` — Router

Gestiona todos los endpoints con inyección de dependencias (FastAPI `Depends`). Incluye:
- Endpoints públicos (`/query`, `/health`)
- Endpoints admin protegidos por API key (`/admin/load`, `/admin/load/status`, `/admin/info`)
- Background task para carga asíncrona de datos.

---

## 5. API REST — Endpoints

**Base URL:** `http://localhost:8002`

### `POST /query` — Búsqueda Semántica

**Request:**
```json
{
  "text": "¿Cómo se clasifica un organismo según la taxonomía de Linneo?",
  "n_results": 5,
  "min_score": 0.7
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `text` | `string` | ✅ | — | Texto de la consulta |
| `n_results` | `integer` | ❌ | `5` | Resultados a devolver |
| `min_score` | `float` | ❌ | `0.0` | Score mínimo de similitud (0.0–1.0) para filtrar resultados |

**Response `200`:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document": "Clasificación de los seres vivos\nLos seres vivos se clasifican...",
    "metadata": {
      "codigo": "SEC-001",
      "titulo": "Clasificación de los seres vivos",
      "keywords_nlp": ["reino", "filo", "clase"],
      "topic_id": 3,
      "curriculum_tema": "Unidad 1",
      "curriculum_seccion": "1.1",
      "curriculum_conceptos_seleccionados": ["taxonomía"]
    },
    "score": 0.87
  }
]
```

| Código | Causa |
|---|---|
| `400` | Texto vacío |
| `500` | Qdrant no disponible |

---

### `GET /health` — Estado del Servicio

**Response `200`:**
```json
{
  "status": "ok",
  "collection": "rag_biologia",
  "points": 142
}
```

---

### `POST /admin/load` — Cargar Datos (Admin)

Requiere header `X-API-Key`.

**Request:**
```json
{
  "json_path": null,
  "recreate": true,
  "batch_size": 100
}
```

| Campo | Default | Descripción |
|---|---|---|
| `json_path` | `corpus/secciones_completas.json` | Ruta al JSON (absoluta o relativa) |
| `recreate` | `true` | Si `true`, elimina y recrea la colección |
| `batch_size` | `100` | Tamaño de lote para upsert |

**Response `200`:**
```json
{
  "status": "loading_started",
  "message": "Carga iniciada desde /app/corpus/secciones_completas.json",
  "json_path": "/app/corpus/secciones_completas.json",
  "recreate": true,
  "batch_size": 100
}
```

> La carga se ejecuta como **background task**. Usar `/admin/load/status` o `/health` para verificar que completó.

**Ejemplo curl:**
```bash
curl -X POST http://localhost:8002/admin/load \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mi-clave-secreta-para-cargar-datos" \
  -d '{"recreate": true}'
```

---

### `GET /admin/load/status` — Estado de Carga (Admin)

Requiere `X-API-Key`. Retorna si el endpoint está disponible y si el archivo JSON por defecto existe.

### `GET /admin/info` — Info del Sistema (Admin)

Requiere `X-API-Key`. Retorna info del proyecto, Qdrant y corpus.

---

## 6. Modelo de Datos

### Sección (unidad mínima de conocimiento)

Cada sección en Qdrant:

```
PointStruct
├── id                              ← UUID (uuid.uuid4())
├── vector[384]                     ← Embedding BAAI/bge-small-en-v1.5
└── payload
    ├── document                    ← Texto indexable (titulo + cuerpo + resumen)
    ├── codigo                      ← ID único (ej: "SEC-001")
    ├── titulo                      ← Título legible
    ├── keywords_nlp                ← Palabras clave NLP
    ├── topic_id                    ← Clúster BERTopic
    ├── curriculum_tema             ← Tema curricular
    ├── curriculum_seccion          ← Sección del currículo
    └── curriculum_conceptos_seleccionados ← Conceptos del currículo
```

### Colección Qdrant

| Parámetro | Valor |
|---|---|
| Nombre | `rag_biologia` |
| Dimensiones | `384` |
| Distancia | Coseno |

### Formato del JSON fuente (`secciones_completas.json`)

```json
{
  "codigo": "SEC-001",
  "titulo": "Clasificación de los seres vivos",
  "texto_completo": "...",
  "resumen": "...",
  "metadatos": {
    "palabras_clave_nlp": ["reino", "filo"]
  },
  "topic_id": 3,
  "curriculum": {
    "tema": "Unidad 1",
    "seccion": "1.1",
    "conceptos_seleccionados": ["taxonomía"]
  }
}
```

---

## 7. Flujo de Datos

### Indexación (carga de contenido)

```
corpus/secciones_completas.json
        │
        ▼
IndexerService.load_from_json()
        │
        ├─ Para cada sección:
        │   ├─ texto = titulo + texto_completo + resumen
        │   ├─ EmbeddingService.embed_one(texto) → vector[384]
        │   └─ PointStruct(id=UUID, vector, payload)
        │
        └─ QdrantService.upsert_points(batch=100) → Qdrant :6333
```

Se puede disparar por:
- `POST /admin/load` (con API key)
- `python scripts/load_to_qdrant.py` (CLI)

### Consulta en tiempo real

```
POST /query { text: "¿Qué es la mitosis?", n_results: 3 }
        │
        ▼
api/routes.py → query_rag()
        ├─ EmbeddingService.embed_one(text) → query_vector[384]
        ├─ QdrantService.search(query_vector, limit=3)
        └─ return [ResultItem(id, document, metadata, score), ...]
```

---

## 8. Seguridad

### pywebguard (FastAPIGuard)

Configurado en `main.py`:

| Característica | Configuración |
|---|---|
| **IP Whitelist** | `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` |
| **IP Blacklist** | `0.0.0.0/8`, `169.254.0.0/16` |
| **Rate Limiting** | 100 req/min, burst de 20 |
| **Auto-ban** | 200 requests → ban 300 segundos |
| **Protección anti-penetración** | Deshabilitada (SQL injection, XSS, path traversal disponibles pero `enabled: False`) |

### TrustedHostMiddleware

Solo acepta requests de: `localhost`, `127.0.0.1`, `rag-api`, `auth-ms`, `*.internal.local`.

### API Key (endpoints admin)

Los endpoints `/admin/*` requieren el header `X-API-Key` con el valor de la variable `ADMIN_API_KEY`.

> ⚠️ **Producción:** Cambiar el valor por defecto `mi-clave-secreta-para-cargar-datos`.

---

## 9. Observabilidad (OpenTelemetry)

El sistema envía **trazas** y **logs** a Grafana Alloy vía OTLP/gRPC.

| Componente | Detalle |
|---|---|
| **Endpoint** | `alloy:4317` (gRPC, insecure) |
| **Servicio** | `rag-api` |
| **Trazas** | `OTLPSpanExporter` → `BatchSpanProcessor` |
| **Logs** | `OTLPLogExporter` → `BatchLogRecordProcessor` |
| **Instrumentación** | `FastAPIInstrumentor` (auto-instrumenta cada request) |
| **Red Docker** | `observability-net` (externa, compartida con stack de observabilidad) |

**Dependencias OpenTelemetry (pinned):**
```
opentelemetry-distro==0.48b0
opentelemetry-sdk==1.27.0
opentelemetry-exporter-otlp-proto-http==1.27.0
opentelemetry-exporter-otlp-proto-grpc==1.27.0
opentelemetry-instrumentation-fastapi==0.48b0
opentelemetry-instrumentation-logging==0.48b0
opentelemetry-semantic-conventions==0.48b0
```

> **Nota:** Estas versiones deben estar sincronizadas entre sí.

---

## 10. Configuración y Variables de Entorno

### `config.yml`

```yaml
qdrant:
  host: localhost
  port: 6333
  collection_name: rag_biologia

embedding:
  model_name: BAAI/bge-small-en-v1.5

logging:
  level: INFO
  file: ./logs/rag_service.log
  rotation: 10 MB
  retention: 30 days
  compression: gz
  console: true
```

### Variables de Entorno (sobreescriben `config.yml`)

| Variable | Default en docker-compose | Default en código | Descripción |
|---|---|---|---|
| `QDRANT_HOST` | `qdrant-server` | `localhost` | Host Qdrant |
| `QDRANT_PORT` | `6333` | `6333` | Puerto Qdrant |
| `COLLECTION_NAME` | `rag_biologia` | `rag_biologia` | Colección |
| `EMBEDDING_MODEL` | _(no seteada)_ | `BAAI/bge-small-en-v1.5` | Modelo de embeddings |
| `ADMIN_API_KEY` | `mi-clave-secreta-para-cargar-datos` | ídem | API key admin |
| `CONFIG_PATH` | _(no seteada)_ | `config.yml` | Ruta config YAML |

---

## 11. Despliegue con Docker

### Docker Compose

```yaml
services:
  qdrant-server:       # Qdrant vectorial, puertos 6333/6334
  rag-api:             # FastAPI, puerto 8002→8000, --reload

networks:
  observability-net:   # Externa, para telemetría a Alloy
```

### Volúmenes

| Ruta Host | Ruta Contenedor | Propósito |
|---|---|---|
| `.` (raíz) | `/app` | Código fuente (hot-reload) |
| `./logs` | `/app/logs` | Persistencia de logs |
| `./config.yml` | `/app/config.yml` | Configuración |
| `./qdrant_storage` | `/qdrant/storage` | Datos Qdrant |

### Puertos

| Servicio | Puerto Host | Binding |
|---|---|---|
| `rag-api` | `8002` | `127.0.0.1` (solo local) |
| `qdrant-server` | `6333` | `0.0.0.0` |
| `qdrant-server` | `6334` (gRPC) | `0.0.0.0` |

### Dockerfile

```dockerfile
FROM python:3.11-slim
# Instala curl (healthchecks), dependencias Python
# Copia código fuente
# CMD: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 12. Dependencias

| Paquete | Versión | Propósito |
|---|---|---|
| `qdrant-client[fastembed]` | latest | Cliente Qdrant + embeddings ONNX integrados |
| `fastapi` | latest | Framework web asíncrono |
| `uvicorn` | latest | Servidor ASGI |
| `pyyaml` | latest | Parseo de `config.yml` |
| `loguru` | latest | Logging con rotación automática |
| `pywebguard` | ≥1.0.26 | Rate limiting, IP filtering, protección web |
| `structlog` | ≥24.1.0 | Logging estructurado |
| `opentelemetry-*` | 1.27.0 / 0.48b0 | Trazas y logs distribuidos |

> **Nota:** El extra `[fastembed]` en `qdrant-client` instala soporte para embeddings con ONNX Runtime. Sin él, hay que instalar `fastembed` por separado.

---

## 13. Cómo Extender el Sistema

### Agregar contenido educativo
1. Actualizar `corpus/secciones_completas.json`.
2. Cargar vía API: `POST /admin/load` con API key.
3. Verificar con `GET /health` que `points` aumentó.

### Cambiar el modelo de embeddings
1. Setear `EMBEDDING_MODEL=nuevo-modelo` en `docker-compose.yml`.
2. Re-cargar datos (el `IndexerService` detecta automáticamente el tamaño del nuevo vector).
3. Verificar.

### Agregar campo al payload
1. Editar `services/indexer_service.py` → agregar campo en el dict `payload`.
2. Re-cargar datos.
3. El campo aparece automáticamente en `metadata` de `/query`.

### Agregar filtros por metadata
1. Extender `QueryRequest` en `core/models.py`.
2. Construir `Filter` de Qdrant en `api/routes.py`.
3. Pasarlo a `qdrant_service.search()`.

---

## 14. CI/CD — GitHub Actions

### `telegram-notify.yml`

Envía notificaciones a un grupo de Telegram cuando:

| Evento | Mensaje |
|---|---|
| PR abierto | 🟢 Nuevo PR + título, autor, enlace |
| PR cerrado | 🔴 PR cerrado + detalles |
| Revisión solicitada | 👀 Revisión + lista de revisores |

**Secrets requeridos:**
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_TOKEN`

---

## 15. Glosario

| Término | Definición |
|---|---|
| **RAG** | Retrieval-Augmented Generation — recuperar contexto antes de generar con LLM |
| **Embedding** | Vector numérico que captura el significado semántico de un texto |
| **Qdrant** | Base de datos vectorial open-source para búsqueda por similitud |
| **fastembed** | Librería de Qdrant para embeddings locales con ONNX (sin GPU) |
| **BAAI/bge-small-en-v1.5** | Modelo de embedding ligero (384 dims) |
| **Coseno** | Métrica de distancia entre vectores (ángulo). Ideal para texto |
| **PointStruct** | Objeto Qdrant: ID + vector + payload |
| **Payload** | Metadatos adjuntos a un vector (texto, etiquetas, fuente) |
| **OTLP** | OpenTelemetry Protocol — estándar para enviar telemetría |
| **Alloy** | Agente de Grafana que recibe y reenvía telemetría |
| **pywebguard** | Middleware de seguridad para FastAPI (rate limit, IP filter) |
