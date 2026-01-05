from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from sqlalchemy import String, Boolean, BigInteger

class Order(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    


