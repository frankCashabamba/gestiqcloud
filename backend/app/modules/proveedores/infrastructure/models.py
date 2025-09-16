from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, func
from app.config.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

