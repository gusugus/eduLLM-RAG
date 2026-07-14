import json
import spacy
from collections import Counter
from typing import List, Dict
from parsear_secciones import parsear_secciones_desde_md

nlp = spacy.load("es_core_news_md")

STOPWORDS_DOMINIO = {
    'ser', 'estar', 'tener', 'haber', 'hacer', 'decir', 'ir', 'ver', 'dar',
    'cosa', 'cual', 'otro', 'mismo', 'tanto', 'vez', 'así', 'sino', 'además',
    'incluir', 'pequeño', 'común', 'distinguir', 'incluido', 'propio', 'bueno',
    'gran', 'mayor', 'primero', 'nuevo', 'último', 'largo', 'corto', 'de', "en",
      "se", "son", "que",
      "el", "la", "los", "las",
}

def extraer_keywords(texto: str, top_n=15) -> List[tuple]:
    """
    Extrae las palabras clave más relevantes de un texto usando spaCy.
    Filtra sustantivos (NOUN, PROPN) y adjetivos largos (>3 letras),
    excluyendo stopwords y palabras de menos de 3 caracteres.
    Retorna lista de (lema, frecuencia).
    """
    doc = nlp(texto)
    palabras = []
    for token in doc:
        if token.is_stop or token.is_punct or not token.is_alpha:
            continue
        if len(token.text) < 3:
            continue
        lema = token.lemma_.lower()
        if lema in STOPWORDS_DOMINIO:
            continue
        if token.pos_ in ('NOUN', 'PROPN'):
            palabras.append(lema)
        elif token.pos_ == 'ADJ' and len(lema) > 3:
            palabras.append(lema)
    contador = Counter(palabras)
    resultado = [(p, f) for p, f in contador.most_common(top_n) if ' ' not in p]
    return resultado

def extraer_entidades(texto: str) -> List[Dict]:
    """
    Extrae entidades nombradas (personas, lugares, organizaciones, etc.)
    usando el NER de spaCy. Retorna lista de dicts con 'texto', 'label' y 'explicacion'.
    """
    doc = nlp(texto)
    entidades = []
    for ent in doc.ents:
        entidades.append({
            'texto': ent.text,
            'label': ent.label_,
            'explicacion': spacy.explain(ent.label_)
        })
    return entidades

def guardar_secciones_con_nlp(secciones: List[Dict], output_json_path: str, top_keywords=10):
    """
    Enriquece cada sección con análisis NLP (keywords, entidades, num_tokens)
    y guarda el resultado como JSON.
    """
    for sec in secciones:
        texto = sec['texto_completo']
        keywords = extraer_keywords(texto, top_n=top_keywords)
        entidades = extraer_entidades(texto)
        sec['analisis_nlp'] = {
            'keywords': [k for k, _ in keywords],
            'entidades': [e['texto'] for e in entidades[:5]],
            'num_tokens': len(nlp(texto))
        }
        sec['metadatos']['palabras_clave_nlp'] = [k for k, _ in keywords]

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(secciones, f, indent=2, ensure_ascii=False)
    print(f"Guardado JSON con {len(secciones)} secciones en {output_json_path}")

if __name__ == '__main__':
    secciones = parsear_secciones_desde_md('documento.md')
    guardar_secciones_con_nlp(secciones, 'secciones_enriquecidas.json')
