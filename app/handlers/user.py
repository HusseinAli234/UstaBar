# app/handlers/user.py (создайте или обновите этот файл)

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.core.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.models.user import User
from sqlalchemy import select
from app.core.config import settings

# Создаем роутер
user_router = Router()

# Определяем состояния (шаги диалога)
class UserState(StatesGroup):
    main_menu = State()
    waiting_for_info = State()

# Вспомогательная функция для "чистого" чата
async def clean_chat(message: Message, state: FSMContext, bot: Bot):
    """
    Удаляет сообщение пользователя и последнее сообщение бота,
    если его ID сохранен в памяти.
    """
    # 1. Удаляем сообщение, которое только что написал пользователь
    try:
        await message.delete()
    except:
        pass # Бывает, что уже удалено или нет прав

    # 2. Удаляем прошлое сообщение бота (вопрос)
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except:
            pass


@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Очищаем состояние при рестарте
    await state.clear()
    
    # Создаем клавиатуру с Web App (Ваш сайт с картой)
    # В url укажите ваш https адрес (ngrok или реальный домен)
    builder = InlineKeyboardBuilder()
    webapp_url = f"{settings.BASE_URL}/webapp"
    builder.button(text="🗺 Открыть карту", web_app=WebAppInfo(url=webapp_url))
    builder.button(text="📝 Ввести данные", callback_data="input_data")
    builder.adjust(1)

    text = "Привет! Это CRM Freelance бот.\nНажми кнопку ниже, чтобы открыть карту."

    # Отправляем сообщение и СОХРАНЯЕМ его ID
    msg = await message.answer(text, reply_markup=builder.as_markup())
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(UserState.main_menu)


# --- ЭФФЕКТ 1: РЕДАКТИРОВАНИЕ (Плавный переход) ---
@user_router.callback_query(F.data == "input_data")
async def ask_info(callback: CallbackQuery, state: FSMContext):
    # Мы не отправляем новое сообщение, а РЕДАКТИРУЕМ старое.
    # Это создает красивый эффект смены контента.
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    
    await callback.message.edit_text(
        text="Пожалуйста, введите ваше имя в чат:",
        reply_markup=builder.as_markup()
    )
    # Переводим бота в режим ожидания текста
    await state.set_state(UserState.waiting_for_info)


# --- ЭФФЕКТ 2: УДАЛЕНИЕ (При вводе текста) ---


@user_router.message(UserState.waiting_for_info, F.text)
async def process_info(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession = Depends(get_async_session),
):
    await clean_chat(message, state, bot)

    tg_id = message.from_user.id
    username = message.from_user.username
    name = message.text

    result = await session.execute(
        select(User).where(User.tg_id == tg_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            tg_id=tg_id,
            username=username,
            name=name,
            hashed_password="telegram_auth"
        )
        session.add(user)
    else:
        user.name = name
        user.username = username

    await session.commit()

    msg = await message.answer(
        text=f"Отлично, {name}! Данные сохранены.",
    )

    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(UserState.main_menu)



# Кнопка "Назад"
@user_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    # Снова используем edit_text для плавного возврата
    builder = InlineKeyboardBuilder()
    builder.button(text="🗺 Открыть карту", web_app=WebAppInfo(url="https://your-domain.com/map"))
    builder.button(text="📝 Ввести данные", callback_data="input_data")
    builder.adjust(1)

    await callback.message.edit_text(
        text="Главное меню:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserState.main_menu)