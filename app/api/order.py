# Временно добавьте в app/api/page_router.py или создайте новый router
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter(tags=["Frontend"])
class OrderCreateSchema(BaseModel):
    service_id: str
    duration: str
    price: int
    comment: str
    address: str
    latitude: float
    longitude: float

@router.post("/api/orders")
async def create_order(order_data: OrderCreateSchema):
    print(f"🎉 ПРИШЕЛ ЗАКАЗ! {order_data}")
    # ТУТ БУДЕТ СОХРАНЕНИЕ В БД (SQLAlchemy)
    return {"status": "ok", "message": "Заказ создан"}