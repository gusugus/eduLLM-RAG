import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def cargar_curriculum(ruta_json):
    """Carga el archivo JSON del currículo y retorna su contenido como lista."""
    with open(ruta_json, 'r', encoding='utf-8') as f:
        return json.load(f)

secciones_por_revisar = []

def emparejar_secciones_con_curriculum(secciones, curriculum, modelo_embedding_name="paraphrase-multilingual-MiniLM-L12-v2", umbral_concepto=0.6, top_conceptos=1, verbose=True):
    """
    Asigna a cada sección del libro el tema curricular más cercano usando
    similitud coseno entre embeddings de SentenceTransformer.
    Para cada sección, compara su título + resumen + keywords contra los
    conceptos del currículo. Si la similitud supera el umbral, asigna el tema.
    Agrega el campo 'curriculum' a cada sección con:
    - tema, seccion, concepto, conceptos_seleccionados, criterios_seleccionados, score_max
    """
    embedding_model = SentenceTransformer(modelo_embedding_name)

    conceptos_info = []
    for item in curriculum:
        for concepto in item['conceptos']:
            if concepto and concepto.strip() and concepto != '--':
                conceptos_info.append({
                    'texto': concepto,
                    'tema': item['tema'],
                    'seccion': item['seccion'],
                    'criterios': item['criterios']
                })

    textos_conceptos = [c['texto'] for c in conceptos_info]
    embeddings_conceptos = embedding_model.encode(textos_conceptos, show_progress_bar=False)

    for sec in secciones:
        texto_sec = f"{sec['titulo']} {sec.get('texto_completo', '')}"
        palabras_clave = sec.get('metadatos', {}).get('palabras_clave_nlp', [])
        if palabras_clave:
            texto_sec += ' ' + ' '.join(palabras_clave[:15])
        emb_sec = embedding_model.encode([texto_sec])[0]

        sims = cosine_similarity([emb_sec], embeddings_conceptos)[0]
        indices_ordenados = np.argsort(sims)[::-1]

        conceptos_match = []
        temas_score = {}
        for idx in indices_ordenados:
            if sims[idx] >= umbral_concepto and len(conceptos_match) < top_conceptos:
                info = conceptos_info[idx]
                conceptos_match.append({
                    'texto': info['texto'],
                    'similitud': float(sims[idx])
                })
                tema = info['tema']
                temas_score[tema] = temas_score.get(tema, 0) + sims[idx]

        if conceptos_match:
            mejor_tema = max(temas_score, key=temas_score.get) if temas_score else conceptos_match[0]['texto']
            mejor_concepto = max(conceptos_match, key=lambda x: x['similitud'])['texto']
            item_curriculum = next((item for item in curriculum if item['tema'] == mejor_tema), None)
            if item_curriculum:
                criterios_set = set(item_curriculum['criterios'])
                for c in conceptos_match:
                    for crit in item_curriculum['criterios']:
                        if crit.strip() and crit != '--':
                            criterios_set.add(crit)
                bertopic_topic = sec.get('bertopic', None).get('topic_name', None)
                sec['curriculum'] = {
                    'tema': mejor_tema,
                    'seccion': item_curriculum['seccion'],
                    'concepto': mejor_concepto,
                    'conceptos_seleccionados': [c['texto'] for c in conceptos_match],
                    'criterios_seleccionados': list(criterios_set),
                    'score_max': float(max(s['similitud'] for s in conceptos_match)),
                }

                if verbose:
                    print(f"\n{sec['codigo']} -> {mejor_tema[:50]} (max sim={sec['curriculum']['score_max']:.3f})")
                    if bertopic_topic:
                        print(f"   Topico BERTopic: {bertopic_topic}")
                    print(f"   Conceptos asignados:")
                    for i, c in enumerate(conceptos_match, 1):
                        print(f"      {i}. {c['texto'][:80]}... (sim={c['similitud']:.3f})")
            else:
                sec['curriculum'] = None
        else:
            sec['curriculum'] = None
            if verbose:
                print(f"{sec['codigo']} -> ningun concepto supera umbral {umbral_concepto}")

    return secciones
