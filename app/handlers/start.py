from aiogram.types import Message
from aiogram.filters import Command
from app.bot import dp

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет из FastAPI!")
