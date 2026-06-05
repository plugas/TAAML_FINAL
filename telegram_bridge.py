import logging
import asyncio
import os
import sqlite3
import struct
import math
import httpx
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from telegram import Update

TELEGRAM_TOKEN = '8849421068:AAG1BUt2Q3CXDD1J9_ja8xYTdGQ_RQ_lDKk'
OPENFANG_BASE = "http://127.0.0.1:4200"
AGENT_NAME = "assistant"
DB_PATH = os.path.expanduser("~/.openfang/data/openfang.db")
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "qwen2.5:1.5b"
TOP_K = 3
SIMILARITY_MIN = 0.4
TIMEOUT_SEC = 120

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def obtener_embedding(texto: str) -> list[float] | None:
    try:
        resp = httpx.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": texto},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("embedding")
    except Exception as e:
        logger.error("Error generando embedding: %s", e)
    return None


def similitud_coseno(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    m1 = math.sqrt(sum(a * a for a in v1))
    m2 = math.sqrt(sum(b * b for b in v2))
    return 0.0 if m1 == 0 or m2 == 0 else dot / (m1 * m2)


def buscar_contexto(pregunta: str) -> str:
    if not os.path.exists(DB_PATH):
        logger.warning("Base de datos no encontrada: %s", DB_PATH)
        return ""

    vector_q = obtener_embedding(pregunta)
    if not vector_q:
        logger.warning("No se pudo generar embedding para la pregunta")
        return ""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT content, embedding FROM memories WHERE embedding IS NOT NULL"
    )
    filas = cursor.fetchall()
    conn.close()

    if not filas:
        return ""

    resultados = []
    for content, blob in filas:
        num_floats = len(blob) // 4
        doc_vector = struct.unpack(f"<{num_floats}f", blob)
        sim = similitud_coseno(vector_q, list(doc_vector))
        resultados.append((sim, content))

    resultados.sort(key=lambda x: x[0], reverse=True)
    mejores = [r for r in resultados if r[0] >= SIMILARITY_MIN][:TOP_K]

    if not mejores:
        logger.info("No se encontraron documentos relevantes (mejor similitud: %.4f)", resultados[0][0] if resultados else 0)
        return ""

    partes = []
    for i, (sim, contenido) in enumerate(mejores, 1):
        preview = contenido[:1500].strip()
        partes.append(f"--- Documento relevante {i} (similitud: {sim:.2f}) ---\n{preview}")

    logger.info("Contexto RAG: %d documento(s) recuperado(s)", len(mejores))
    return "\n\n".join(partes)


async def consultar_openfang(mensaje_usuario: str, agent_id: str) -> str:
    loop = asyncio.get_running_loop()
    contexto = await loop.run_in_executor(None, buscar_contexto, mensaje_usuario)

    if contexto:
        mensaje_final = (
            f"{contexto}\n\n"
            f"--- Instrucción ---\n"
            f"Responde la siguiente pregunta usando ÚNICAMENTE la información de los documentos anteriores. "
            f"Si no encuentras la respuesta en los documentos, di que no tienes esa información.\n\n"
            f"Pregunta: {mensaje_usuario}"
        )
    else:
        mensaje_final = (
            f"No hay documentos relevantes en la base de conocimiento.\n\n"
            f"Pregunta: {mensaje_usuario}"
        )

    logger.info("Enviando consulta a OpenFang (contexto: %d chars)", len(contexto))
    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        resp = await client.post(
            f"{OPENFANG_BASE}/api/agents/{agent_id}/message",
            json={"message": mensaje_final},
        )
        resp.raise_for_status()
        data = resp.json()
        respuesta = data.get("response") or data.get("content") or ""
        logger.info(
            "Tokens: %s in / %s out | iteraciones: %s",
            data.get("input_tokens"),
            data.get("output_tokens"),
            data.get("iterations"),
        )
        return respuesta or "[El agente no generó respuesta]"


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent_id = context.bot_data.get("agent_id")
    if not agent_id:
        await update.message.reply_text("El bot no se ha conectado con OpenFang. Reintenta en unos segundos.")
        return
    pregunta = update.message.text
    try:
        respuesta = await consultar_openfang(pregunta, agent_id)
    except httpx.HTTPStatusError as e:
        logger.error("HTTP %s: %s", e.response.status_code, e.response.text)
        if e.response.status_code == 404:
            respuesta = "El agente solicitado no existe. Revisa la configuración."
        elif e.response.status_code >= 500:
            respuesta = "El servidor OpenFang tuvo un error interno. Reintenta más tarde."
        else:
            respuesta = f"Error de comunicación: {e.response.status_code}"
    except httpx.TimeoutException:
        logger.warning("Timeout consultando a OpenFang")
        respuesta = "La consulta tardó demasiado. Intenta con una pregunta más corta o simple."
    except httpx.RequestError as e:
        logger.error("Error de conexión con OpenFang: %s", e)
        respuesta = "No pude conectarme con OpenFang. ¿Está corriendo el kernel (openfang daemon)?"
    except Exception as e:
        logger.exception("Error inesperado")
        respuesta = "Ocurrió un error inesperado."

    if len(respuesta) > 4000:
        respuesta = respuesta[:4000] + "... [TRUNCADO]"
    await update.message.reply_text(respuesta)


async def post_init(application):
    logger.info("Resolviendo agente '%s' en OpenFang...", AGENT_NAME)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            agent_id = await resolve_agent_id(client)
        if agent_id:
            application.bot_data["agent_id"] = agent_id
            logger.info("Agente '%s' resuelto, ID: %s", AGENT_NAME, agent_id)
        else:
            logger.error("No se pudo resolver el agente '%s'", AGENT_NAME)
    except httpx.RequestError as e:
        logger.error("OpenFang no está disponible en %s: %s", OPENFANG_BASE, e)


async def resolve_agent_id(client: httpx.AsyncClient) -> str | None:
    resp = await client.get(f"{OPENFANG_BASE}/api/agents")
    resp.raise_for_status()
    agents = resp.json()
    if isinstance(agents, dict):
        agents = agents.get("agents", list(agents.values()))
    for agent in agents:
        if isinstance(agent, dict) and agent.get("name") == AGENT_NAME:
            return agent.get("id")
    logger.error(f"Agente '{AGENT_NAME}' no encontrado entre {len(agents)} agente(s)")
    return None


async def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensaje))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
