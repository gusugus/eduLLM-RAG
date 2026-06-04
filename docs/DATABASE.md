[← Volver al índice](INDEX.md)

# Base de datos — Qdrant

El servicio utiliza **Qdrant** como base de datos vectorial. No hay base de datos relacional; todos los datos se almacenan como puntos (vectores + payload) en colecciones de Qdrant.

> **Nota para IA:** Las operaciones de base de datos se concentran en `services/qdrant_service.py`. La lógica de transformación de datos vive en `services/indexer_service.py`.

---

## Colección principal

| Propiedad | Valor |
|-----------|-------|
| **Nombre** | `rag_biologia` (configurable vía `COLLECTION_NAME`) |
| **Distancia** | Coseno (`Distance.COSINE`) |
| **Dimensión del vector** | 384 (determinado por el modelo `BAAI/bge-small-en-v1.5`) |
| **IDs** | UUID v4 (generados en cada carga) |

---

## Esquema del payload

Cada punto almacenado en Qdrant contiene los siguientes campos en su payload:

| Campo | Tipo | Origen | Descripción |
|-------|------|--------|-------------|
| `document` | `string` | Concatenación de `titulo` + `texto_completo` + `resumen` | Texto completo indexable. Es lo que se retorna al cliente. |
| `codigo` | `string` | `sec.codigo` | Código identificador de la sección educativa |
| `titulo` | `string` | `sec.titulo` | Título de la sección |
| `keywords_nlp` | `string[]` | `sec.metadatos.palabras_clave_nlp` | Palabras clave extraídas automáticamente por NLP |
| `topic_id` | `int` | `sec.topic_id` | ID de tópico asignado por topic modeling |
| `curriculum_tema` | `string` | `sec.curriculum.tema` | Tema del currículo oficial |
| `curriculum_seccion` | `string` | `sec.curriculum.seccion` | Sección del currículo oficial |
| `curriculum_conceptos_seleccionados` | `string[]` | `sec.curriculum.conceptos_seleccionados` | Conceptos curriculares vinculados a la sección |

---

## Esquema del JSON fuente

El archivo `corpus/secciones_completas.json` es un array de objetos con la siguiente estructura:

```
sección {
  codigo: string
  titulo: string
  texto_completo: string
  resumen: string (opcional)
  topic_id: int
  metadatos: {
    palabras_clave_nlp: string[]
  }
  curriculum: {
    tema: string
    seccion: string
    conceptos_seleccionados: string[]
  }
}
```

---

## Generación del vector

El texto que se vectoriza es una concatenación:

```
"{titulo}\n{texto_completo}\nResumen: {resumen}"
```

- Si no hay `resumen`, se omite la última línea.
- El modelo `BAAI/bge-small-en-v1.5` genera un vector de **384 dimensiones**.

---

## Proceso de carga

Ver diagrama completo en [ARCHITECTURE.md](ARCHITECTURE.md#flujo-de-datos-carga-de-corpus).

Pasos resumidos:

1. Leer JSON desde `corpus/secciones_completas.json`
2. (Opcional) Recrear colección: eliminar → crear con `vector_size=384`
3. Para cada sección: concatenar texto → generar embedding → construir `PointStruct`
4. Insertar en Qdrant en lotes de 100 puntos (`upsert_points`)

**Herramientas de carga:**

| Herramienta | Archivo | Uso |
|-------------|---------|-----|
| Script CLI | `scripts/load_to_qdrant.py` | `python scripts/load_to_qdrant.py --json <ruta> --recreate` |
| Background task | `api/routes.py → run_load_task()` | Función interna (sin endpoint público actualmente) |

---

## Persistencia y almacenamiento

| Aspecto | Detalle |
|---------|---------|
| **Almacenamiento en Docker** | Volumen `./qdrant_storage:/qdrant/storage` |
| **Backup** | Archivo `qdrant_storage.7z` incluido en el repo (`.gitignore` excluye `*.7z`) |
| **Migración** | Al recrear la colección, todos los puntos se eliminan y se recargan |

> ⚠️ **Importante:** No existe migración incremental. Cada carga con `--recreate` destruye la colección y la reconstruye.

---

## Última revisión

- **Fecha:** 2026-05-24
- **Commit:** `5cfbd82`

## Instrucciones para actualizar este doc

- Si cambias los campos del payload en `indexer_service.py`, actualiza la tabla de esquema.
- Si cambias el modelo de embeddings, actualiza la dimensión del vector.
- Si añades filtros o índices en Qdrant, documéntalo aquí.
- Si cambias la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
