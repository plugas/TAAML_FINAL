import os
import sqlite3
import struct
import math
import requests

# --- CONFIGURACIÓN ---
DB_PATH = os.path.expanduser("~/.openfang/data/openfang.db")
OLLAMA_URL = "http://localhost:11434"
MODELO = "qwen2.5:1.5b" 

def obtener_embedding(texto):
    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": MODELO, "prompt": texto})
    return res.json().get("embedding") if res.status_code == 200 else None

def similitud_coseno(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    return 0 if mag1 == 0 or mag2 == 0 else dot_product / (mag1 * mag2)

def auditar_memoria():
    print("🔍 INICIANDO AUDITORÍA DE MEMORIA RAG...\n")
    
    # 1. Validar Archivo
    print(f"📁 Ruta DB: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("❌ ERROR CRÍTICO: La base de datos no existe en esa ruta.")
        return

    # 2. Validar Tablas y Filas
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content, embedding FROM memories WHERE embedding IS NOT NULL")
    filas = cursor.fetchall()
    conn.close()
    
    print(f"📊 Documentos vectorizados encontrados en SQLite: {len(filas)}")
    if len(filas) == 0:
        print("❌ ERROR: La tabla está vacía o no tiene embeddings.")
        return

    # 3. Prueba de Fuego (Matemática Vectorial)
    pregunta_prueba = "¿Qué es Riopaila y a qué se dedica?"
    print(f"\n🤖 Vectorizando pregunta de prueba: '{pregunta_prueba}'")
    vector_pregunta = obtener_embedding(pregunta_prueba)
    
    if not vector_pregunta:
        print("❌ ERROR: Ollama no devolvió el vector de la pregunta.")
        return
        
    print(f"📏 Dimensión del vector de la pregunta ({MODELO}): {len(vector_pregunta)}")

    print("\n🧮 CALCULANDO SIMILITUDES (Sin filtros):")
    for i, (content, blob) in enumerate(filas):
        num_floats = len(blob) // 4
        doc_vector = struct.unpack(f'<{num_floats}f', blob)
        
        similitud = similitud_coseno(vector_pregunta, doc_vector)
        
        # Imprimimos el puntaje y los primeros 50 caracteres del documento
        texto_corto = content[:50].replace('\n', ' ')
        print(f"  - Doc {i+1} | Similitud: {similitud:.4f} | Dimensiones: {len(doc_vector)} | Texto: '{texto_corto}...'")

if __name__ == "__main__":
    auditar_memoria()