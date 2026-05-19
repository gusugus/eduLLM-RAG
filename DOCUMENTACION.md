# Documentación Técnica — Servicio RAG de Biología

> **Repositorio:** `/home/gusgus/Documentos/rag`  
> **Propósito:** Microservicio de Recuperación-Aumentada-con-Generación (RAG) para contenido educativo de Biología. Expone una API REST que, dada una consulta en texto libre, devuelve los fragmentos más relevantes del material de estudio, listos para inyectarse en un prompt de LLM.

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Estructura de Archivos](#3-estructura-de-archivos)
4. [Componentes Principales](#4-componentes-principales)
5. [API REST — Endpoints Públicos](#5-api-rest--endpoints-públicos)
6. [Modelo de Datos](#6-modelo-de-datos)
7. [Flujo de Datos Completo](#7-flujo-de-datos-completo)
8. [Configuración y Variables de Entorno](#8-configuración-y-variables-de-entorno)
9. [Despliegue con Docker](#9-despliegue-con-docker)
10. [Dependencias](#10-dependencias)
11. [Integración con el Proxy/LLM](#11-integración-con-el-proxyllm)
12. [Cómo Extender el Sistema](#12-cómo-extender-el-sistema)
13. [Glosario](#13-glosario)

---

## 1. Visión General

Este repositorio implementa el **módulo de búsqueda semántica** de la plataforma educativa MindBuzz. Su responsabilidad única es:

> Dado un texto de consulta (pregunta del alumno o del sistema), buscar en una base de datos vectorial (Qdrant) los fragmentos de contenido educativo más relevantes y devolverlos con su puntuación de similitud.

El servicio **no genera texto** — eso lo hace el LLM. Solo recupera contexto relevante para enriquecer el prompt.

**Stack tecnológico:**
- **FastAPI** — Framework web asíncrono (Python)
- **Qdrant** — Base de datos vectorial (corre en Docker)
- **fastembed (BAAI/bge-small-en-v1.5)** — Modelo de embeddings ligero (no requiere GPU, no requiere PyTorch)
- **Uvicorn** — Servidor ASGI
- **Loguru** — Logging con rotación automática

---

## 2. Arquitectura del Sistema

```
                     ┌─────────────────────────────────────┐
                     │         Proxy / LLM Backend         │
                     │  (services/rag_service.py en proxy) │
                     └──────────────┬──────────────────────┘
                                    │ POST /query
                                    ▼
                     ┌──────────────────────────────────────┐
                     │        RAG API (FastAPI)             │
                     │         api.py  :8002                │
                     │                                      │
                     │  1. Embed(query) via fastembed       │
                     │  2. Search(Qdrant)                   │
                     │  3. Return top-K docs + score        │
                     └──────────────┬───────────────────────┘
                                    │ HTTP REST
                                    ▼
                     ┌─────────────────────────────────────┐
                     │         Qdrant Server               │
                     │    qdrant-server  :6333             │
                     │    Colección: rag_biologia          │
                     │    Vectores: 384 dims (coseno)      │
                     └─────────────────────────────────────┘
```

Ambos servicios (`rag-api` y `qdrant-server`) corren como contenedores Docker definidos en `docker-compose.yml`.

---

## 3. Estructura de Archivos

```
/home/gusgus/Documentos/rag/
│
├── api.py                    ← Servicio FastAPI principal (único archivo de código)
├── config.yml                ← Configuración de logging y parámetros del servicio
├── requirements.txt          ← Dependencias Python del servicio
│
├── Dockerfile                ← Imagen Docker del servicio RAG API
├── docker-compose.yml        ← Orquestación: rag-api + qdrant-server
│
├── qdrant/                   ← Scripts y compose para solo Qdrant (migración inicial)
│   ├── docker-compose.yml    ← Levanta SOLO Qdrant (para la migración inicial)
│   ├── migrar_a_qdrant.py    ← Script one-time: carga secciones_completas.json → Qdrant
│   └── secciones_completas.json ← Datos fuente del contenido educativo (84 KB)
│
├── qdrant_storage/           ← Volumen persistente de Qdrant (NO editar manualmente)
├── chroma_db/                ← (Vestigial) ChromaDB anterior, ya no se usa
├── logs/                     ← Logs del servicio con rotación automática
└── README.md                 ← Guía rápida de inicio (4 pasos)
```

> **IMPORTANTE:** El archivo `qdrant/secciones_completas.json` es el **origen único de verdad** para el contenido indexado. Si se actualiza el contenido educativo, hay que re-ejecutar `migrar_a_qdrant.py` con el nuevo JSON.

---

## 4. Componentes Principales

### `api.py` — El Servicio FastAPI

**Ubicación:** `/home/gusgus/Documentos/rag/api.py`

Es el único archivo de código de producción. Hace tres cosas al arrancar:

1. **Lee la configuración** desde `config.yml` (o variables de entorno que la sobreescriben).
2. **Carga el modelo de embeddings** `BAAI/bge-small-en-v1.5` (384 dimensiones, se descarga automáticamente la primera vez desde HuggingFace).
3. **Conecta a Qdrant** y verifica que la colección `rag_biologia` exista. Si no existe, **falla en el arranque** con un error (protección intencional: el servicio no arranca sin datos).

**Clases Pydantic (esquemas de entrada/salida):**

| Clase | Uso | Campos |
|---|---|---|
| `QueryRequest` | Body del `POST /query` | `text: str`, `n_results: int = 5` |
| `ResultItem` | Cada item de la respuesta | `id: str`, `document: str`, `metadata: dict`, `score: float` |

---

### `config.yml` — Configuración Central

```yaml
logging:
  level: "INFO"           # DEBUG | INFO | WARNING | ERROR
  rotation: "10 MB"       # Rota el archivo cuando llega a 10 MB
  retention: "30 days"    # Borra logs más viejos de 30 días
  compression: "gz"       # Comprime los logs rotados
  file: "/app/logs/rag_service.log"  # Ruta dentro del contenedor
  console: true           # También imprime en stdout
```

> **NOTA:** `config.yml` solo maneja logging. Los parámetros de Qdrant y del modelo de embeddings van en variables de entorno (ver sección 8).

---

### `qdrant/migrar_a_qdrant.py` — Carga Inicial de Datos

Script **one-time** (se corre una sola vez para poblar Qdrant). No es parte del servicio en producción.

**Qué hace paso a paso:**
1. Conecta a Qdrant en `localhost:6333`.
2. **Elimina** la colección `rag_biologia` si ya existe (reset total).
3. **Crea** la colección con `384` dimensiones y distancia coseno.
4. Carga `qdrant/secciones_completas.json`.
5. Por cada sección del JSON, construye el texto indexable:
   ```
   {titulo}\n{texto_completo}\nResumen: {resumen}
   ```
6. Genera el embedding con `BAAI/bge-small-en-v1.5`.
7. Inserta en lotes de 100 puntos.

**Formato esperado de `secciones_completas.json`** — cada elemento del array:

```json
{
  "codigo": "SEC-001",
  "titulo": "Clasificación de los seres vivos",
  "texto_completo": "...",
  "resumen": "...",
  "metadatos": {
    "tema": "Taxonomía",
    "fuente": "Libro 10mo Ciencias Naturales"
  },
  "analisis_nlp": {
    "keywords": ["reino", "filo", "clase"]
  },
  "topic_id": 3,
  "curriculum": {
    "tema": "Unidad 1"
  }
}
```

**Payload almacenado en Qdrant por cada punto:**

| Campo | Origen en JSON | Descripción |
|---|---|---|
| `document` | texto construido | **El texto que devuelve la API** al hacer una query |
| `codigo` | `sec.codigo` | Identificador único de la sección |
| `titulo` | `sec.titulo` | Título legible |
| `tema` | `sec.metadatos.tema` | Tema curricular |
| `fuente` | `sec.metadatos.fuente` | Origen del contenido |
| `keywords_nlp` | `sec.analisis_nlp.keywords` | Palabras clave extraídas por NLP |
| `topic_id` | `sec.topic_id` | ID de tópico asignado por BERTopic |
| `curriculum_tema` | `sec.curriculum.tema` | Tema del currículo |

---

## 5. API REST — Endpoints Públicos

El servicio corre en el puerto **8002** (mapeado desde 8000 interno por Docker).

**Base URL (producción local):** `http://localhost:8002`

---

### `POST /query`

**Descripción:** Busca los fragmentos más relevantes para una consulta de texto libre.

**Request Body (JSON):**
```json
{
  "text": "¿Cómo se clasifica un organismo según la taxonomía de Linneo?",
  "n_results": 5
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `text` | `string` | ✅ Sí | — | Texto de la consulta |
| `n_results` | `int` | ❌ No | `5` | Cantidad de resultados a devolver |

**Respuesta exitosa (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document": "Clasificación de los seres vivos\nLos seres vivos se clasifican en dominios...",
    "metadata": {
      "codigo": "SEC-001",
      "titulo": "Clasificación de los seres vivos",
      "tema": "Taxonomía",
      "fuente": "Libro 10mo Ciencias Naturales",
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
| `id` | `string` (UUID) | Identificador del punto en Qdrant |
| `document` | `string` | **Texto completo del fragmento** — esto se inyecta en el prompt del LLM |
| `metadata` | `dict` | Todos los campos del payload excepto `document` |
| `score` | `float` | Similitud coseno (0.0–1.0, mayor = más relevante) |

**Errores:**

| Código | Causa |
|---|---|
| `400` | El campo `text` está vacío o solo tiene espacios |
| `500` | Error interno (Qdrant no disponible, error de embedding, etc.) |

---

### `GET /health`

**Descripción:** Verifica que el servicio esté funcionando y conectado a Qdrant.

**Respuesta exitosa (200):**
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
| `collection` | Nombre de la colección activa |
| `points` | Cantidad de vectores indexados en Qdrant |

> **TIP:** Usar `GET /health` para validar que la migración fue exitosa. Si `points` es `0`, la colección está vacía y hay que re-ejecutar `migrar_a_qdrant.py`.

---

## 6. Modelo de Datos

### Sección (unidad mínima de conocimiento)

Una **sección** es el fragmento de texto indexado. Se almacena en Qdrant como un vector de 384 dimensiones acompañado de su payload.

```
Sección en Qdrant
├── id                  ← UUID único (generado con uuid.uuid4())
├── vector[384]         ← Embedding generado por BAAI/bge-small-en-v1.5
└── payload
    ├── document        ← Texto completo (título + cuerpo + resumen)
    ├── codigo          ← ID único (ej: "SEC-001")
    ├── titulo          ← Título legible
    ├── tema            ← Tema curricular
    ├── fuente          ← Libro o material de origen
    ├── keywords_nlp    ← Lista de palabras clave (generadas por NLP externo)
    ├── topic_id        ← Número de clúster temático (BERTopic)
    └── curriculum_tema ← Unidad curricular
```

### Colección Qdrant

| Parámetro | Valor |
|---|---|
| Nombre | `rag_biologia` |
| Dimensiones | `384` |
| Distancia | Coseno |
| Motor | Qdrant |

---

## 7. Flujo de Datos Completo

### Fase 1: Indexación (one-time setup)

```
qdrant/secciones_completas.json
        │
        ▼
qdrant/migrar_a_qdrant.py
        │
        ├─ Para cada sección:
        │   ├─ Construye texto = titulo + texto_completo + resumen
        │   ├─ fastembed.embed(texto) → vector[384]
        │   └─ Crea PointStruct(id=UUID, vector, payload)
        │
        └─ client.upsert(batch=100) → Qdrant :6333
```

### Fase 2: Consulta en tiempo real

```
POST /query { text: "¿Qué es la mitosis?", n_results: 3 }
        │
        ▼
api.py
        ├─ embedding_model.embed(text) → query_vector[384]
        │
        ├─ qdrant_client.query_points(
        │       collection="rag_biologia",
        │       query=query_vector,
        │       limit=3
        │  )
        │
        └─ Retorna [ResultItem(id, document, metadata, score), ...]
```

---

## 8. Configuración y Variables de Entorno

Las variables de entorno **sobreescriben** los valores leídos de `config.yml`.

| Variable de Entorno | Valor en docker-compose | Default en código | Descripción |
|---|---|---|---|
| `QDRANT_HOST` | `qdrant-server` | `localhost` | Host del servidor Qdrant |
| `QDRANT_PORT` | `6333` | `6333` | Puerto REST de Qdrant |
| `COLLECTION_NAME` | `rag_biologia` | `rag_biologia` | Colección a usar |
| `EMBEDDING_MODEL` | _(no seteada)_ | `BAAI/bge-small-en-v1.5` | Modelo de embeddings |
| `CONFIG_PATH` | _(no seteada)_ | `config.yml` | Ruta al archivo YAML |

> **ADVERTENCIA:** Si cambiás el `EMBEDDING_MODEL`, **debés re-indexar toda la colección** porque el tamaño del vector cambia. Hay que recrear la colección en Qdrant con el nuevo tamaño de dimensiones.

---

## 9. Despliegue con Docker

### Primera vez (migración + build)

```bash
# Paso 1: Levantar SOLO Qdrant para la migración
cd /home/gusgus/Documentos/rag/qdrant
docker compose up -d

# Paso 2: Cargar los datos del JSON a Qdrant
python migrar_a_qdrant.py
# Output esperado: "✅ Carga completada"

# Paso 3: Bajar el Qdrant temporal
docker compose down

# Paso 4: Levantar el sistema completo (qdrant-server + rag-api)
cd /home/gusgus/Documentos/rag
docker compose up --build
```

### Levantar el sistema (uso normal)

```bash
cd /home/gusgus/Documentos/rag
docker compose up -d
```

### Verificar que funciona

```bash
# Healthcheck
curl http://localhost:8002/health

# Consulta de prueba
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"text": "clasificación de los seres vivos", "n_results": 3}'
```

### Puertos expuestos al host

| Servicio | Puerto Host | Puerto Interno | Protocolo |
|---|---|---|---|
| `rag-api` | `8002` | `8000` | HTTP/REST |
| `qdrant-server` | `6333` | `6333` | HTTP/REST ([Dashboard](http://localhost:6333/dashboard)) |
| `qdrant-server` | `6334` | `6334` | gRPC |

### Volúmenes Docker

| Ruta Host | Ruta Contenedor | Propósito |
|---|---|---|
| `.` (raíz del repo) | `/app` | Código fuente (con `--reload` para hot-reload) |
| `./logs` | `/app/logs` | Persistencia de logs |
| `./config.yml` | `/app/config.yml` | Configuración de logging |
| `./qdrant_storage` | `/qdrant/storage` | Datos persistentes de Qdrant |

---

## 10. Dependencias

| Paquete | Versión | Propósito |
|---|---|---|
| `qdrant-client[fastembed]` | latest | Cliente de Qdrant + modelo de embeddings ONNX integrado (sin GPU, sin PyTorch) |
| `fastapi` | latest | Framework web asíncrono |
| `uvicorn` | latest | Servidor ASGI para FastAPI |
| `pyyaml` | latest | Parseo de `config.yml` |
| `loguru` | latest | Logging con rotación, retención y compresión automáticas |

> **NOTA:** El extra `[fastembed]` en `qdrant-client` es crítico: instala el soporte para generar embeddings localmente con ONNX Runtime. Sin ese extra, hay que instalar `fastembed` por separado.

---

## 11. Integración con el Proxy/LLM

El proxy (`/home/gusgus/Documentos/proxy`) actualmente usa **ChromaDB local** en `proxy/services/rag_service.py`, no este servicio Qdrant. Son dos sistemas independientes:

| Sistema | Tecnología | Modelo | Puerto | Estado |
|---|---|---|---|---|
| `proxy/services/rag_service.py` | ChromaDB local | `all-mpnet-base-v2` | — (en proceso) | En uso |
| `rag/api.py` (este repo) | Qdrant + Docker | `BAAI/bge-small-en-v1.5` | `8002` | Producción |

Para integrar **este** servicio en el proxy, modificar `proxy/services/rag_service.py`:

```python
import requests

def get_context_for_prompt(query: str, top_k: int = 3) -> str:
    try:
        resp = requests.post(
            "http://localhost:8002/query",
            json={"text": query, "n_results": top_k},
            timeout=5
        )
        docs = [item["document"] for item in resp.json()]
        if not docs:
            return ""
        context = "\n\n---\n\n".join(docs)
        return f"=== CONTEXTO DE CONOCIMIENTO (RAG) ===\n{context}\n=== FIN ===\n\n"
    except Exception:
        return ""
```

---

## 12. Cómo Extender el Sistema

### Agregar nuevo contenido educativo
1. Actualizar `qdrant/secciones_completas.json` con las nuevas secciones (mismo formato).
2. Correr `python qdrant/migrar_a_qdrant.py` (con Qdrant corriendo).
3. Verificar con `GET /health` que el conteo de puntos aumentó.

### Cambiar el modelo de embeddings
1. Editar `docker-compose.yml`: agregar `EMBEDDING_MODEL=nuevo-modelo`.
2. Actualizar la dimensión del vector en `migrar_a_qdrant.py` (línea `VectorParams(size=???)`).
3. Re-ejecutar la migración completa.

### Agregar un nuevo campo al payload
1. Editar `migrar_a_qdrant.py`: agregar el campo en el dict `payload`.
2. Re-ejecutar la migración.
3. El nuevo campo aparecerá automáticamente en `metadata` de la respuesta de `/query`.

### Agregar filtros por metadata en las queries
La API actual no expone filtros. Para agregar filtrado por `tema` o `fuente`:

1. Extender `QueryRequest` en `api.py`:
   ```python
   class QueryRequest(BaseModel):
       text: str
       n_results: int = 5
       tema: str | None = None  # Nuevo filtro
   ```
2. Construir un `Filter` de Qdrant y pasarlo a `query_points`.

### Actualizar el nivel de logging sin reiniciar
Editar `config.yml` → cambiar `level`. Con Docker y el volumen montado, el cambio se aplica al próximo arranque del contenedor.

---

## 13. Glosario

| Término | Definición |
|---|---|
| **RAG** | Retrieval-Augmented Generation. Técnica donde se recupera contexto relevante de una base de conocimiento antes de enviar el prompt al LLM. |
| **Embedding** | Representación numérica (vector de floats) de un texto que captura su significado semántico. |
| **Qdrant** | Base de datos vectorial open-source, optimizada para búsqueda por similitud semántica. |
| **fastembed** | Librería de Qdrant para generar embeddings localmente usando ONNX (sin GPU, sin PyTorch). |
| **BAAI/bge-small-en-v1.5** | Modelo de embedding ligero (384 dims), rápido, buena relación calidad/tamaño. |
| **Colección** | Equivalente a una "tabla" en Qdrant. Agrupa vectores del mismo dominio. |
| **Coseno** | Métrica de distancia que mide el ángulo entre vectores. Ideal para texto. |
| **top_k / n_results** | Cantidad de resultados más similares a retornar. |
| **PointStruct** | Objeto de Qdrant que encapsula un ID, un vector y su payload. |
| **Payload** | Metadatos adjuntos a un vector en Qdrant (texto, etiquetas, fuente, etc.). |
| **one-time script** | Script que se ejecuta una sola vez para setup inicial, no en producción. |
