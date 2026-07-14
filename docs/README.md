[← Volver al índice](INDEX.md)

# RAG Service — eduLLM

Microservicio de **Retrieval-Augmented Generation (RAG)** construido con FastAPI y Qdrant. Proporciona búsqueda semántica sobre contenido educativo de biología, permitiendo a otros servicios (como un LLM generador de quizzes) recuperar fragmentos relevantes del currículo mediante similitud vectorial.

## Propósito

| Qué hace | Qué NO hace |
|----------|-------------|
| Recibe una consulta de texto libre | No genera respuestas con LLM |
| Genera embeddings con `BAAI/bge-small-en-v1.5` | No almacena usuarios ni sesiones |
| Busca los `n` documentos más similares en Qdrant | No expone interfaz gráfica |
| Devuelve fragmentos ranqueados por score de coseno | No gestiona autenticación de usuarios |

## Stack tecnológico

- **Framework:** FastAPI + Uvicorn
- **Base de datos vectorial:** Qdrant
- **Embeddings:** FastEmbed (`BAAI/bge-small-en-v1.5`)
- **Seguridad:** pywebguard (rate limiting, IP filtering)
- **Observabilidad:** OpenTelemetry → Grafana Alloy (trazas + logs)
- **Logging:** Loguru + structlog
- **Contenedores:** Docker + Docker Compose

## Setup rápido

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose
- (Opcional) Red Docker `observability-net` para telemetría

### 1. Clonar e instalar dependencias

```bash
git clone <repo-url>
cd rag
pip install -r requirements.txt
```

### 2. Levantar con Docker Compose (recomendado)

```bash
# Crear red de observabilidad (solo la primera vez)
docker network create observability-net

# Levantar servicios
docker compose up -d
```

Esto levanta:
- **qdrant-server** en `localhost:6333`
- **rag-api** en `localhost:8002` (mapeado desde el puerto interno 8000)

### 3. Ejecución local (sin Docker)

```bash
# Levantar Qdrant manualmente
docker run -p 6333:6333 qdrant/qdrant:latest

# Ejecutar la API
python main.py
```

### 4. Cargar datos del corpus

```bash
# Desde dentro del contenedor o localmente
python scripts/load_to_qdrant.py --json corpus/secciones_completas.json --recreate
```

### 5. Verificar que funciona

```bash
curl http://localhost:8002/api/rag/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "collection": "rag_biologia",
  "points": 110
}
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Host del servidor Qdrant |
| `QDRANT_PORT` | `6333` | Puerto del servidor Qdrant |
| `COLLECTION_NAME` | `rag_biologia` | Nombre de la colección en Qdrant |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Modelo de embeddings |
| `ADMIN_API_KEY` | `mi-clave-secreta-para-cargar-datos` | API key para endpoints admin |
| `CONFIG_PATH` | `config.yml` | Ruta al archivo de configuración |

## Estructura del proyecto

```
rag/
├── main.py                 # Punto de entrada, configuración de app
├── config.yml              # Configuración YAML (Qdrant, logging, embedding)
├── requirements.txt        # Dependencias Python
├── Dockerfile              # Imagen Docker
├── docker-compose.yml      # Orquestación de servicios
├── api/
│   └── routes.py           # Definición de endpoints REST
├── core/
│   ├── config.py           # Carga de configuración (YAML + env vars)
│   ├── logging_config.py   # Setup de Loguru
│   └── models.py           # Modelos Pydantic (request/response)
├── services/
│   ├── embedding_service.py  # Generación de embeddings (singleton)
│   ├── qdrant_service.py     # Operaciones CRUD contra Qdrant
│   └── indexer_service.py    # Orquestación de carga de datos
├── scripts/
│   ├── load_to_qdrant.py   # CLI para carga masiva de datos
│   └── enriquecer_curriculum/   # Pipeline de enriquecimiento (NLP, BERTopic, matching curricular)
├── corpus/
│   └── secciones_completas.json  # Datos educativos fuente
└── .github/workflows/
    └── telegram-notify.yml  # Notificaciones de PR por Telegram
```

> Para detalles de cada módulo, ver [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Última revisión

- **Fecha:** 2026-06-12
- **Commit:** `(pendiente)`

[← Volver al índice](INDEX.md)
