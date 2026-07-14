#!/usr/bin/env python3
"""
Extract curriculum topics and sections from secciones_completas.json
and store the mapping in PostgreSQL table comun.admi_parametro
with key = 'CLASIFICACION_TEMAS'
"""

import json
import os
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv  # pip install python-dotenv

# Cargar variables de entorno (opcional)
load_dotenv()

# Configuración de base de datos (ajusta según tu entorno)
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}
import re

def build_topic_mapping(input_file='corpus/secciones_completas.json'):
    """Construye mapping {tema_limpio: [concepto1, concepto2, ...]} desde el JSON"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    mapping = {}
    for item in data:
        curriculum = item.get('curriculum', {})
        tema_original = curriculum.get('tema')  # ← Corregido: obtener el tema
        conceptos_seleccionados = curriculum.get('conceptos_seleccionados', [])
        
        if not tema_original or not conceptos_seleccionados:
            continue
        
        # Limpiar el tema: eliminar (pág. XX) o (página XX)
        tema_limpio = re.sub(r'\s*\(p[áa]g(?:ina)?\.?\s*\d+\)', '', tema_original)
        tema_limpio = re.sub(r'\s+', ' ', tema_limpio).strip()
        
        if tema_limpio not in mapping:
            mapping[tema_limpio] = set()
        
        # Agregar todos los conceptos (si es lista) o el concepto único
        if isinstance(conceptos_seleccionados, list):
            for concepto in conceptos_seleccionados:
                mapping[tema_limpio].add(concepto)
        else:
            mapping[tema_limpio].add(conceptos_seleccionados)

    # Convertir sets a listas ordenadas
    return {tema: sorted(list(conceptos)) for tema, conceptos in mapping.items()}

def save_mapping_to_db(mapping_json):
    """Inserta o actualiza el mapping en comun.admi_parametro con clave 'CLASIFICACION_TEMAS'"""
    conn = None
    try:
        DATABASE_URL = os.getenv('DB_HOST', '')

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Verificar si ya existe el registro con esa clave
        select_sql = "SELECT id_parametro FROM comun.admi_parametro WHERE clave = %s"
        cur.execute(select_sql, ('CLASIFICACION_TEMAS',))
        existing = cur.fetchone()

        if existing:
            # Actualizar
            update_sql = """
                UPDATE comun.admi_parametro
                SET valor = %s,
                    tipo = 'JSON',
                    descripcion = 'Mapping de temas a secciones extraído de secciones_completas.json',
                    fecha_modificacion = NOW(),
                    usuario_modificacion = 1
                WHERE clave = 'CLASIFICACION_TEMAS'
            """
            cur.execute(update_sql, (Json(mapping_json),))
            print("Registro actualizado en admi_parametro")
        else:
            # Insertar
            insert_sql = """
                INSERT INTO comun.admi_parametro
                    (clave, valor, tipo, descripcion, fecha_creacion, usuario_creacion, id_estado)
                VALUES
                    (%s, %s, %s, %s, NOW(), %s, %s)
                RETURNING id_parametro
            """
            cur.execute(insert_sql, (
                'CLASIFICACION_TEMAS',
                Json(mapping_json),
                'JSON',
                'Mapping de temas a secciones extraído de secciones_completas.json',
                '1',
                 1  # 1 activo
            ))
            inserted_id = cur.fetchone()[0]
            print(f"✅ Registro insertado con id_parametro = {inserted_id}")

        conn.commit()
        cur.close()

    except Exception as e:
        print(f"❌ Error al guardar en base de datos: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def main():
    print("Leyendo secciones_completas.json...")
    mapping = build_topic_mapping()
    print(f"   → {len(mapping)} temas encontrados.")

    print("Guardando mapping en PostgreSQL (comun.admi_parametro)...")
    save_mapping_to_db(mapping)

    # Opcional: mostrar un ejemplo
    primeros_temas = list(mapping.items())[:3]
    print("\nEjemplo del mapping guardado:")
    for tema, secciones in primeros_temas:
        print(f"  {tema}:")
        for sec in secciones[:2]:
            print(f"    - {sec}")
        if len(secciones) > 2:
            print(f"    ... y {len(secciones)-2} más.")

if __name__ == "__main__":
    main()

