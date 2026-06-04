import os
import sqlite3

# Ajusta la ruta a tu openfang.db si es diferente
DB_PATH = os.path.expanduser("~/.openfang/data/openfang.db")

def inspeccionar_esquema():
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la BD en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for tabla in ["memories", "kv_store"]:
        cursor.execute(f"PRAGMA table_info({tabla});")
        columnas = cursor.fetchall()
        
        print(f"\n📊 Estructura de la tabla '{tabla}':")
        if not columnas:
            print("  (Tabla vacía o no existe)")
        for col in columnas:
            # col[1] es el nombre, col[2] es el tipo de dato
            print(f"  - {col[1]} (Tipo: {col[2]})")

    conn.close()

if __name__ == "__main__":
    inspeccionar_esquema()