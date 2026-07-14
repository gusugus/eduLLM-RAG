# Wiki — RAG EduLLM

---

## PÁGINA 1 → título: `Home`

---

# RAG EduLLM

Microservicio de búsqueda semántica para contenido educativo de Biología.
Parte del ecosistema **EduLLM / MindBuzz**.

## ¿Qué hace este servicio?

Dado un texto de consulta (una pregunta del alumno o del sistema), busca en una base de datos vectorial los **fragmentos de contenido educativo más relevantes** y los devuelve listos para inyectarse en el prompt de un LLM.

> El servicio **no genera texto**. Solo recupera contexto. La generación la hace el LLM.

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| API | FastAPI + Uvicorn (Python 3.11) |
| Base de datos vectorial | Qdrant |
| Modelo de embeddings | BAAI/bge-small-en-v1.5 (fastembed, ONNX, sin GPU) |
| Seguridad | pywebguard (rate limiting, IP filtering) |
| Observabilidad | OpenTelemetry → Grafana Alloy (OTLP/gRPC) |
| Logging | Loguru + structlog con rotación automática |
| Infraestructura | Docker + Docker Compose |
| CI/CD | GitHub Actions (notificaciones Telegram) |

## Páginas de esta wiki

| Página | Descripción |
|---|---|
| [[Configuración]] | Cómo instalar y correr el sistema desde cero |
| [[API-Reference]] | Endpoints disponibles, parámetros y ejemplos |
| [[Arquitectura]] | Diagrama del sistema, componentes y flujo de datos |
| [[Seguridad-y-Observabilidad]] | Middlewares, rate limiting, OpenTelemetry |
| [[Cómo-Extender]] | Agregar contenido, cambiar modelos, agregar filtros |

## Estructura del repositorio

```
rag/
├── main.py                    # Punto de entrada: FastAPI + middlewares + telemetría
├── config.yml                 # Configuración de Qdrant, embeddings y logging
├── requirements.txt           # Dependencias Python
├── Dockerfile                 # Imagen del servicio (python:3.11-slim)
├── docker-compose.yml         # Orquestación: rag-api + qdrant-server
├── api/
│   └── routes.py              # Endpoints: /query, /health, /admin/*
├── core/
│   ├── config.py              # Clase Settings (YAML + env vars)
│   ├── logging_config.py      # Setup de Loguru
│   └── models.py              # Schemas Pydantic
├── services/
│   ├── embedding_service.py   # Singleton de embeddings (fastembed)
│   ├── qdrant_service.py      # Cliente Qdrant (CRUD)
│   └── indexer_service.py     # Carga: JSON → embeddings → Qdrant
├── scripts/
│   └── load_to_qdrant.py      # Script CLI de carga
├── corpus/
│   └── secciones_completas.json  # Contenido educativo fuente
├── qdrant_storage/            # Datos persistentes de Qdrant (no editar)
└── logs/                      # Logs con rotación automática
```

---

---

## PÁGINA 2 → título: `Configuración`

---

# Configuración

Guía completa para instalar y correr el sistema desde cero.

## Requisitos previos

- **Docker** instalado y corriendo → [Instalar Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (incluido en Docker Desktop)
- Red Docker para observabilidad:

```bash
docker network create observability-net
```

---

## Configuración inicial (primera vez)

### Paso 1 — Levantar el sistema completo

```bash
docker compose up --build -d
```

Esto construye la imagen Docker del servicio RAG y levanta dos contenedores:
- `qdrant-server` — base de datos vectorial en el puerto `6333`
- `rag-api` — servicio FastAPI en el puerto `8002`

### Paso 2 — Cargar el contenido educativo

Usando el endpoint admin (recomendado):

```bash
curl -X POST http://localhost:8002/admin/load \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mi-clave-secreta-para-cargar-datos" \
  -d '{"recreate": true, "batch_size": 100}'
```

Alternativa con script CLI:
```bash
docker compose exec rag-api python scripts/load_to_qdrant.py
```

> La primera ejecución puede tardar unos minutos porque descarga el modelo de embeddings (~90 MB).

### Paso 3 — Verificar que todo funciona

```bash
curl http://localhost:8002/health
```

Respuesta esperada:
```json
{"status": "ok", "collection": "rag_biologia", "points": 142}
```

Si `points` es `0`, la carga no fue exitosa — repetir el Paso 2.

---

## Uso cotidiano

```bash
# Levantar
docker compose up -d

# Detener
docker compose down
```

---

## Puertos

| Servicio | Puerto en tu máquina |
|---|---|
| RAG API (FastAPI) | `http://localhost:8002` |
| Qdrant REST | `http://localhost:6333` ([Ver Dashboard](http://localhost:6333/dashboard)) |
| Qdrant gRPC | `localhost:6334` |

---

## Variables de entorno

Configurables en `docker-compose.yml`:

| Variable | Default | Descripción |
|---|---|---|
| `QDRANT_HOST` | `qdrant-server` | Host del servidor Qdrant |
| `QDRANT_PORT` | `6333` | Puerto REST de Qdrant |
| `COLLECTION_NAME` | `rag_biologia` | Nombre de la colección |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Modelo de embeddings |
| `ADMIN_API_KEY` | `mi-clave-secreta-para-cargar-datos` | API key para endpoints admin |
| `CONFIG_PATH` | `config.yml` | Ruta al archivo de configuración |

---

---

## PÁGINA 3 → título: `API-Reference`

---

# API Reference

Base URL: `http://localhost:8002`

---

## Endpoints Públicos

### POST `/query`

Busca los fragmentos de contenido educativo más relevantes para una consulta de texto libre.

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "text": "¿Cómo se clasifica un organismo según la taxonomía de Linneo?",
  "n_results": 5,
  "min_score": 0.7
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `text` | `string` | ✅ | — | Texto de la consulta en lenguaje natural |
| `n_results` | `integer` | ❌ | `5` | Cantidad de resultados a devolver |
| `min_score` | `float` | ❌ | `0.0` | Score mínimo de similitud (0.0–1.0) para filtrar resultados |

**Response `200 OK`:**
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
      "curriculum_tema": "Unidad 1"
    },
    "score": 0.87
  }
]
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | `string` | UUID del punto en Qdrant |
| `document` | `string` | Texto completo del fragmento (se inyecta en el prompt del LLM) |
| `metadata` | `object` | Metadatos del fragmento |
| `score` | `float` | Similitud coseno (0.0–1.0, mayor = más relevante) |

**Errores:** `400` texto vacío, `500` error interno.

**Ejemplo curl:**
```bash
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"text": "diferencia entre mitosis y meiosis", "n_results": 3}'
```

---

### GET `/health`

Verifica que el servicio esté corriendo y conectado a Qdrant.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "collection": "rag_biologia",
  "points": 142
}
```

---

## Endpoints de Administración

Todos requieren el header `X-API-Key` con el valor configurado en `ADMIN_API_KEY`.

### POST `/admin/load`

Carga datos desde un archivo JSON a Qdrant. Se ejecuta como background task.

**Body:**
```json
{
  "json_path": null,
  "recreate": true,
  "batch_size": 100
}
```

**Response `200`:** `{"status": "loading_started", ...}`

**Ejemplo:**
```bash
curl -X POST http://localhost:8002/admin/load \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mi-clave-secreta-para-cargar-datos" \
  -d '{"recreate": true}'
```

### GET `/admin/load/status`

Retorna disponibilidad del endpoint y existencia del JSON por defecto.

### GET `/admin/info`

Retorna información del sistema: rutas, estado de Qdrant y corpus.

---

---

## PÁGINA 4 → título: `Arquitectura`

---

# Arquitectura

## Diagrama del sistema

```
  ┌──────────────────────────────────────┐
  │          Cliente / Proxy LLM         │
  └─────────────────┬────────────────────┘
                    │  POST /query
                    ▼
  ┌──────────────────────────────────────┐
  │     main.py (FastAPI App :8002)      │
  │                                      │
  │  Middlewares:                         │
  │   ├─ TrustedHostMiddleware           │
  │   ├─ FastAPIGuard (pywebguard)       │
  │   └─ FastAPIInstrumentor (OTel)      │
  │                                      │
  │  Router → api/routes.py             │
  │   ├─ EmbeddingService (Singleton)    │
  │   ├─ QdrantService                   │
  │   └─ IndexerService                  │
  └─────────────────┬────────────────────┘
                    │  HTTP :6333
                    ▼
  ┌──────────────────────────────────────┐
  │         Qdrant Server :6333          │
  │    Colección: rag_biologia           │
  │    ~142 vectores de 384 dims         │
  │    Distancia: Coseno                 │
  └──────────────────────────────────────┘
```

## Capas del código

```
main.py                    → App + middlewares + telemetría
  └─ api/routes.py         → Endpoints (presentación)
       ├─ core/models.py   → Schemas Pydantic
       ├─ core/config.py   → Settings (YAML + env vars)
       └─ services/        → Lógica de negocio
            ├─ embedding_service.py   (Singleton, fastembed)
            ├─ qdrant_service.py      (cliente Qdrant)
            └─ indexer_service.py     (orquestación de carga)
```

## Flujo de indexación (carga de datos)

```
corpus/secciones_completas.json
         │
         ▼
IndexerService.load_from_json()
         ├─ texto = titulo + texto_completo + resumen
         ├─ EmbeddingService.embed_one(texto) → vector[384]
         └─ QdrantService.upsert_points(batch=100) → Qdrant
```

## Flujo de consulta (tiempo real)

```
POST /query { text: "¿Qué es la mitosis?" }
         │
         ▼
api/routes.py → query_rag()
         ├─ EmbeddingService.embed_one(text) → query_vector[384]
         ├─ QdrantService.search(query_vector, limit)
         └─ return [ { id, document, metadata, score }, ... ]
```

## Contenedores Docker

| Contenedor | Imagen | Puerto externo | Puerto interno |
|---|---|---|---|
| `rag-api` | Dockerfile local | `8002` (localhost) | `8000` |
| `qdrant-server` | `qdrant/qdrant:latest` | `6333` | `6333` |
| `qdrant-server` | `qdrant/qdrant:latest` | `6334` (gRPC) | `6334` |

---

---

## PÁGINA 5 → título: `Seguridad-y-Observabilidad`

---

# Seguridad y Observabilidad

## Seguridad

### pywebguard (FastAPIGuard)

Middleware de seguridad configurado en `main.py`:

| Feature | Configuración |
|---|---|
| IP Whitelist | `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` |
| IP Blacklist | `0.0.0.0/8`, `169.254.0.0/16` |
| Rate Limiting | 100 req/min, burst 20 |
| Auto-ban | 200 requests → ban 5 minutos |
| Anti-penetración | Disponible pero deshabilitado |

### TrustedHostMiddleware

Solo acepta requests de hosts: `localhost`, `127.0.0.1`, `rag-api`, `auth-ms`, `*.internal.local`.

### API Key (Admin)

Endpoints `/admin/*` requieren header `X-API-Key`. Configurable con variable `ADMIN_API_KEY`.

## Observabilidad (OpenTelemetry)

Trazas y logs se envían a Grafana Alloy vía OTLP/gRPC.

| Componente | Detalle |
|---|---|
| Endpoint | `alloy:4317` (gRPC, insecure) |
| Service name | `rag-api` |
| Trazas | `OTLPSpanExporter` → `BatchSpanProcessor` |
| Logs | `OTLPLogExporter` → `BatchLogRecordProcessor` |
| Instrumentación | `FastAPIInstrumentor` (auto) |
| Red Docker | `observability-net` (externa) |

---

---

## PÁGINA 6 → título: `Cómo-Extender`

---

# Cómo Extender el Sistema

---

## Agregar o actualizar contenido educativo

1. Editar `corpus/secciones_completas.json` con las nuevas secciones.
2. Cargar vía API:

```bash
curl -X POST http://localhost:8002/admin/load \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mi-clave-secreta-para-cargar-datos" \
  -d '{"recreate": true}'
```

3. Verificar con `GET /health` que `points` refleja el nuevo total.

---

## Cambiar el modelo de embeddings

> ⚠️ Cambiar el modelo requiere re-indexar toda la colección.

1. Editar `docker-compose.yml`, agregar variable:
   ```yaml
   environment:
     - EMBEDDING_MODEL=nombre/del-nuevo-modelo
   ```
2. Re-cargar datos con `POST /admin/load` (recreate=true). El `IndexerService` detecta automáticamente las dimensiones.
3. Reiniciar: `docker compose restart rag-api`.

---

## Agregar un nuevo campo al payload

1. Editar `services/indexer_service.py`, agregar el campo en el dict `payload`:
   ```python
   payload = {
       "document": texto_indexable,
       # ... campos existentes ...
       "nuevo_campo": sec.get('nuevo_campo', ''),
   }
   ```
2. Re-cargar datos.
3. El campo aparece automáticamente en `metadata` de `/query`.

---

## Agregar filtros por metadata

1. Extender `QueryRequest` en `core/models.py`:
   ```python
   class QueryRequest(BaseModel):
       text: str
       n_results: int = 5
       tema: str | None = None
   ```

2. Construir filtro en `api/routes.py`:
   ```python
   from qdrant_client.models import Filter, FieldCondition, MatchValue

   query_filter = None
   if request.tema:
       query_filter = Filter(
           must=[FieldCondition(key="tema", match=MatchValue(value=request.tema))]
       )
   ```

3. Pasar `query_filter` a `qdrant_service.search()`.

---

## Agregar umbral de similitud (min_score)

1. Extender `QueryRequest` en `core/models.py`:
   ```python
   class QueryRequest(BaseModel):
       text: str
       n_results: int = 5
       min_score: float = 0.0
   ```

2. Configurar umbral en `config.yml`:
   ```yaml
   search:
     min_score: 0.7
   ```

3. O sobrescribir con variable de entorno:
   ```bash
   export MIN_SCORE=0.7
   ```

4. El endpoint `/query` filtrará automáticamente los resultados con score ≥ min_score.

---

## Cambiar el nivel de logging

Editar `config.yml`:
```yaml
logging:
  level: "DEBUG"
```

Reiniciar:
```bash
docker compose restart rag-api
```
