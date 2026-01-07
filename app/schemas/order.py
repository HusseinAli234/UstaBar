from pydantic import BaseModel
from typing import Optional,List
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.order import OrderStatus

class OrderCreate(BaseModel):
    service_id: str
    price: int
    duration: str
    comment: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    photos: Optional[str] = None # Приходит строка "img1.jpg,img2.jpg"


class OrderRead(BaseModel):
    id: int
    service_type: str
    price: int
    status: OrderStatus # Pydantic сам превратит Enum в строку
    address: str
    created_at: datetime
    
    
    class Config:
        # Эта настройка разрешает Pydantic читать данные из ORM-моделей
        from_attributes = True

# Схема для ДЕТАЛЬНОГО просмотра
class OrderReadDetail(BaseModel):
    id: int
    service_type: str
    price: int
    status: OrderStatus
    address: str
    created_at: datetime
    duration: str
    comment: Optional[str] = None
    photos: Optional[List[str]] = [] # Список имен файлов

    class Config:
        from_attributes = True