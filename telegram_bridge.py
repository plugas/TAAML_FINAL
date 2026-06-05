import logging
import json
import asyncio
import websockets
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from telegram import Update

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = '8849421068:AAG1BUt2Q3CXDD1J9_ja8xYTdGQ_RQ_lDKk'
WS_URL = "ws://127.0.0.1:50051/api/agents/6792748b-81a6-482e-871e-4ed799332142/ws"

logging.basicConfig(level=logging.INFO)

async def consultar_openfang(mensaje_usuario):
    try:
        # Nota: La URL cambia a /chat en lugar de /ws para iniciar la sesión
        # Pero si OpenFang insiste en el WebSocket, debemos enviar el mensaje 
        # envolviéndolo en un comando de 'session_start'
        async with websockets.connect(WS_URL) as ws:
            
            # 1. PASO CRÍTICO: Iniciar sesión con el agente
            await ws.send(json.dumps({
                "type": "session_start",
                "agent_id": "6792748b-81a6-482e-871e-4ed799332142"
            }))
            
            # 2. PASO CRÍTICO: Enviar el mensaje una vez iniciada la sesión
            await ws.send(json.dumps({
                "type": "message",
                "content": mensaje_usuario
            }))
            
            # 3. Escucha activa (filtrando eventos globales)
            while True:
                respuesta_cruda = await ws.recv()
                data = json.loads(respuesta_cruda)
                
                # Ignoramos volcados de agentes
                if "agents" in data:
                    continue
                
                # Buscamos la respuesta específica al mensaje
                if data.get("type") in ["message", "chat_response", "reply"]:
                    return data.get("content") or data.get("reply")
                
                logging.info(f"Ignorando evento: {data.get('type')}")
    except Exception as e:
        return f"Error: {e}"

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pregunta = update.message.text
    respuesta = await consultar_openfang(pregunta)
    
    # Corte de seguridad extremo para Telegram
    if len(respuesta) > 4000:
        respuesta = respuesta[:4000] + "... [TRUNCADO]"
        
    await update.message.reply_text(respuesta)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensaje))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())