from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from app.schemas.order import OrderReadDetail # <-- Импорт новой схемы
from sqlalchemy.orm import selectinload
from app.core.database import get_async_session
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate,OrderRead
from app.core.security_tg import validate_telegram_data # Ваша функция проверки хеша
from app.core.config import settings


from sqlalchemy import desc



router = APIRouter(tags=["Orders"])

@router.post("/api/orders")
async def create_order(
    order_data: OrderCreate,
    # Получаем initData из заголовка Authorization
    authorization: str = Header(..., alias="Authorization"), 
    session: AsyncSession = Depends(get_async_session)
):
    # 1. ПРОВЕРКА АВТОРИЗАЦИИ
    # Валидируем данные от Телеграма
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверные данные авторизации")

    tg_id = user_data["id"]

    # 2. ИЩЕМ ЮЗЕРА В БД
    # Нам нужно связать заказ с конкретным клиентом
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Запустите бот через /start")

    # 3. ОБРАБОТКА ДАННЫХ
    # Фото приходят строкой "img1.jpg,img2.jpg", превращаем в список
    photos_list = order_data.photos.split(",") if order_data.photos else []

    # Создаем точку для PostGIS (Longitude, Latitude)
    # ВАЖНО: PostGIS использует порядок (X Y) -> (Dolgota Shirota)
    point = f"POINT({order_data.longitude} {order_data.latitude})"

    # 4. СОЗДАЕМ ЗАКАЗ
    new_order = Order(
        customer_id=user.id,
        service_type=order_data.service_id,
        price=order_data.price,
        duration=order_data.duration,
        comment=order_data.comment,
        address=order_data.address,
        photos=photos_list,     # SQLAlchemy сам сохранит это как JSON
        location=point,         # GeoAlchemy2 преобразует строку в geometry
        status=OrderStatus.SEARCHING # Сразу ставим статус "В поиске"
    )

    session.add(new_order)
    await session.commit()
    
    return {"status": "ok", "order_id": new_order.id}





@router.get("/api/orders/my", response_model=list[OrderRead])
async def get_my_orders(
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    # 1. Валидация
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 2. Ищем юзера
    result = await session.execute(select(User).where(User.tg_id == user_data["id"]))
    user = result.scalar_one_or_none()
    if not user:
        return []

    # 3. Достаем заказы (новые сверху)
    stmt = select(Order).where(Order.customer_id == user.id).order_by(desc(Order.created_at))
    result = await session.execute(stmt)
    orders = result.scalars().all()

    return orders



@router.get("/api/orders/{order_id}", response_model=OrderReadDetail)
async def get_order_detail(
    order_id: int,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")

    query = (
        select(Order)
        .join(Order.customer)
        .where(
            Order.id == order_id,
            User.tg_id == user_data["id"]
        )
        # ВАЖНО: Подгружаем мастера, иначе Pydantic упадет
        .options(selectinload(Order.worker)) 
    )
    
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
        
    return order

# app/api/order_router.py

@router.post("/api/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1. Ищем заказ
    # Обязательно проверяем customer_id, чтобы нельзя было отменить чужой заказ
    # stmt = select(Order).where(
    #     Order.id == order_id,
    #     Order.customer_id == user.id  # Нужно сначала найти юзера по tg_id, см. ниже полный код
    # )
    
    # --- Поиск юзера (лучше вынести в dependency, но пока так) ---
    user_res = await session.execute(select(User).where(User.tg_id == user_data["id"]))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    order_res = await session.execute(select(Order).where(Order.id == order_id, Order.customer_id == user.id))
    order = order_res.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # 2. Проверяем статус
    if order.status != OrderStatus.SEARCHING:
        raise HTTPException(status_code=400, detail="Нельзя отменить заказ, который уже в работе или завершен")

    # 3. Отменяем
    order.status = OrderStatus.CANCELED
    await session.commit()
    
    return {"status": "ok", "message": "Заказ отменен"}


from app.schemas.response import ApplicationRead
from app.models.order import OrderResponse # Не забудь импортировать модель

# 1. ПОЛУЧИТЬ СПИСОК ОТКЛИКОВ

@router.get("/api/orders/{order_id}/applications", response_model=list[ApplicationRead])
async def get_order_applications(
    order_id: int,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Ищем заказ и проверяем, что он принадлежит юзеру
    # (код проверки order/user пропущен для краткости, используй из прошлых примеров)
    # ...

    # Запрос: Отклики + Данные рабочего + Профиль рабочего
    # Важно: нужно загрузить relationship worker
    stmt = (
        select(OrderResponse)
        .where(
            OrderResponse.order_id == order_id, 
            OrderResponse.is_skipped == False
        )
        .options(selectinload(OrderResponse.worker)) 
    )
    
    result = await session.execute(stmt)
    applications = result.scalars().all()
    
    return applications



# @router.post("/api/orders/{order_id}/accept/{application_id}")
# async def accept_application(
#     order_id: int,
#     application_id: int,
#     authorization: str = Header(..., alias="Authorization"),
#     session: AsyncSession = Depends(get_async_session)
# ):
#     # 1. ПРОВЕРКА АВТОРИЗАЦИИ
#     user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
#     if not user_data:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     # 2. ПОЛУЧАЕМ ТЕКУЩЕГО ЮЗЕРА
#     user_res = await session.execute(select(User).where(User.tg_id == user_data["id"]))
#     user = user_res.scalar_one_or_none()

#     # 3. ПОЛУЧАЕМ ЗАКАЗ И ПРОВЕРЯЕМ, ЧТО ОН ПРИНАДЛЕЖИТ ЮЗЕРУ
#     order_res = await session.execute(
#         select(Order).where(
#             Order.id == order_id, 
#             Order.customer_id == user.id  # <-- ВАЖНО: Только владелец может принять мастера
#         )
#     )
#     order = order_res.scalar_one_or_none()
    
#     if not order:
#         raise HTTPException(404, "Заказ не найден или нет прав")

#     # 4. ПОЛУЧАЕМ ОТКЛИК
#     app_res = await session.execute(select(OrderResponse).where(OrderResponse.id == application_id))
#     application = app_res.scalar_one_or_none()
    
#     if not application:
#         raise HTTPException(404, "Отклик не найден")

#     # ... логика обновления статуса ...
#     order.status = OrderStatus.IN_PROGRESS
#     if application.proposed_price:
#         order.price = application.proposed_price
#     order.worker_id = application.worker_id

#     await session.commit()
#     return {"status": "ok"}


@router.post("/api/orders/{order_id}/complete")
async def complete_order(
    order_id: int,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # --- ДОБАВЛЯЕМ ПОИСК ЮЗЕРА ---
    user_res = await session.execute(select(User).where(User.tg_id == user_data["id"]))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # -----------------------------

    # Теперь user.id существует
    order_res = await session.execute(
        select(Order).where(Order.id == order_id, Order.customer_id == user.id)
    )
    order = order_res.scalar_one_or_none()
    
    if not order:
        raise HTTPException(404, "Заказ не найден")

    if order.status != OrderStatus.IN_PROGRESS:
        raise HTTPException(400, "Можно завершить только заказ в работе")

    order.status = OrderStatus.COMPLETED
    await session.commit()
    
    return {"status": "ok", "message": "Заказ завершен"}

from app.loader import bot
from sqlalchemy.orm import selectinload



@router.post("/api/orders/{order_id}/accept/{application_id}")
async def accept_application(
    order_id: int,
    application_id: int,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    # ... (код проверки авторизации и прав клиента, который мы писали ранее) ...

    # 1. Получаем отклик ВМЕСТЕ с данными мастера (чтобы знать его tg_id)
    stmt = (
        select(OrderResponse)
        .where(OrderResponse.id == application_id)
        .options(selectinload(OrderResponse.worker)) # Подгружаем мастера
    )
    app_res = await session.execute(stmt)
    application = app_res.scalar_one_or_none()
    
    if not application:
        raise HTTPException(404, "Отклик не найден")

    # 2. Получаем заказ
    order_res = await session.execute(select(Order).where(Order.id == order_id))
    order = order_res.scalar_one()

    # 3. Обновляем статус заказа
    order.status = OrderStatus.IN_PROGRESS
    if application.proposed_price:
        order.price = application.proposed_price
    order.worker_id = application.worker_id
    
    await session.commit()
    
    # --- НОВОЕ: ОТПРАВКА УВЕДОМЛЕНИЯ МАСТЕРУ ---
    try:
        worker_tg_id = application.worker.tg_id
        msg_text = (
            f"🎉 <b>Ура! Вас выбрали исполнителем!</b>\n\n"
            f"Заказ: {order.service_type}\n"
            f"Цена: {order.price} ₽\n\n"
            f"👉 Зайдите в раздел «Мои работы», чтобы увидеть контакты клиента и адрес."
        )
        # Отправляем сообщение
        await bot.send_message(chat_id=worker_tg_id, text=msg_text, parse_mode="HTML")
    except Exception as e:
        print(f"Не удалось отправить уведомление мастеру: {e}")
    # -------------------------------------------
    
    return {"status": "ok"}