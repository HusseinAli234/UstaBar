from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    service_id: str
    price: int
    duration: str
    comment: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    photos: Optional[str] = None # Приходит строка "img1.jpg,img2.jpg"