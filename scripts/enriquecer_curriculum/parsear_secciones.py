import re
import yaml
from typing import List, Dict

def parsear_secciones_desde_md(ruta_md: str) -> List[Dict]:
    """
    Parsea un archivo Markdown con secciones numeradas ## X.Y.
    Retorna lista de diccionarios con:
        - codigo: str (ej. "1.1")
        - titulo: str
        - texto_completo: str (contenido hasta siguiente sección)
        - resumen: str o None (primera línea que empiece con 'Resumen:')
        - metadatos: dict (bloque YAML entre ---, o {} si no existe)
    """
    with open(ruta_md, 'r', encoding='utf-8') as f:
        lineas = f.readlines()

    secciones = []
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        if re.match(r'^##\s+\d+\.\d+', linea):
            codigo = linea.split()[1]
            titulo = linea[3:].strip()
            texto_lines = []
            j = i + 1
            metadatos = {}
            while j < len(lineas):
                if re.match(r'^##\s+\d+\.\d+', lineas[j].strip()):
                    break
                if lineas[j].strip() == '---' and j+1 < len(lineas):
                    yaml_lines = []
                    j += 1
                    while j < len(lineas) and lineas[j].strip() != '---':
                        yaml_lines.append(lineas[j])
                        j += 1
                    j += 1
                    try:
                        metadatos = yaml.safe_load('\n'.join(yaml_lines)) or {}
                    except:
                        metadatos = {}
                    continue
                texto_lines.append(lineas[j])
                j += 1
            texto_completo = '\n'.join(texto_lines).strip()
            resumen = None
            for line in texto_completo.splitlines():
                if line.startswith('Resumen:'):
                    resumen = line[8:].strip()
                    break
            secciones.append({
                'codigo': codigo,
                'titulo': titulo,
                'texto_completo': texto_completo,
                'resumen': resumen,
                'metadatos': metadatos
            })
            i = j
        else:
            i += 1
    return secciones
