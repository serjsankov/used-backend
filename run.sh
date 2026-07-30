#!/bin/sh
# Запуск FastAPI на порту, который передаёт App Platform
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}