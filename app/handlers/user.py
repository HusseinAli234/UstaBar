from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Импорты БД
from sqlalchemy import select
from app.core.database import async_session_maker 
from app.models.user import User
from app.core.config import settings

user_router = Router()

# --- 1. Состояния ---
class Registration(StatesGroup):
    role_selection = State()    
    service_selection = State() 
    waiting_for_name = State() 
    waiting_for_surname = State() 
    waiting_for_phone = State()   
    main_menu = State()         

# --- 2. Вспомогательная функция очистки ---
async def clean_chat(message: Message, state: FSMContext, bot: Bot):
    try:
        await message.delete()
    except:
        pass
    
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except:
            pass

# --- 3. Вспомогательная функция: ПОКАЗ ГЛАВНОГО МЕНЮ ---
async def show_main_menu(message: Message, state: FSMContext, user: User):
    """
    Показывает меню уже зарегистрированному пользователю.
    """
    await state.clear() # Сбрасываем шаги регистрации, если они были
    
    builder = InlineKeyboardBuilder()
    
    # Формируем ссылку и текст в зависимости от роли
    webapp_url = f"{settings.BASE_URL}/webapp/select-service"
    
    if user.role == "worker":
        # У рабочих кнопка ведет к заказам
        btn_text = "🗺 Открыть заказы"
        welcome_text = f"🛠 С возвращением, мастер {user.name}!\nЖдем новых заказов."
    else:
        # У клиентов кнопка ведет к созданию заказа
        btn_text = "🗺 Создать заказ"
        welcome_text = f"👤 С возвращением, {user.name}!\nНужен мастер? Жмите кнопку ниже."
        
    builder.button(text=btn_text, web_app=WebAppInfo(url=webapp_url))
    
    # Кнопка для редактирования профиля (если вдруг захочет изменить данные)
    builder.button(text="⚙️ Настройки / Изменить роль", callback_data="edit_profile")
    builder.adjust(1)
    
    msg = await message.answer(welcome_text, reply_markup=builder.as_markup())
    
    # Сохраняем ID, чтобы потом чистить чат
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(Registration.main_menu)


# --- 4. Хендлер START (Главный вход) ---
@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # 1. Сразу проверяем БД
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()

    # 2. Логика ветвления
    if user:
        # ПОЛЬЗОВАТЕЛЬ УЖЕ ЕСТЬ -> Главное меню
        await show_main_menu(message, state, user)
    else:
        # ПОЛЬЗОВАТЕЛЯ НЕТ -> Начинаем регистрацию
        await start_registration(message, state)


async def start_registration(message: Message, state: FSMContext):
    """Начало процесса регистрации"""
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Я Клиент (Ищу услуги)", callback_data="role_client")
    builder.button(text="🛠 Я Рабочий (Предлагаю услуги)", callback_data="role_worker")
    builder.adjust(1)
    
    text = "👋 Добро пожаловать в UstaBar!\nМы вас не знаем. Давайте знакомиться.\n\nКто вы?"
    
    msg = await message.answer(text, reply_markup=builder.as_markup())
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(Registration.role_selection)


# --- Хендлер для кнопки "Изменить профиль" (Restart) ---
@user_router.callback_query(F.data == "edit_profile")
async def edit_profile_handler(callback: CallbackQuery, state: FSMContext):
    # Просто запускаем регистрацию заново
    await start_registration(callback.message, state)


# ... (Далее идут ваши хендлеры регистрации: process_role, process_service, name, surname) ...
# ... Оставьте их как есть, кроме последнего process_phone ...


# --- ОБНОВЛЕННЫЙ ФИНАЛ РЕГИСТРАЦИИ (process_phone) ---
@user_router.message(Registration.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    await clean_chat(message, state, bot)
    
    phone = message.text
    data = await state.get_data()
    
    async with async_session_maker() as session:
        # Проверяем, вдруг он уже есть (на всякий случай)
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Создаем нового
            user = User(
                tg_id=message.from_user.id,
                username=message.from_user.username,
                name=data.get("name"),
                surname=data.get("surname"),
                phone=phone,
                role=data.get("role"),
                service_type=data.get("service_type"),
                hashed_password="telegram_auth"
            )
            session.add(user)
            await session.commit()
            # Важно: обновляем объект user, чтобы у него появился ID и все поля
            await session.refresh(user)
        else:
            # Обновляем (если он нажал "Изменить профиль")
            user.name = data.get("name")
            user.surname = data.get("surname")
            user.phone = phone
            user.role = data.get("role")
            user.service_type = data.get("service_type")
            await session.commit()
            await session.refresh(user)

    # Вместо того чтобы дублировать код меню, вызываем нашу функцию!
    # message отправляем тот, который есть, user передаем из БД
    await show_main_menu(message, state, user)




# --- ШАГ 2: Обработка выбора РОЛИ ---
@user_router.callback_query(Registration.role_selection)
async def process_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1] # client или worker
    await state.update_data(role=role)
    
    if role == "worker":
        # Если рабочий -> Спрашиваем профессию
        builder = InlineKeyboardBuilder()
        services = [
            ("cleaning", "🧹 Клининг"),
            ("electrician", "⚡ Электрик"),
            ("plumber", "🔧 Сантехник"),
            ("nanny", "🧸 Няня"),
            ("other", "Другое")
        ]
        for s_id, s_name in services:
            builder.button(text=s_name, callback_data=f"service_{s_id}")
        builder.adjust(2)
        
        await callback.message.edit_text("Выберите ваш вид деятельности:", reply_markup=builder.as_markup())
        await state.set_state(Registration.service_selection)
        
    else:
        # Если клиент -> Сразу спрашиваем имя
        await callback.message.edit_text("Как к вам обращаться? (Введите Имя)")
        await state.set_state(Registration.waiting_for_name)


# --- ШАГ 3 (Только для рабочих): Выбор УСЛУГИ ---
@user_router.callback_query(Registration.service_selection)
async def process_service(callback: CallbackQuery, state: FSMContext):
    service_type = callback.data.split("_")[1]
    await state.update_data(service_type=service_type)
    
    # Теперь спрашиваем имя (как и у клиентов)
    # Используем edit_text, чтобы не плодить сообщения
    await callback.message.edit_text("Отлично! Теперь введите ваше Имя:")
    await state.set_state(Registration.waiting_for_name)


# --- ШАГ 4: Ввод ИМЕНИ ---
@user_router.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext, bot: Bot):
    await clean_chat(message, state, bot) # Удаляем сообщение юзера
    
    name = message.text
    await state.update_data(name=name)
    
    msg = await message.answer(f"Приятно познакомиться, {name}!\nТеперь введите вашу Фамилию:")
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(Registration.waiting_for_surname)


# --- ШАГ 5: Ввод ФАМИЛИИ ---
@user_router.message(Registration.waiting_for_surname)
async def process_surname(message: Message, state: FSMContext, bot: Bot):
    await clean_chat(message, state, bot)
    
    surname = message.text
    await state.update_data(surname=surname)
    
    msg = await message.answer("Почти готово! Введите ваш номер телефона:")
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(Registration.waiting_for_phone)