import json
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN

from sklearn.feature_extraction.text import CountVectorizer
from bertopic.representation import KeyBERTInspired
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords

stop_words_es = set(stopwords.words('spanish')) | {
    'qué', 'cómo', 'cuándo', 'dónde', 'porque', 'pero', 'sino', 'más', 'menos',
    'muy', 'mucho', 'poco', 'tan', 'tanto', 'tras', 'ante', 'bajo', 'cabe',
    'versus', 'vía', 'etc', 'etcétera', 'además', 'incluso', 'respecto'
}

def clusterizar_secciones_por_topicos(secciones: list, modelo_embedding_name="paraphrase-multilingual-MiniLM-L12-v2"):
    """
    Agrupa las secciones en tópicos semánticos usando BERTopic.
    Usa SentenceTransformer para embeddings, UMAP para reducción de dimensionalidad
    y HDBSCAN para clustering.
    Retorna (secciones, topic_model) con el campo 'bertopic' agregado a cada sección
    contiendo topic_id, topic_name, topic_prob y topic_repr.
    """
    vectorizer_model = CountVectorizer(
        ngram_range=(1, 2),
        stop_words=list(stop_words_es),
        min_df=2,
        max_df=0.85,
        lowercase=True
    )

    textos = [sec.get('texto_completo', '') for sec in secciones]
    textos_validos = [t for t in textos if t.strip()]
    if not textos_validos:
        print("No hay textos válidos para analizar.")
        return secciones, None

    embedding_model = SentenceTransformer(modelo_embedding_name)

    umap_model = UMAP(n_neighbors=5, n_components=5, min_dist=0.0, metric='cosine', random_state=42)
    hdbscan_model = HDBSCAN(min_cluster_size=2, min_samples=1, metric='euclidean', prediction_data=True)
    representation_model = KeyBERTInspired()

    topic_model = BERTopic(
        embedding_model=embedding_model,
        language="spanish",
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        representation_model=representation_model,
        verbose=True,
    )

    topics, probs = topic_model.fit_transform(textos_validos)

    if np.all(np.array(topics) == -1):
        print("Todos los documentos fueron clasificados como ruido. Asignando tema único.")
        new_topics = [0] * len(topics)
        topic_model.set_topic_labels({0: "tema_unico"})
    else:
        if -1 in topics:
            print(f"Reduciendo {np.sum(np.array(topics) == -1)} outliers...")
            try:
                new_topics = topic_model.reduce_outliers(textos_validos, topics, strategy="embeddings")
            except Exception as e:
                print(f"Error al reducir outliers: {e}. Manteniendo originales.")
                new_topics = topics
        else:
            print("No hay documentos ruido. Manteniendo tópicos originales.")
            new_topics = topics

    indices_validos = [i for i, sec in enumerate(secciones) if sec.get('texto_completo', '').strip()]

    topic_names_map = {}
    topic_info = topic_model.get_topic_info()

    for _, row in topic_info.iterrows():
        tid = row['Topic']
        if tid != -1:
            name = row['Name']
            if '_' in name and name.split('_')[0].isdigit():
                name = '_'.join(name.split('_')[1:])
            topic_names_map[tid] = name
    topic_names_map[-1] = "Ruido"

    indices_validos = [i for i, sec in enumerate(secciones) if sec.get('texto_completo', '').strip()]
    for idx_original, topic_id in zip(indices_validos, new_topics):
        prob_value = probs[idx_original] if probs is not None else None
        try:
            repr_list = topic_info[topic_info['Topic'] == topic_id]['Representation'].values[0]
        except IndexError:
            repr_list = []

        secciones[idx_original]['bertopic'] = {
            'topic_id': int(topic_id),
            'topic_name': topic_names_map.get(topic_id, f"topic_{topic_id}"),
            'topic_prob': float(prob_value) if prob_value is not None else None,
            'topic_repr': repr_list
        }

    for sec in secciones:
        if 'bertopic' not in sec:
            sec['bertopic'] = {
                'topic_id': -1,
                'topic_name': 'Sin texto',
                'topic_prob': None
            }
            sec['topic_bertopic'] = -1
            sec['topic_name'] = 'Sin texto'

    print("\nInformación de tópicos:")
    print(topic_info)

    return secciones, topic_model
