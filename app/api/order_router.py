from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

# Импорты вашего проекта
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