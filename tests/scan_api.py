import requests
import json

print("🔍 Escaneando la API de OpenFang...")
try:
    # Consultamos la lista de agentes registrados
    res = requests.get("http://127.0.0.1:50051/api/agents")
    if res.status_code == 200:
        datos = res.json()
        print("\n✅ Agentes encontrados en el Kernel:")
        print(json.dumps(datos, indent=2))
    else:
        print(f"⚠️ La ruta /api/agents devolvió error: {res.status_code}")
except Exception as e:
    print(f"❌ Error de conexión: {e}")