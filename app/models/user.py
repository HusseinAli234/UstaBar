from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column,relationship
from app.core.database import Base
from sqlalchemy import String, Boolean, BigInteger, ForeignKey,Float
from typing import Optional,List
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    tg_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )

    username: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )

    name: Mapped[str | None] = mapped_column(String, nullable=True)
    surname: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String,nullable=True)
    service_type: Mapped[str | None] = mapped_column(String,nullable=True)
    role: Mapped[str | None] = mapped_column(String,nullable=True)



    # Роль: 'client' или 'worker'
    role: Mapped[str] = mapped_column(String, default="client") 

    # --- СВЯЗИ ---
    
    # 1. Связь с профилем работника (One-to-One)
    # Если юзер - клиент, тут будет None.
    worker_profile: Mapped[Optional["WorkerProfile"]] = relationship(
        back_populates="user",
        # cascade="all, delete-orphan" удалит профиль, если удалят юзера
        cascade="all, delete-orphan" 
    )

    # 2. Заказы, которые создал этот юзер (One-to-Many)
    client_orders: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="[Order.customer_id]", # <--- Важно!
        back_populates="customer"
    )
    worker_orders: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="[Order.worker_id]",   # <--- Важно!
        back_populates="worker"
    )


    hashed_password: Mapped[str] = mapped_column(
        String(1024), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)


class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # СВЯЗЬ ОДИН-К-ОДНОМУ
    # unique=True гарантирует, что у одного юзера только один профиль
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Обратная связь
    user: Mapped["User"] = relationship(back_populates="worker_profile")

    # Поля анкеты
    description: Mapped[Optional[str]] = mapped_column(String) # О себе
    company_name: Mapped[Optional[str]] = mapped_column(String)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    
    # Можно хранить список ссылок на фото работ (портфолио)
    # В PG это можно делать через ARRAY или JSON
    # portfolio_photos: Mapped[list[str]] = mapped_column(JSON, default=list)