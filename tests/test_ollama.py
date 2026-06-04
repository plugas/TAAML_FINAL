import requests
import json

# URL local de Ollama
url = "http://localhost:11434/api/generate"

# En tu máquina usas qwen2.5:1.5b. En el i7 cambiarán esto a gemma2:9b
payload = {
    "model": "qwen2.5:1.5b",
    "prompt": "Eres un asistente experto en IA. Responde en una oración: ¿Qué es un sistema agéntico?",
    "stream": False
}

print("Enviando petición al modelo local...")
response = requests.post(url, json=payload)

if response.status_code == 200:
    data = json.loads(response.text)
    print("\nRespuesta del Modelo:\n")
    print(data["response"])
else:
    print(f"Error en la conexión: {response.status_code}")