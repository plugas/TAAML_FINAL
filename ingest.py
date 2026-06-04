import os
import requests

# Puerto por defecto de la API de memoria de OpenFang
OPENFANG_MEMORY_URL = "http://localhost:3009/api/memory/ingest"
DATA_DIR = "./data"  # Actualizado al directorio raíz de tus documentos

def ingestar_documentos():
    if not os.path.exists(DATA_DIR):
        print(f"❌ El directorio '{DATA_DIR}' no existe.")
        return

    archivos_encontrados = False

    # os.walk recorre de forma recursiva la carpeta principal y todas las subcarpetas
    for root, dirs, files in os.walk(DATA_DIR):
        for filename in files:
            if filename.lower().endswith('.md'):
                archivos_encontrados = True
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                        
                    if content.strip():
                        # Extraemos la ruta relativa para usarla como nombre del documento
                        # Ej: si el archivo está en data/Knowledge/archivo.md, se guardará como "Knowledge/archivo.md"
                        rel_path = os.path.relpath(filepath, DATA_DIR)
                        
                        payload = {
                            "document_name": rel_path,
                            "content": content,
                            "store_type": "vector"
                        }
                        
                        print(f"Vectorizando '{rel_path}'...")
                        response = requests.post(OPENFANG_MEMORY_URL, json=payload)
                        
                        if response.status_code == 200:
                            print(f"✅ Éxito: '{rel_path}' guardado en el Vector Store.")
                        else:
                            print(f"❌ Error de API con '{rel_path}': {response.status_code} - {response.text}")
                            
                except requests.exceptions.ConnectionError:
                    print("\n❌ Error crítico: No se pudo conectar a OpenFang.")
                    print("Asegúrate de que el Kernel está corriendo (Puerto 3009).")
                    return # Abortamos todo el proceso si el servidor está caído
                except Exception as e:
                    print(f"⚠️ Error inesperado leyendo {filepath}: {e}")

    if not archivos_encontrados:
        print(f"⚠️ No se encontraron archivos .md en '{DATA_DIR}' ni en sus subcarpetas.")

if __name__ == "__main__":
    print("Iniciando proceso de ingesta RAG recursiva (Markdown)...")
    ingestar_documentos()
    print("Proceso finalizado.")