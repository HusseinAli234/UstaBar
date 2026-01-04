from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.api.auth import auth  # Ваши старые роуты
# Импортируем ваш роутер с логикой бота (который мы писали ранее)
from app.handlers.user import user_router 

# --- Инициализация Бота и Диспетчера ---
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

# Подключаем ваши обычные API роуты (auth и т.д.)
app.include_router(auth.router)


# --- Самое главное: Роут для приема сообщений от Telegram ---
@app.post(settings.WEBHOOK_PATH)
async def bot_webhook(request: Request):
    """
    Сюда Telegram шлет JSON с сообщениями.
    Мы пересылаем его в aiogram.
    """
    # Получаем JSON из запроса
    telegram_update = await request.json()
    
    # Превращаем JSON в объект Update (понятный для aiogram)
    update = types.Update(**telegram_update)
    
    # "Скармливаем" обновление диспетчеру
    await dp.feed_update(bot=bot, update=update)
    
    # FastAPI сам вернет код 200 OK, это сигнал Телеграму, что мы получили сообщение