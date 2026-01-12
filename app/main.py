from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import types

# ИМПОРТИРУЕМ ИЗ LOADER
from app.loader import bot, dp 

# Роутеры
from app.api.page_router import router as page_router
from app.core.config import settings
from app.handlers.user import user_router 
from app.api.upload_router import router as upload_router
from app.core.storage import init_storage
from app.api.order_router import router as order_router
from app.api.worker_router import router as worker_router

init_storage()

# Подключаем роутеры бота к диспетчеру (это можно оставить здесь)
dp.include_router(user_router)


# --- Жизненный цикл (ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. ДЕЙСТВИЯ ПРИ ЗАПУСКЕ
    webhook_url = settings.BASE_URL + settings.WEBHOOK_PATH
    print(f"🚀 Устанавливаем вебхук: {webhook_url}")
    
    # bot импортирован из loader, но работает так же
    await bot.set_webhook(url=webhook_url)
    
    yield 
    
    # 2. ДЕЙСТВИЯ ПРИ ВЫКЛЮЧЕНИИ
    print("🛑 Удаляем вебхук...")
    await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(
    title="CRM Freelance App",
    lifespan=lifespan 
)

app.include_router(order_router)
app.include_router(worker_router)
app.include_router(page_router)
app.include_router(upload_router)

# Вебхук хендлер
@app.post(settings.WEBHOOK_PATH)
async def bot_webhook(request: Request):
    telegram_update = await request.json()
    update = types.Update(**telegram_update)
    await dp.feed_update(bot=bot, update=update)