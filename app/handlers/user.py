from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Импорты БД
from sqlalchemy import select
from app.core.database import async_session_maker # Импортируем фабрику сессий напрямую
from app.models.user import User
from app.core.config import settings

user_router = Router()

# --- 1. Определяем состояния (Шаги регистрации) ---
class Registration(StatesGroup):
    role_selection = State()    # Выбор роли
    service_selection = State() # Выбор услуги (только для рабочих)
    waiting_for_name = State()  # Имя
    waiting_for_surname = State() # Фамилия
    waiting_for_phone = State()   # Телефон
    main_menu = State()         # Финал

# --- 2. Вспомогательная функция очистки ---
async def clean_chat(message: Message, state: FSMContext, bot: Bot):
    """Удаляет сообщение юзера и прошлый вопрос бота"""
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

# --- 3. Хендлеры ---

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Кнопки выбора роли
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Я Клиент (Ищу услуги)", callback_data="role_client")
    builder.button(text="🛠 Я Рабочий (Предлагаю услуги)", callback_data="role_worker")
    builder.adjust(1)
    
    text = "👋 Привет! Добро пожаловать в UstaBar.\nКто вы?"
    
    msg = await message.answer(text, reply_markup=builder.as_markup())
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(Registration.role_selection)


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


# --- ШАГ 6 (ФИНАЛ): Ввод ТЕЛЕФОНА и СОХРАНЕНИЕ ---
@user_router.message(Registration.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    await clean_chat(message, state, bot)
    
    phone = message.text
    data = await state.get_data() # Получаем все накопленные данные
    
    # Подготовка данных для сохранения
    user_data = {
        "tg_id": message.from_user.id,
        "username": message.from_user.username,
        "name": data.get("name"),
        "surname": data.get("surname"), # Предполагаем, что добавите поле в модель
        "phone": phone,                 # Предполагаем, что добавите поле в модель
        "role": data.get("role"),       # 'client' или 'worker'
        "service_type": data.get("service_type"), # Может быть None, если клиент
        "hashed_password": "telegram_auth"
    }

    # --- РАБОТА С БД (Правильный способ для Aiogram) ---
    async with async_session_maker() as session:
        # Проверяем, есть ли юзер
        result = await session.execute(select(User).where(User.tg_id == user_data["tg_id"]))
        user = result.scalar_one_or_none()
        
        if not user:
            # Создаем нового
            # ВАЖНО: Убедитесь, что в модели User есть эти поля!
            # Если полей пока нет, закомментируйте лишние аргументы
            user = User(**user_data)
            session.add(user)
        else:
            # Обновляем существующего
            user.name = user_data["name"]
            user.surname = user_data["surname"]
            user.phone = user_data["phone"]
            user.role = user_data["role"]
            user.service_type = user_data["service_type"]
        
        await session.commit()

    # --- ФИНАЛЬНОЕ МЕНЮ ---
    builder = InlineKeyboardBuilder()
    
    # Ссылка на карту теперь одна, но внутри карты мы можем показывать разное в зависимости от роли
    webapp_url = f"{settings.BASE_URL}/webapp/select-service"
    
    if user_data["role"] == "worker":
        # У рабочих может быть другой текст кнопки
        builder.button(text="🗺 Открыть заказы", web_app=WebAppInfo(url=webapp_url))
        fin_text = "✅ Регистрация рабочего завершена! Ждите заказов."
    else:
        builder.button(text="🗺 Создать заказ", web_app=WebAppInfo(url=webapp_url))
        fin_text = "✅ Регистрация клиента завершена! Можно заказывать услуги."
        
    # Кнопка для редактирования анкеты
    builder.button(text="🔄 Заполнить заново", callback_data="restart_reg")
    builder.adjust(1)
    
    msg = await message.answer(fin_text, reply_markup=builder.as_markup())
    await state.update_data(last_msg_id=msg.message_id)
    await state.set_state(Registration.main_menu)

# Кнопка рестарта
@user_router.callback_query(F.data == "restart_reg")
async def restart(callback: CallbackQuery, state: FSMContext):
    await cmd_start(callback.message, state)