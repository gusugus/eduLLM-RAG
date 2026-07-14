[← Volver al índice](INDEX.md)

# API Reference — RAG Service

**Base URL:** `/api/rag`
**Archivo fuente:** `api/routes.py`

> **Nota para IA:** Todos los endpoints usan inyección de dependencias de FastAPI (`Depends`) para obtener instancias de `EmbeddingService`, `QdrantService` e `IndexerService`.

---

## Endpoints

### `POST /api/rag/query`

Realiza una búsqueda semántica sobre el corpus indexado en Qdrant.

**Request Body:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `text` | `string` | ✅ | — | Texto de la consulta |
| `n_results` | `int` | ❌ | `5` | Cantidad de resultados a devolver |
| `min_score` | `float` | ❌ | `0.0` | Score mínimo de similitud (0.0–1.0) para filtrar resultados |

**Ejemplo de request:**

```json
{
  "text": "¿Cuáles son las fases de la mitosis?",
  "n_results": 3,
  "min_score": 0.7
}
```

**Response (`200 OK`):** `List[ResultItem]`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `string` | UUID del punto en Qdrant |
| `document` | `string` | Texto completo del fragmento |
| `metadata` | `object` | Metadatos asociados (ver tabla abajo) |
| `score` | `float` | Score de similitud coseno (0.0–1.0) |

**Campos dentro de `metadata`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `codigo` | `string` | Código identificador de la sección |
| `titulo` | `string` | Título de la sección |
| `keywords_nlp` | `string[]` | Palabras clave extraídas por NLP |
| `topic_id` | `int` | ID del tópico (topic modeling) |
| `curriculum_tema` | `string` | Tema del currículo asociado |
| `curriculum_seccion` | `string` | Sección del currículo |
| `curriculum_conceptos_seleccionados` | `string[]` | Conceptos curriculares vinculados |

**Ejemplo de response:**

```json
[
  {
    "id": "a1b2c3d4-...",
    "document": "Mitosis\nLa mitosis es un proceso de división celular...",
    "metadata": {
      "codigo": "BIO-CEL-003",
      "titulo": "Mitosis",
      "keywords_nlp": ["mitosis", "división celular", "cromosomas"],
      "topic_id": 2,
      "curriculum_tema": "Biología Celular",
      "curriculum_seccion": "División Celular",
      "curriculum_conceptos_seleccionados": ["mitosis", "profase", "metafase"]
    },
    "score": 0.892
  }
]
```

**Errores:**

| Código | Detalle |
|--------|---------|
| `400` | `"Texto de consulta vacío"` — cuando `text` está vacío o solo contiene espacios |
| `400` | `"No hay resultados que cumplan el umbral mínimo de similitud"` — cuando no hay resultados con score ≥ min_score |

---

### `GET /api/rag/health`

Health check del servicio. Verifica conexión con Qdrant y estado de la colección.

**Request:** Sin parámetros.

**Response (`200 OK`):**

```json
{
  "status": "ok",
  "collection": "rag_biologia",
  "points": 110
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | `string` | Siempre `"ok"` si la API responde |
| `collection` | `string` | Nombre de la colección activa |
| `points` | `int` | Cantidad de puntos (documentos) indexados |

---

### `POST /api/rag/query-by-tema-and-subtema`

Obtiene documentos filtrados por tema curricular y agrupados por subtema (concepto seleccionado).

**Request Body:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `tema` | `string` | ✅ | Tema curricular exacto (ej: `"Tema 1: La Complejidad de la Vida: Niveles de Taxonomía (pág. 6)"`) |
| `subtemas` | `string[]` | ✅ | Lista de conceptos seleccionados a buscar dentro del tema |

**Ejemplo de request:**
```json
{
  "tema": "Tema 1: La Complejidad de la Vida: Niveles de Taxonomía (pág. 6)",
  "subtemas": ["Aportes de Carlos Linneo a la clasificación", "Sistema de clasificación taxonómica"]
}
```

**Response (`200 OK`):** `List[SubtemaDocumentos]`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `subtema` | `string` | Concepto seleccionado |
| `documentos` | `DocumentoItem[]` | Documentos que matchean ese subtema |

**`DocumentoItem`:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `string` | UUID del punto en Qdrant |
| `document` | `string` | Texto completo del fragmento |

**Ejemplo de response:**
```json
[
  {
    "subtema": "Aportes de Carlos Linneo",
    "documentos": [
      {
        "id": "09f21311-...",
        "document": "1.3 La nomenclatura linneana\nResumen: ..."
      }
    ]
  },
  {
    "subtema": "Sistema de clasificación taxonómica",
    "documentos": []
  }
]
```

**Comportamiento:**
- Filtra documentos donde `curriculum_tema` coincida exactamente con el `tema` proporcionado.
- Dentro de ese filtro, busca documentos cuyos `curriculum_conceptos_seleccionados` contengan al menos uno de los `subtemas`.
- Cada documento se asigna al **primer** subtema que coincida (no se repite entre grupos).

**Errores:**

| Código | Detalle |
|--------|---------|
| `400` | `"Tema vacío"` — cuando `tema` está vacío |
| `400` | `"Lista de subtemas vacía"` — cuando `subtemas` está vacío |

---### `GET /api/rag/admin/info`

Endpoint de administración que devuelve información de diagnóstico del sistema.

> **Nota:** La autenticación por API key (`X-API-Key` header) está actualmente **comentada** en el código fuente. El endpoint es público.

**Request Headers (diseño original, actualmente deshabilitado):**

| Header | Tipo | Descripción |
|--------|------|-------------|
| `X-API-Key` | `string` | API key de administrador |

**Response (`200 OK`):**

```json
{
  "project_root": "/app",
  "qdrant": {
    "host": "qdrant-server",
    "port": 6333,
    "collection": "rag_biologia",
    "points_count": 110
  },
  "default_corpus": {
    "path": "/app/corpus/secciones_completas.json",
    "exists": true
  }
}
```

| Campo | Descripción |
|-------|-------------|
| `project_root` | Ruta raíz detectada del proyecto |
| `qdrant.host` | Host de Qdrant configurado |
| `qdrant.port` | Puerto de Qdrant configurado |
| `qdrant.collection` | Nombre de la colección |
| `qdrant.points_count` | Puntos totales indexados |
| `default_corpus.path` | Ruta al archivo JSON del corpus |
| `default_corpus.exists` | Si el archivo existe en disco |

---

## Modelos Pydantic

Definidos en `core/models.py`:

### `QueryRequest`

```
text: str          — Texto de búsqueda (requerido)
n_results: int = 5 — Cantidad de resultados
```

### `ResultItem`

```
id: str                    — UUID del punto
document: str              — Texto completo
metadata: Dict[str, Any]   — Metadatos del payload
score: float               — Score de similitud
```

### `LoadRequest` (definido en `api/routes.py`)

```
json_path: Optional[str] = None  — Ruta al JSON (usa default si None)
recreate: bool = True             — Si recrear la colección
batch_size: int = 100             — Tamaño de lote para upsert
```

> **Nota para IA:** `LoadRequest` se usa internamente para la función `run_load_task()` en background, pero no hay un endpoint público que lo exponga actualmente.

### `TemaQueryRequest`

```
tema: str              — Tema curricular exacto
subtemas: List[str]    — Conceptos seleccionados a buscar
```

### `DocumentoItem`

```
id: str          — UUID del punto en Qdrant
document: str    — Texto completo del fragmento
```

### `SubtemaDocumentos`

```
subtema: str                  — Concepto seleccionado
documentos: List[DocumentoItem] — Documentos que matchean ese subtema
```

---

## Última revisión

- **Fecha:** 2026-06-08
- **Commit:** `af19733`

## Instrucciones para actualizar este doc

- Si añades un nuevo endpoint, documéntalo siguiendo el formato existente.
- Si modificas los modelos en `core/models.py`, actualiza la sección "Modelos Pydantic".
- Si añades headers de autenticación, actualiza la documentación del endpoint correspondiente.
- Si cambias la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
