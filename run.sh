#!/bin/sh
# Запуск FastAPI на порту, который передаёт App Platform (переменная PORT)
# Если PORT не задан — используется 8000
PORT="${PORT:-8000}"
echo "Starting uvicorn on port $PORT"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"