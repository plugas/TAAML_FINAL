import os
import json
import sqlite3
import requests
import uuid
import struct
from datetime import datetime, timezone

# --- CONFIGURACIÓN ---
DATA_DIR = "./data"
DB_PATH = os.path.expanduser("~/.openfang/data/openfang.db") 
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
MODELO_EMBEDDING = "qwen2.5:1.5b" 

def obtener_embedding(texto):
    """Llama a Ollama localmente para vectorizar el texto."""
    payload = {
        "model": MODELO_EMBEDDING,
        "prompt": texto
    }
    try:
        response = requests.post(OLLAMA_EMBED_URL, json=payload)
        if response.status_code == 200:
            return json.loads(response.text)["embedding"]
    except Exception as e:
        print(f"Error generando embedding con Ollama: {e}")
    return None

def inyectar_conocimiento():
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en {DB_PATH}.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    archivos_procesados = 0

    print("Iniciando inyección en 'memories' (Vector Store) y 'kv_store'...")

    for root, dirs, files in os.walk(DATA_DIR):
        for filename in files:
            if filename.lower().endswith('.md'):
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, DATA_DIR).replace("\\", "/")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if content:
                    print(f"Procesando: {rel_path}...")
                    vector = obtener_embedding(content)
                    
                    if vector:
                        # 1. Preparar los datos
                        doc_id = str(uuid.uuid4())
                        agent_id = "system" # Agente por defecto dueño del conocimiento global
                        now = datetime.now(timezone.utc).isoformat()
                        
                        # Convertir vector a binario (BLOB - Array C de Float32, Little-Endian)
                        embedding_blob = struct.pack(f'<{len(vector)}f', *vector)
                        
                        # Metadatos en JSON
                        metadata = json.dumps({
                            "filename": filename,
                            "path": rel_path,
                            "type": "markdown_knowledge"
                        })

                        try:
                            # 2. Inserción en Vector Store (memories)
                            cursor.execute("""
                                INSERT INTO memories 
                                (id, agent_id, content, source, scope, confidence, metadata, created_at, accessed_at, access_count, deleted, embedding)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                doc_id, agent_id, content, rel_path, "global", 1.0, 
                                metadata, now, now, 0, 0, embedding_blob
                            ))

                            # 3. Inserción en KV Store (kv_store)
                            # Guardamos una clave única para rápida lectura de metadatos sin buscar en vectores
                            kv_key = f"doc_meta:{rel_path}"
                            kv_value = metadata.encode('utf-8') # El BLOB aquí puede ser texto codificado
                            
                            cursor.execute("""
                                INSERT INTO kv_store (agent_id, key, value, version, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (agent_id, kv_key, kv_value, 1, now))

                            archivos_procesados += 1
                            print(f"✅ Conocimiento anclado: {filename}")

                        except sqlite3.Error as e:
                            print(f"⚠️ Error SQL inyectando {filename}: {e}")

    conn.commit()
    conn.close()
    print(f"\n🚀 Fase 2 Completada: {archivos_procesados} documentos inyectados en OpenFang OS.")

if __name__ == "__main__":
    inyectar_conocimiento()