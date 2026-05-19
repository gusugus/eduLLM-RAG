# RAG EduLLM — Guía de Configuración

Servicio de búsqueda semántica (RAG) para contenido educativo de Biología.  
Usa **Qdrant** como base de datos vectorial y **FastAPI** como API REST.

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) instalado y corriendo
- [Docker Compose](https://docs.docker.com/compose/install/) (incluido en Docker Desktop)
- Python 3.11+ (solo para el script de migración)
- Dependencias Python para el script de migración:

```bash
pip install "qdrant-client[fastembed]"
```

---

## Configuración inicial (primera vez)

Estos pasos solo se hacen **una vez** para poblar la base de datos vectorial.

### Paso 1 — Levantar Qdrant solo (para la migración)

```bash
cd qdrant/
docker compose up -d
```

Verificar que está corriendo:
```bash
curl http://localhost:6333/healthz
# Respuesta esperada: {"title":"qdrant - vector search engine"}
```

### Paso 2 — Migrar los datos a Qdrant

Este script lee `qdrant/secciones_completas.json`, genera los embeddings y los carga en Qdrant.

```bash
# Desde la raíz del proyecto
python qdrant/migrar_a_qdrant.py
```

Output esperado:
```
Colección 'rag_biologia' creada
Subidos 100/142 puntos
Subidos 142/142 puntos
✅ Carga completada
```

### Paso 3 — Apagar el Qdrant temporal

```bash
cd qdrant/
docker compose down
```

> Los datos quedan persistidos en `qdrant_storage/` y se reutilizarán en el siguiente paso.

### Paso 4 — Levantar el sistema completo (primera vez, con build)

```bash
# Desde la raíz del proyecto
docker compose up --build
```

Esto construye la imagen del servicio RAG y levanta:
- `qdrant-server` en el puerto `6333`
- `rag-api` en el puerto `8002`

---

## Uso normal (después de la configuración inicial)

```bash
docker compose up -d
```

Para detenerlo:
```bash
docker compose down
```

---

## Verificar que funciona

```bash
# Healthcheck del servicio RAG
curl http://localhost:8002/health
# Respuesta: {"status":"ok","collection":"rag_biologia","points":142}

# Consulta de prueba
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"text": "clasificación de los seres vivos", "n_results": 3}'
```

---

## Actualizar el contenido educativo

Si se modifica `qdrant/secciones_completas.json` con nuevo contenido:

```bash
# 1. Levantar Qdrant temporal
cd qdrant/ && docker compose up -d

# 2. Re-ejecutar la migración (borra y recrea la colección)
python qdrant/migrar_a_qdrant.py

# 3. Bajar Qdrant temporal
docker compose down

# 4. Volver a levantar el sistema completo
cd .. && docker compose up -d
```

---

## Puertos

| Servicio | Puerto |
|---|---|
| RAG API | `http://localhost:8002` |
| Qdrant REST | `http://localhost:6333` |
| Qdrant gRPC | `localhost:6334` |

## Endpoints disponibles

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/query` | Busca fragmentos relevantes por texto |
| `GET` | `/health` | Estado del servicio |

Ver `DOCUMENTACION.md` para detalles completos de la API.
