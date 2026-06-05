.phony: limpiar ingesta prueba_openfang

limpiar:
	cls
ingesta:
	make limpiar
	uv run ingest_sqlite.py
prueba_openfang:
	cls
	uv run ./tests/test_openfang.py
prueba_telegram:
	make limpiar
	uv run telegram_bridge.py