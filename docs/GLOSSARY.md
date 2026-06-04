[← Volver al índice](INDEX.md)

# Glosario — RAG Service

Este documento define conceptos técnicos y de dominio utilizados a lo largo del proyecto RAG.

---

## Términos del Dominio RAG / IA

### RAG (Retrieval-Augmented Generation)
Técnica para mejorar las respuestas de un modelo de lenguaje grande (LLM) proporcionándole hechos y fragmentos extraídos de una fuente de datos externa confiable (en este caso, la base de datos de biología) como contexto en la consulta (prompt).

### Vector de Embedding (Incrustación Vectorial)
Representación numérica (un array de números reales de coma flotante) de un fragmento de texto. Captura el significado semántico del texto. Textos con significados similares tienen vectores cercanos en el espacio vectorial.

### Similitud de Coseno (Cosine Similarity)
Métrica utilizada para medir la similitud semántica entre dos vectores. Compara la dirección de los vectores en un espacio multidimensional. Varía entre -1.0 y 1.0 (donde 1.0 es idéntico).

### Qdrant
Base de datos vectorial especializada para almacenar embeddings y realizar búsquedas rápidas utilizando algoritmos de vecinos más cercanos (ANN - Approximate Nearest Neighbors).

### FastEmbed
Librería ligera de Python mantenida por Qdrant para la generación rápida de embeddings de texto, diseñada para ejecutarse sin requerir infraestructuras complejas de GPU.

### BAAI/bge-small-en-v1.5
El modelo de embeddings de texto utilizado por defecto en el sistema. Genera vectores de 384 dimensiones.

---

## Términos del Dominio Curricular / Proyecto

### Corpus
El conjunto total de documentos o secciones educativas estructuradas en formato JSON (`corpus/secciones_completas.json`) que representan el conocimiento disponible para indexar.

### Sección
Unidad mínima de texto indexable en el corpus. Posee un código único, título, texto completo, resumen y metadatos curriculares.

### Topic ID
Identificador asignado a cada sección mediante un modelado de tópicos previo (Topic Modeling), permitiendo agrupar textos temáticamente similares.

---

## Última revisión

- **Fecha:** 2026-05-24
- **Commit:** `5cfbd82`

## Instrucciones para actualizar este doc

- Si el proyecto se extiende a otros modelos de lenguaje o nuevas técnicas de recuperación (e.g. Hybrid Search, Reranking), añade sus definiciones.
- Si cambia el modelo de embeddings, actualiza su definición.
- Si cambia la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
