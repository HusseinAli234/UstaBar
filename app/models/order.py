import enum
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Enum, JSON,Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry # pip install geoalchemy2

from app.core.database import Base
from app.models.user import User # Импорт для TypeHinting

class OrderStatus(str, enum.Enum):
    SEARCHING = "searching"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Клиент (Владелец заказа)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    customer: Mapped["User"] = relationship(back_populates="created_orders")

    # Детали заказа
    service_type: Mapped[str] = mapped_column(String, index=True) # electrician
    price: Mapped[int] = mapped_column(Integer) # Бюджет
    duration: Mapped[str] = mapped_column(String) # "2 часа"
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    # Фото (храним как JSON массив ссылок)
    photos: Mapped[Optional[list[str]]] = mapped_column(JSON)

    # --- ГЕОЛОКАЦИЯ (PostGIS) ---
    # Используем тип Geometry. В Pydantic это будет отображаться как str или bytes при чтении
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))
    address: Mapped[str] = mapped_column(String)

    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.SEARCHING)

    # Отклики от рабочих (One-to-Many)
    responses: Mapped[list["OrderResponse"]] = relationship(back_populates="order")


# --- Таблица откликов (Рабочий -> Заказ) ---
class OrderResponse(Base):
    __tablename__ = "order_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # К какому заказу отклик
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    order: Mapped["Order"] = relationship(back_populates="responses")

    # Какой рабочий откликнулся
    worker_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    worker: Mapped["User"] = relationship() # Просто связь, без back_populates если не нужно

    # Предложение рабочего
    message: Mapped[Optional[str]] = mapped_column(Text) # "Буду через 15 минут"
    proposed_price: Mapped[Optional[int]] = mapped_column(Integer) # Если хочет другую цену
    is_skipped: Mapped[bool] = mapped_column(Boolean, default=False)