from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from app.api.page_router import router as page_router
from app.core.config import settings
from app.handlers.user import user_router 
from app.api.upload_router import router as upload_router
from app.core.storage import init_storage
from app.api.order_router import router as order_router
from app.api.worker_router import router as worker_router

# ...
init_storage() # Создаем бакет при старте

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутеры бота (меню, кнопки и т.д.)
dp.include_router(user_router)


# --- Жизненный цикл (Старт/Стоп сервера) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. ДЕЙСТВИЯ ПРИ ЗАПУСКЕ
    webhook_url = settings.BASE_URL + settings.WEBHOOK_PATH
    print(f"🚀 Устанавливаем вебхук: {webhook_url}")
    
    # Сообщаем Телеграму, куда слать данные
    await bot.set_webhook(url=webhook_url)
    
    yield # В этот момент работает сервер...
    
    # 2. ДЕЙСТВИЯ ПРИ ВЫКЛЮЧЕНИИ
    print("🛑 Удаляем вебхук...")
    await bot.delete_webhook()
    # Закрываем сессию бота
    await bot.session.close()


# --- Инициализация приложения FastAPI ---
app = FastAPI(
    title="CRM Freelance App",
    lifespan=lifespan  # Подключаем наш жизненный цикл
)


app.include_router(order_router)
app.include_router(worker_router)
# Подключаем ваши обычные API роуты (auth и т.д.)
# app.include_router(auth.router)
app.include_router(page_router)
app.include_router(upload_router)
# --- Самое главное: Роут для приема сообщений от Telegram ---
@app.post(settings.WEBHOOK_PATH)
async def bot_webhook(request: Request):

    # Получаем JSON из запроса
    telegram_update = await request.json()
    
    # Превращаем JSON в объект Update (понятный для aiogram)
    update = types.Update(**telegram_update)
    
    # "Скармливаем" обновление диспетчеру
    await dp.feed_update(bot=bot, update=update)
    
    # FastAPI сам вернет код 200 OK, это сигнал Телеграму, что мы получили сообщение