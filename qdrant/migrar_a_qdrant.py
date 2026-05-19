# cargar_a_qdrant.py
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding
import uuid

# Configuración
COLLECTION_NAME = "rag_biologia"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
JSON_PATH = "secciones_completas.json"  # Ajusta según tu JSON generado

# Conectar a Qdrant
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Eliminar colección si existe
if client.collection_exists(COLLECTION_NAME):
    client.delete_collection(COLLECTION_NAME)
    print(f"Colección '{COLLECTION_NAME}' eliminada")

# Crear colección con dimensión del modelo (384 para BAAI/bge-small-en-v1.5)
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)
print(f"Colección '{COLLECTION_NAME}' creada")

# Cargar modelo de embeddings (ligero, sin PyTorch)
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Cargar los datos del JSON
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    secciones = json.load(f)

points = []
for sec in secciones:
    # Texto a indexar
    texto_indexable = f"{sec['titulo']}\n{sec.get('texto_completo', '')}"
    if sec.get('resumen'):
        texto_indexable += f"\nResumen: {sec['resumen']}"
    
    # Generar embedding
    embedding = list(embedding_model.embed([texto_indexable]))[0]  # fastembed devuelve generador
    
    # Metadatos
    payload = {
        "document": texto_indexable,   # ← CLAVE IMPORTANTE para que la API lo devuelva
        "codigo": sec.get('codigo', ''),
        "titulo": sec.get('titulo', ''),
        "tema": sec.get('metadatos', {}).get('tema', ''),
        "fuente": sec.get('metadatos', {}).get('fuente', ''),
        "keywords_nlp": sec.get('analisis_nlp', {}).get('keywords', []) if 'analisis_nlp' in sec else [],
        "topic_id": sec.get('topic_id', -1),
        "curriculum_tema": sec.get('curriculum', {}).get('tema', '') if sec.get('curriculum') else '',
    }
    
    points.append(PointStruct(
        id=str(uuid.uuid4()),  # o usar sec['codigo'] si es único
        vector=embedding.tolist(),
        payload=payload
    ))

# Insertar en lotes
batch_size = 100
for i in range(0, len(points), batch_size):
    client.upsert(collection_name=COLLECTION_NAME, points=points[i:i+batch_size])
    print(f"Subidos {min(i+batch_size, len(points))}/{len(points)} puntos")

print("✅ Carga completada")