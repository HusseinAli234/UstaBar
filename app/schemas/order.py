from pydantic import BaseModel
from typing import Optional,List
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.order import OrderStatus


class WorkerContact(BaseModel):
    name: str
    phone: Optional[str]
    username: Optional[str]

    
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
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List, Any
from app.models.order import OrderStatus
from geoalchemy2.shape import to_shape # Нужно для конвертации

# ... твои прошлые схемы ...

# Обновляем схему детализации (которая используется в фиде)
class OrderReadDetail(BaseModel):
    id: int
    service_type: str
    price: int
    status: OrderStatus
    address: str
    created_at: datetime
    duration: str
    comment: Optional[str] = None
    photos: Optional[List[str]] = []
    worker: Optional[WorkerContact] = None
    
    # Добавляем поля координат
    lat: float
    lon: float

    class Config:
        from_attributes = True

    # Проще сделать через model_validator, чтобы разобрать объект Order целиком
    from pydantic import model_validator

    @model_validator(mode='before')
    @classmethod
    def extract_coords(cls, data: Any) -> Any:
        # data - это объект SQLAlchemy Order
        if hasattr(data, "location") and data.location is not None:
            # Превращаем WKBElement (PostGIS) в объект Shapely
            shapely_point = to_shape(data.location)
            # Добавляем атрибуты динамически, чтобы Pydantic их съел
            data.lat = shapely_point.y # Latitude
            data.lon = shapely_point.x # Longitude
        return data