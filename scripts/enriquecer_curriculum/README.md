# Pipeline de Enriquecimiento de Currículum

Pipeline que transforma un libro de texto en Markdown (`## X.Y`) en secciones enriquecidas con NLP, tópicos BERTopic, matching curricular, y carga a ChromaDB.

**Orquestador:** `pipeline_enriquecer.py` — ejecuta los pasos en orden.

---

## Archivos

| Archivo | Antiguo nombre | Responsabilidad |
|---------|---------------|-----------------|
| `parsear_secciones.py` | `lectura_md.py` | Parsea el .md a lista de secciones |
| `analisis_nlp.py` | `md_to_json.py` | NLP con spaCy: keywords, entidades, tokens |
| `clusterizar_topicos.py` | `secciones_to_temas.py` | BERTopic: clustering semántico |
| `emparejar_curriculum.py` | `match_curriculum.py` | Matching semántico vs currículo oficial |
| `parsear_curriculum.py` | `crear_curriculum_json.py` | Convierte curriculum.md a curriculum.json |
| `cargar_chroma.py` | `json_to_chroma.py` | Carga JSON a ChromaDB |
| `pipeline_enriquecer.py` | `pipeline_completo.py` | Orquestador del pipeline completo |

## Funciones

### `parsear_secciones.py`
- `parsear_secciones_desde_md(ruta_md)` — Parsea el Markdown y retorna lista de dicts con `codigo`, `titulo`, `texto_completo`, `resumen`, `metadatos`.

### `analisis_nlp.py`
- `extraer_keywords(texto, top_n=15)` — Extrae (lema, frecuencia) de sustantivos/adjetivos relevantes.
- `extraer_entidades(texto)` — Extrae entidades nombradas con spaCy NER.
- `guardar_secciones_con_nlp(secciones, output_json_path, top_keywords=10)` — Enriquece con NLP y guarda JSON.

### `clusterizar_topicos.py`
- `clusterizar_secciones_por_topicos(secciones, modelo_embedding_name)` — Agrupa secciones por tópicos con BERTopic. Agrega campo `bertopic` con `topic_id`, `topic_name`, `topic_prob`, `topic_repr`.

### `emparejar_curriculum.py`
- `cargar_curriculum(ruta_json)` — Carga el JSON del currículo.
- `emparejar_secciones_con_curriculum(secciones, curriculum, ...)` — Asigna a cada sección el tema curricular más cercano por similitud coseno usando título + texto_completo + keywords. Agrega campo `curriculum`.

### `parsear_curriculum.py`
- `parsear_curriculum_desde_md(texto)` — Parsea el Markdown del currículo a JSON estructurado con `seccion`, `tema`, `conceptos`, `criterios`.

### `cargar_chroma.py`
- `indexar_en_chroma(ruta_json)` — Indexa las secciones en ChromaDB con metadatos de NLP, BERTopic y currículo.

### `pipeline_enriquecer.py`
- `ejecutar_pipeline_enriquecimiento(ruta_md, json_final)` — Ejecuta el pipeline completo: parseo → NLP → BERTopic → matching curricular → guardado JSON.

## Flujo de datos

```
.md (libro texto)
  │
  ▼
parsear_secciones.py ──► lista de secciones
  │
  ▼
analisis_nlp.py ──► NLP por sección (keywords, entidades, tokens)
  │
  ▼
clusterizar_topicos.py ──► BERTopic clustering
  │
  ▼
emparejar_curriculum.py ──► Matching vs currículo oficial
  │
  ▼
corpus/secciones_completas.json
  │
  ▼
cargar_chroma.py ──► ChromaDB (rag_biologia)
```
