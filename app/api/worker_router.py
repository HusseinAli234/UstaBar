from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, not_

from app.core.database import get_async_session
from app.models.user import User
from app.models.order import Order, OrderStatus, OrderResponse
from app.schemas.order import OrderReadDetail # Используем схему из прошлого шага
from app.core.security_tg import validate_telegram_data
from app.core.config import settings

router = APIRouter(tags=["Worker"])

# 1. ПОЛУЧИТЬ КАРТОЧКУ (Следующий заказ)
@router.get("/api/worker/feed", response_model=list[OrderReadDetail])
async def get_worker_feed(
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Получаем ID рабочего
    result = await session.execute(select(User).where(User.tg_id == user_data["id"]))
    worker = result.scalar_one_or_none()

    # Основной запрос:
    # 1. Заказ в статусе SEARCHING
    # 2. Тип услуги совпадает с типом рабочего (опционально, если хочешь)
    # 3. Рабочий еще НЕ откликался на этот заказ (нет записи в OrderResponse)
    
    # Подзапрос: ID заказов, на которые этот рабочий уже реагировал
    subquery = select(OrderResponse.order_id).where(OrderResponse.worker_id == worker.id)

    stmt = select(Order).where(
        and_(
            Order.status == OrderStatus.SEARCHING,
            Order.service_type == worker.service_type, # Фильтр по профессии!
            not_(Order.id.in_(subquery)) # Исключаем виденные
        )
    ).limit(10) # Грузим пачками по 10 штук

    result = await session.execute(stmt)
    orders = result.scalars().all()
    return orders


# 2. ЛАЙК (ОТКЛИКНУТЬСЯ)
@router.post("/api/worker/apply/{order_id}")
async def apply_order(
    order_id: int,
    price: int, # Рабочий может предложить свою цену
    message: str,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    worker = (await session.execute(select(User).where(User.tg_id == user_data["id"]))).scalar_one()

    # Проверяем, не откликался ли уже
    existing = await session.execute(
        select(OrderResponse).where(
            OrderResponse.order_id == order_id, 
            OrderResponse.worker_id == worker.id
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_exists"}

    # Создаем отклик
    response = OrderResponse(
        order_id=order_id,
        worker_id=worker.id,
        proposed_price=price,
        message=message,
        is_skipped=False
    )
    session.add(response)
    await session.commit()
    
    # ТУТ МОЖНО ОТПРАВИТЬ УВЕДОМЛЕНИЕ КЛИЕНТУ ЧЕРЕЗ БОТА
    # await bot.send_message(chat_id=client_tg_id, text="На ваш заказ новый отклик!")

    return {"status": "applied"}


# 3. ДИЗЛАЙК (ПРОПУСТИТЬ)
@router.post("/api/worker/skip/{order_id}")
async def skip_order(
    order_id: int,
    authorization: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_async_session)
):
    user_data = validate_telegram_data(authorization, settings.BOT_TOKEN)
    worker = (await session.execute(select(User).where(User.tg_id == user_data["id"]))).scalar_one()

    # Записываем "пустой" отклик с флагом is_skipped
    response = OrderResponse(
        order_id=order_id,
        worker_id=worker.id,
        is_skipped=True # <-- Важно
    )
    session.add(response)
    await session.commit()
    
    return {"status": "skipped"}