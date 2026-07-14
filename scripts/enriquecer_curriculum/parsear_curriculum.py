import re
import json

def parsear_curriculum_desde_md(texto):
    """
    Parsea el Markdown del currículo oficial (secciones ###, temas ####,
    listas de conceptos y criterios) y retorna una lista de dicts
    con 'seccion', 'tema', 'conceptos' y 'criterios'.
    """
    secciones_raw = re.split(r'(?=### Sección \d+:)', texto)
    resultados = []
    for bloque in secciones_raw:
        if not bloque.strip():
            continue
        m_seccion = re.search(r'### (Sección \d+:.*?)\n', bloque)
        if not m_seccion:
            continue
        nombre_seccion = m_seccion.group(1).strip()
        temas_raw = re.split(r'(?=#### Tema \d+:)', bloque)
        for tema_bloque in temas_raw:
            if not tema_bloque.strip() or not tema_bloque.startswith('####'):
                continue
            m_tema = re.search(r'#### (Tema \d+:.*?)(?:\n|$)', tema_bloque)
            if not m_tema:
                continue
            titulo_tema = m_tema.group(1).strip()
            conceptos = []
            criterios = []
            patron_conceptos = r'\*\*Conceptos obligatorios[^\*]*\*\*:?\s*\n(.*?)(?=\*\*Criterios de evaluación|\Z)'
            m_conceptos = re.search(patron_conceptos, tema_bloque, re.DOTALL)
            if m_conceptos:
                texto_conceptos = m_conceptos.group(1)
                conceptos = re.findall(r'^\s*-\s*(.*?)$', texto_conceptos, re.MULTILINE)
            patron_criterios = r'\*\*Criterios de evaluación[^\*]*\*\*:?\s*\n(.*?)(?=\n###|\n####|\n\*\*|\Z)'
            m_criterios = re.search(patron_criterios, tema_bloque, re.DOTALL)
            if m_criterios:
                texto_criterios = m_criterios.group(1)
                criterios = re.findall(r'^\s*-\s*(.*?)$', texto_criterios, re.MULTILINE)
            resultados.append({
                "seccion": nombre_seccion,
                "tema": titulo_tema,
                "conceptos": conceptos,
                "criterios": criterios
            })
    return resultados

if __name__ == "__main__":
    with open('/home/gusgus/Documentos/rag/corpus/curriculum.md', 'r', encoding='utf-8') as f:
        raw = f.read()
    curriculum = parsear_curriculum_desde_md(raw)
    with open('/home/gusgus/Documentos/rag/corpus/curriculum.json', 'w', encoding='utf-8') as f:
        json.dump(curriculum, f, indent=2, ensure_ascii=False)
    print(f"curriculum.json generado con {len(curriculum)} temas.")
