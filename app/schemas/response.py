# app/schemas/response.py
from pydantic import BaseModel
from typing import Optional

class WorkerShortInfo(BaseModel):
    id: int
    name: str
    rating: float = 5.0
    # avatar_url: Optional[str] = None # Если будете делать аватарки

class ApplicationRead(BaseModel):
    id: int
    proposed_price: Optional[int]
    message: Optional[str]
    worker: WorkerShortInfo # Вложенный объект с инфой о мастере
    
    class Config:
        from_attributes = True