"""
Pipeline completo de enriquecimiento de currículo.
Orquesta: parseo de Markdown → NLP → BERTopic → matching curricular → guardado JSON.
"""
from parsear_secciones import parsear_secciones_desde_md
from analisis_nlp import extraer_keywords, extraer_entidades, nlp
from clusterizar_topicos import clusterizar_secciones_por_topicos
from emparejar_curriculum import emparejar_secciones_con_curriculum, cargar_curriculum
import json

def ejecutar_pipeline_enriquecimiento(ruta_md, json_final='secciones_completas.json'):
    """
    Ejecuta el pipeline completo de enriquecimiento:
    1. Parsea el Markdown a secciones
    2. Aplica NLP (keywords, entidades, tokens)
    3. Asigna tópicos con BERTopic
    4. Hace matching contra el currículo oficial
    5. Guarda el JSON final (sin analisis_nlp para reducir tamaño)
    """
    print("1. Parseando Markdown...")
    secciones = parsear_secciones_desde_md(ruta_md)
    print(f"   -> {len(secciones)} secciones encontradas.")

    print("2. Aplicando NLP (keywords, entidades)...")
    for sec in secciones:
        texto = sec['texto_completo']
        keywords = extraer_keywords(texto, top_n=15)
        entidades = extraer_entidades(texto)
        sec['analisis_nlp'] = {
            'keywords': [{'palabra': k, 'frecuencia': f} for k, f in keywords],
            'entidades': entidades,
            'num_tokens': len(nlp(texto))
        }
        sec['metadatos']['palabras_clave_nlp'] = [k for k, _ in keywords]

    print("3. Asignando topicos con BERTopic...")
    secciones_con_temas, _ = clusterizar_secciones_por_topicos(secciones)

    print("4. Cargando curriculum y haciendo matching...")
    curriculum = cargar_curriculum('/home/gusgus/Documentos/rag/corpus/curriculum.json')
    secciones_final = emparejar_secciones_con_curriculum(secciones_con_temas, curriculum)

    print("4.5. Eliminando analisis_nlp del JSON final (para reducir tamano)...")
    for sec in secciones_final:
        if 'analisis_nlp' in sec:
            del sec['analisis_nlp']
        if sec['curriculum'] is not None and 'score_max' in sec['curriculum']:
            del sec['curriculum']['score_max']

    json_final = '/home/gusgus/Documentos/rag/corpus/secciones_completas.json'
    print(f'5. Guardando JSON final en {json_final}')
    with open(json_final, 'w', encoding='utf-8') as f:
        json.dump(secciones_final, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    ejecutar_pipeline_enriquecimiento('/home/gusgus/Documentos/rag/corpus/libro_10_ciencias_naturales.md')
