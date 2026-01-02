#!/bin/bash

# Ожидание готовности базы данных (можно заменить на pg_isready)
echo "Waiting for postgres..."
sleep 2

# Накатываем миграции
echo "Running migrations..."
alembic upgrade head

# Запуск приложения
echo "Starting FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload