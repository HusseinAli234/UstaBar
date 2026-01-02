FROM python:3.12-slim as builder

# Установка системных зависимостей для сборки некоторых библиотек Python
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка зависимостей (используем uv для скорости, если хотите, или обычный pip)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.12-slim
WORKDIR /app

# Копируем установленные библиотеки из билдера
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения
COPY . .

# Делаем скрипт запуска исполняемым
RUN chmod +x scripts/start.sh

CMD ["./scripts/start.sh"]