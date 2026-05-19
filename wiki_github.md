# Wiki — RAG EduLLM

---

## PÁGINA 1 → título: `Home`

---

# RAG EduLLM

Microservicio de búsqueda semántica para contenido educativo de Biología.
Parte del ecosistema **MindBuzz / EduLLM**.

## ¿Qué hace este servicio?

Dado un texto de consulta (una pregunta del alumno o del sistema), busca en una base de datos vectorial los **fragmentos de contenido educativo más relevantes** y los devuelve listos para inyectarse en el prompt de un LLM.

> El servicio **no genera texto**. Solo recupera contexto. La generación la hace el LLM.

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| API | FastAPI + Uvicorn |
| Base de datos vectorial | Qdrant |
| Modelo de embeddings | BAAI/bge-small-en-v1.5 (fastembed, sin GPU) |
| Logging | Loguru con rotación automática |
| Infraestructura | Docker + Docker Compose |

## Páginas de esta wiki

| Página | Descripción |
|---|---|
| [[Configuración]] | Cómo instalar y correr el sistema desde cero |
| [[API-Reference]] | Endpoints disponibles, parámetros y ejemplos |
| [[Arquitectura]] | Diagrama del sistema y flujo de datos |
| [[Cómo-Extender]] | Agregar contenido, cambiar modelos, agregar filtros |

## Estructura del repositorio

```
rag/
├── api.py                 # Servicio FastAPI (único archivo de producción)
├── config.yml             # Configuración de logging
├── requirements.txt       # Dependencias Python
├── Dockerfile             # Imagen del servicio RAG API
├── docker-compose.yml     # Orquestación: rag-api + qdrant-server
├── qdrant/
│   ├── docker-compose.yml     # Solo Qdrant (para migración inicial)
│   ├── migrar_a_qdrant.py     # Script one-time de carga de datos
│   └── secciones_completas.json  # Contenido educativo fuente
├── qdrant_storage/        # Datos persistentes de Qdrant (no editar)
└── logs/                  # Logs con rotación automática
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
- **Python 3.11+** — solo para el script de migración inicial

Instalar las dependencias del script de migración:

```bash
pip install "qdrant-client[fastembed]"
```

---

## Configuración inicial (primera vez)

Estos pasos se hacen **una sola vez** para poblar la base de datos vectorial con el contenido educativo.

### Paso 1 — Levantar Qdrant (servicio temporal para migración)

```bash
cd qdrant/
docker compose up -d
```

Verificar que está corriendo:

```bash
curl http://localhost:6333/healthz
```

Respuesta esperada:
```json
{"title": "qdrant - vector search engine"}
```

### Paso 2 — Migrar los datos a Qdrant

Este script lee `qdrant/secciones_completas.json`, genera los embeddings vectoriales y los carga en Qdrant.

```bash
# Desde la raíz del proyecto
python qdrant/migrar_a_qdrant.py
```

Output esperado:

```
Colección 'rag_biologia' eliminada
Colección 'rag_biologia' creada
Subidos 100/142 puntos
Subidos 142/142 puntos
✅ Carga completada
```

> La primera ejecución puede tardar unos minutos porque descarga el modelo de embeddings (~90 MB).

### Paso 3 — Apagar el Qdrant temporal

```bash
cd qdrant/
docker compose down
```

Los datos quedan persistidos en `qdrant_storage/` y se reutilizarán automáticamente.

### Paso 4 — Levantar el sistema completo

```bash
# Desde la raíz del proyecto
docker compose up --build
```

Esto construye la imagen Docker del servicio RAG y levanta dos contenedores:
- `qdrant-server` — base de datos vectorial en el puerto `6333`
- `rag-api` — servicio FastAPI en el puerto `8002`

### Paso 5 — Verificar que todo funciona

```bash
# Healthcheck
curl http://localhost:8002/health
```

Respuesta esperada:
```json
{"status": "ok", "collection": "rag_biologia", "points": 142}
```

Si `points` es `0`, la migración no fue exitosa — repetir desde el Paso 1.

---

## Uso cotidiano

Una vez configurado, solo necesitás:

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

Podés sobreescribir la configuración por defecto en `docker-compose.yml`:

| Variable | Default | Descripción |
|---|---|---|
| `QDRANT_HOST` | `qdrant-server` | Host del servidor Qdrant |
| `QDRANT_PORT` | `6333` | Puerto REST de Qdrant |
| `COLLECTION_NAME` | `rag_biologia` | Nombre de la colección |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Modelo de embeddings |
| `CONFIG_PATH` | `config.yml` | Ruta al archivo de configuración |

---

---

## PÁGINA 3 → título: `API-Reference`

---

# API Reference

Base URL: `http://localhost:8002`

---

## POST `/query`

Busca los fragmentos de contenido educativo más relevantes para una consulta de texto libre.

### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "text": "¿Cómo se clasifica un organismo según la taxonomía de Linneo?",
  "n_results": 5
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `text` | `string` | ✅ | — | Texto de la consulta en lenguaje natural |
| `n_results` | `integer` | ❌ | `5` | Cantidad de resultados a devolver |

### Response `200 OK`

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document": "Clasificación de los seres vivos\nLos seres vivos se clasifican en dominios...\nResumen: La taxonomía de Linneo organiza...",
    "metadata": {
      "codigo": "SEC-001",
      "titulo": "Clasificación de los seres vivos",
      "tema": "Taxonomía",
      "fuente": "Libro 10mo Ciencias Naturales",
      "keywords_nlp": ["reino", "filo", "clase", "orden"],
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
| `document` | `string` | **Texto completo del fragmento** — este es el que se inyecta en el prompt del LLM |
| `metadata` | `object` | Metadatos del fragmento (tema, fuente, keywords, etc.) |
| `score` | `float` | Similitud coseno con la consulta (0.0–1.0, mayor = más relevante) |

### Errores

| Código | Causa |
|---|---|
| `400 Bad Request` | El campo `text` está vacío o solo contiene espacios |
| `500 Internal Server Error` | Qdrant no disponible u otro error interno |

### Ejemplo con curl

```bash
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "text": "diferencia entre mitosis y meiosis",
    "n_results": 3
  }'
```

---

## GET `/health`

Verifica que el servicio esté corriendo y conectado a Qdrant.

### Response `200 OK`

```json
{
  "status": "ok",
  "collection": "rag_biologia",
  "points": 142
}
```

| Campo | Descripción |
|---|---|
| `status` | Siempre `"ok"` si el servicio está sano |
| `collection` | Nombre de la colección activa en Qdrant |
| `points` | Cantidad de vectores indexados |

### Ejemplo con curl

```bash
curl http://localhost:8002/health
```

---

---

## PÁGINA 4 → título: `Arquitectura`

---

# Arquitectura

## Diagrama del sistema

```
  ┌──────────────────────────────────────┐
  │          Cliente / Proxy LLM         │
  │   (hace POST /query con la pregunta) │
  └─────────────────┬────────────────────┘
                    │
                    │  POST http://localhost:8002/query
                    │  Body: { "text": "...", "n_results": 5 }
                    ▼
  ┌──────────────────────────────────────┐
  │         RAG API — api.py             │
  │         FastAPI + Uvicorn :8002      │
  │                                      │
  │  1. Recibe la consulta en texto      │
  │  2. Genera embedding (384 dims)      │
  │     con BAAI/bge-small-en-v1.5       │
  │  3. Consulta Qdrant por similitud    │
  │  4. Retorna top-K fragmentos + score │
  └─────────────────┬────────────────────┘
                    │
                    │  HTTP REST :6333
                    ▼
  ┌──────────────────────────────────────┐
  │         Qdrant Server :6333          │
  │    Colección: rag_biologia           │
  │    ~142 vectores de 384 dims         │
  │    Distancia: Coseno                 │
  └──────────────────────────────────────┘
```

## Flujo de indexación (one-time setup)

```
secciones_completas.json
         │
         │  Cada sección tiene: titulo, texto_completo, resumen, metadatos
         ▼
migrar_a_qdrant.py
         │
         ├─ Construye texto = titulo + texto_completo + resumen
         ├─ fastembed.embed(texto)  →  vector[384]
         └─ qdrant.upsert(id=UUID, vector, payload)  →  Qdrant :6333
```

## Flujo de consulta (tiempo real)

```
POST /query { text: "¿Qué es la mitosis?" }
         │
         ▼
api.py
         ├─ embedding_model.embed(text)  →  query_vector[384]
         ├─ qdrant.query_points(query_vector, limit=n_results)
         └─ return [ { id, document, metadata, score }, ... ]
```

## Estructura de un punto en Qdrant

```
PointStruct
├── id            → UUID único
├── vector[384]   → Embedding del texto (BAAI/bge-small-en-v1.5)
└── payload
    ├── document       ← Texto completo (lo que devuelve /query)
    ├── codigo         ← ID de la sección (ej: "SEC-001")
    ├── titulo         ← Título legible
    ├── tema           ← Tema curricular
    ├── fuente         ← Libro o material de origen
    ├── keywords_nlp   ← Lista de palabras clave (NLP)
    ├── topic_id       ← Clúster BERTopic
    └── curriculum_tema← Unidad curricular
```

## Contenedores Docker

| Contenedor | Imagen | Puerto externo | Puerto interno |
|---|---|---|---|
| `rag-api` | Dockerfile local | `8002` | `8000` |
| `qdrant-server` | `qdrant/qdrant:latest` | `6333` | `6333` |
| `qdrant-server` | `qdrant/qdrant:latest` | `6334` (gRPC) | `6334` |

---

---

## PÁGINA 5 → título: `Cómo-Extender`

---

# Cómo Extender el Sistema

---

## Agregar o actualizar contenido educativo

El contenido fuente está en `qdrant/secciones_completas.json`.

1. Editar el JSON con las nuevas secciones (mismo formato que el existente).
2. Re-ejecutar la migración:

```bash
# Levantar Qdrant temporal
cd qdrant/
docker compose up -d

# Re-indexar (borra y recrea la colección)
python qdrant/migrar_a_qdrant.py

# Bajar Qdrant temporal
docker compose down

# Volver a levantar el sistema completo
cd ..
docker compose up -d
```

3. Verificar con `GET /health` que `points` aumentó.

---

## Cambiar el modelo de embeddings

> ⚠️ **Importante:** cambiar el modelo requiere re-indexar toda la colección porque las dimensiones del vector cambian.

1. Editar `docker-compose.yml`, agregar la variable de entorno al servicio `rag-api`:
   ```yaml
   environment:
     - EMBEDDING_MODEL=nombre/del-nuevo-modelo
   ```

2. En `qdrant/migrar_a_qdrant.py`, actualizar el `size` de la colección según las dimensiones del nuevo modelo:
   ```python
   client.create_collection(
       collection_name=COLLECTION_NAME,
       vectors_config=VectorParams(size=768, distance=Distance.COSINE)  # ← cambiar
   )
   ```

3. Actualizar también el `model_name` en el script:
   ```python
   embedding_model = TextEmbedding(model_name="nombre/del-nuevo-modelo")
   ```

4. Re-ejecutar la migración completa (ver sección anterior).

---

## Agregar un nuevo campo al payload

1. Editar `qdrant/migrar_a_qdrant.py`, agregar el campo en el dict `payload`:
   ```python
   payload = {
       "document": texto_indexable,
       "codigo": sec.get('codigo', ''),
       # ... campos existentes ...
       "nuevo_campo": sec.get('nuevo_campo', ''),  # ← agregar acá
   }
   ```

2. Re-ejecutar la migración.

3. El nuevo campo aparece automáticamente en `metadata` de la respuesta de `/query` — no hay que tocar `api.py`.

---

## Agregar filtros por metadata en las consultas

La API actual no tiene filtros. Para agregar, por ejemplo, filtrar por `tema`:

**1. Extender el schema en `api.py`:**
```python
class QueryRequest(BaseModel):
    text: str
    n_results: int = 5
    tema: str | None = None  # ← nuevo campo opcional
```

**2. Construir el filtro de Qdrant en el endpoint:**
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

@app.post("/query", response_model=List[ResultItem])
async def query_rag(request: QueryRequest):
    query_embedding = list(embedding_model.embed([request.text]))[0]
    
    query_filter = None
    if request.tema:
        query_filter = Filter(
            must=[FieldCondition(key="tema", match=MatchValue(value=request.tema))]
        )
    
    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        limit=request.n_results,
        query_filter=query_filter,  # ← agregar acá
        with_payload=True
    ).points
    ...
```

**Ejemplo de uso con filtro:**
```bash
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"text": "reproducción celular", "n_results": 3, "tema": "Biología Celular"}'
```

---

## Cambiar el nivel de logging

Editar `config.yml`:

```yaml
logging:
  level: "DEBUG"   # DEBUG | INFO | WARNING | ERROR
```

Reiniciar el contenedor para aplicar el cambio:

```bash
docker compose restart rag-api
```
