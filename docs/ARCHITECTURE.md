[← Volver al índice](INDEX.md)

# Arquitectura — RAG Service

## Visión general

El servicio sigue una arquitectura de **3 capas** con inyección de dependencias nativa de FastAPI:

```
┌──────────────────────────────────────────────────┐
│                    main.py                       │
│  App FastAPI + Middlewares + Telemetría           │
└────────────────────┬─────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │      api/routes.py    │   ← Capa de presentación
         │  (Endpoints REST)     │
         └───────────┬───────────┘
                     │ Depends()
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────┐   ┌────────────┐   ┌──────────┐
│Embedding│   │  Qdrant    │   │ Indexer  │  ← Capa de servicios
│Service  │   │  Service   │   │ Service  │
└────────┘   └────────────┘   └──────────┘
    │                │
    ▼                ▼
┌────────┐   ┌────────────┐
│FastEmbed│   │  Qdrant DB │   ← Capa de infraestructura
└────────┘   └────────────┘
```

## Diagrama de componentes (Mermaid)

```mermaid
graph TD
    subgraph "Entrada"
        CLIENT["Cliente HTTP"]
    end

    subgraph "main.py"
        MW_TRUST["TrustedHostMiddleware"]
        MW_GUARD["pywebguard (FastAPIGuard)"]
        OTEL["OpenTelemetry"]
    end

    subgraph "api/"
        ROUTES["routes.py — APIRouter"]
    end

    subgraph "core/"
        CONFIG["config.py — Settings"]
        LOGGING["logging_config.py — Loguru"]
        MODELS["models.py — Pydantic"]
    end

    subgraph "services/"
        EMBED["EmbeddingService (singleton)"]
        QDRANT_SVC["QdrantService"]
        INDEXER["IndexerService"]
    end

    subgraph "Infraestructura"
        QDRANT_DB["Qdrant Server"]
        FASTEMBED["FastEmbed Model"]
        ALLOY["Grafana Alloy"]
    end

    CLIENT -->|HTTP| MW_TRUST
    MW_TRUST --> MW_GUARD
    MW_GUARD --> ROUTES
    ROUTES -->|Depends| EMBED
    ROUTES -->|Depends| QDRANT_SVC
    ROUTES -->|Depends| INDEXER
    INDEXER --> EMBED
    INDEXER --> QDRANT_SVC
    EMBED --> FASTEMBED
    QDRANT_SVC --> QDRANT_DB
    OTEL -->|OTLP/gRPC| ALLOY
    CONFIG -.->|lee| EMBED
    CONFIG -.->|lee| QDRANT_SVC
    CONFIG -.->|lee| LOGGING
```

## Módulos

### `main.py` — Punto de entrada

Responsabilidad: Crear la app FastAPI, configurar middlewares y telemetría.

| Componente | Función |
|-----------|---------|
| `configure_telemetry()` | Configura OpenTelemetry (trazas + logs) hacia Alloy vía gRPC |
| `security_config` | Define reglas de pywebguard (IP whitelist, rate limiting) |
| `TrustedHostMiddleware` | Restringe hosts permitidos |

---

### `api/` — Capa de presentación

| Archivo | Responsabilidad |
|---------|----------------|
| `routes.py` | Define todos los endpoints REST bajo el prefijo `/api/rag`. Usa inyección de dependencias de FastAPI para obtener servicios. |

> **Nota para IA:** Los endpoints se documentan en detalle en [API.md](API.md).

---

### `core/` — Configuración y modelos

| Archivo | Responsabilidad |
|---------|----------------|
| `config.py` | Singleton `Settings` que carga `config.yml` y sobrescribe con variables de entorno. Todas las configuraciones se leen desde aquí. |
| `logging_config.py` | Configura Loguru con salida a consola y archivo rotativo. |
| `models.py` | Define `QueryRequest` y `ResultItem` (modelos Pydantic para request/response). |

---

### `services/` — Lógica de negocio

| Archivo | Responsabilidad |
|---------|----------------|
| `embedding_service.py` | Singleton que carga el modelo FastEmbed (lazy init en `__init__` con flag `_initialized`) y expone `embed()` / `embed_one()`. |
| `qdrant_service.py` | CRUD contra Qdrant: crear/eliminar colecciones, upsert de puntos, búsqueda vectorial. |
| `indexer_service.py` | Orquesta la carga de datos: lee JSON → genera embeddings → inserta en Qdrant en lotes. |

---

### `scripts/` — Herramientas CLI

| Archivo | Responsabilidad |
|---------|----------------|
| `load_to_qdrant.py` | Script CLI con `argparse` para carga masiva de datos del corpus a Qdrant. Resuelve la raíz del proyecto dinámicamente para imports absolutos. |
| `enriquecer_curriculum/` | Pipeline de enriquecimiento de secciones educativas (ver su [README](../scripts/enriquecer_curriculum/README.md)). |

---

### `corpus/` — Datos fuente

| Archivo | Responsabilidad |
|---------|----------------|
| `secciones_completas.json` | JSON con secciones educativas de biología (título, texto, resumen, metadatos, curriculum). |

## Flujo de datos: Consulta de búsqueda

```mermaid
sequenceDiagram
    participant C as Cliente
    participant R as routes.py
    participant E as EmbeddingService
    participant Q as QdrantService
    participant DB as Qdrant DB

    C->>R: POST /api/rag/query {text, n_results}
    R->>R: Validar texto no vacío
    R->>E: embed_one(text)
    E-->>R: vector[384]
    R->>Q: search(vector, limit)
    Q->>DB: query_points(collection, vector)
    DB-->>Q: ScoredPoints[]
    Q-->>R: results
    R-->>C: [{id, document, metadata, score}]
```

## Flujo de datos: Carga de corpus

```mermaid
sequenceDiagram
    participant S as Script/Admin
    participant I as IndexerService
    participant E as EmbeddingService
    participant Q as QdrantService
    participant DB as Qdrant DB

    S->>I: load_from_json(path, recreate)
    I->>Q: delete_collection() + create_collection()
    Q->>DB: DELETE + CREATE collection
    loop Por cada sección del JSON
        I->>E: embed_one(titulo + texto + resumen)
        E-->>I: vector[384]
        I->>I: Construir PointStruct(uuid, vector, payload)
    end
    I->>Q: upsert_points(points, batch_size=100)
    Q->>DB: upsert en lotes
```

## Middleware y seguridad

El orden de ejecución de los middlewares es (de afuera hacia adentro):

1. **TrustedHostMiddleware** — Rechaza requests con `Host` no permitido
2. **FastAPIGuard (pywebguard)** — IP whitelist/blacklist + rate limiting (100 req/min, burst 20, auto-ban a 200)

> Para configuración detallada de seguridad, ver la sección `security_config` en `main.py`.

## Observabilidad

| Señal | Transporte | Destino |
|-------|-----------|---------|
| Trazas (traces) | OTLP/gRPC `:4317` | Grafana Alloy |
| Logs | OTLP/gRPC `:4317` | Grafana Alloy |
| Logs locales | Archivo rotativo | `./logs/rag_service.log` |

> **Nota para IA:** La telemetría se configura en `main.py → configure_telemetry()`. El endpoint de Alloy es `alloy:4317` y requiere la red Docker `observability-net`.

---

## Última revisión

- **Fecha:** 2026-06-12
- **Commit:** `(pendiente)`

## Instrucciones para actualizar este doc

- Si añades un nuevo módulo o servicio, agrega una fila en la tabla correspondiente.
- Si cambias el flujo de datos, actualiza los diagramas Mermaid.
- Si modificas middlewares o telemetría, actualiza las secciones respectivas.
- Si cambia la estructura de archivos, actualiza [INDEX.md](INDEX.md).

[← Volver al índice](INDEX.md)
