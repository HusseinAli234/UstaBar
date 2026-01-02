from fastapi import FastAPI, Request
from aiogram.types import Update
from app.bot import bot, dp

app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
