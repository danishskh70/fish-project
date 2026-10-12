from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

class Customer(Base):
    __tablename__="customers"
    
    id:Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    name:Mapped[str]=mapped_column(String(100),nullable=False)
    phone:Mapped[str]=mapped_column(String(20),nullable=False)
    address:Mapped[str]=mapped_column(String(255),nullable=False)
    is_active:Mapped[bool]=mapped_column(Boolean,nullable=False,server_default=text("true"))