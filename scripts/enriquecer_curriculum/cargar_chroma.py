import json
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

CHROMA_PATH = Path("chroma_db")
COLLECTION_NAME = "rag_biologia"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

def indexar_en_chroma(ruta_json: str):
    """
    Carga el JSON de secciones enriquecidas a una colección persistente de ChromaDB.
    Cada sección se indexa con su texto completo como documento y metadatos
    de NLP, BERTopic y currículo.
    """
    with open(ruta_json, 'r', encoding='utf-8') as f:
        secciones = json.load(f)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)

    try:
        client.delete_collection(COLLECTION_NAME)
    except:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )

    ids = []
    documentos = []
    metadatas = []

    for sec in secciones:
        doc_id = sec.get('codigo', f"sec_{len(ids)}")
        texto_indexable = f"{sec['titulo']}\n{sec['texto_completo']}"
        if sec.get('resumen'):
            texto_indexable += f"\nResumen: {sec['resumen']}"

        analisis = sec.get('analisis_nlp', {})
        keywords_list = analisis.get('keywords', [])
        keywords_str = ', '.join([k.get('palabra', '') for k in keywords_list if 'palabra' in k])

        entidades_list = analisis.get('entidades', [])
        entidades_str = ', '.join([e.get('texto', '') for e in entidades_list if e.get('texto')])

        curriculum = sec.get('curriculum')
        if curriculum:
            tema_curricular = curriculum.get('tema', '')
            seccion_curricular = curriculum.get('seccion', '')
        else:
            tema_curricular = ''
            seccion_curricular = ''

        topic_id = sec.get('topic_id', -1)
        topic_keywords = sec.get('topic_keywords', [])
        topic_keywords_str = ', '.join(topic_keywords) if isinstance(topic_keywords, list) else ''

        meta = {
            'codigo': sec.get('codigo', ''),
            'titulo': sec.get('titulo', ''),
            'tema': sec.get('metadatos', {}).get('tema', ''),
            'fuente': sec.get('metadatos', {}).get('fuente', ''),
            'keywords_nlp': keywords_str,
            'entidades': entidades_str,
            'topic_id': topic_id,
            'curriculum_tema': tema_curricular,
            'curriculum_seccion': seccion_curricular
        }

        ids.append(doc_id)
        documentos.append(texto_indexable)
        metadatas.append(meta)

    collection.add(
        ids=ids,
        documents=documentos,
        metadatas=metadatas
    )
    print(f"Cargados {len(secciones)} documentos en ChromaDB")
