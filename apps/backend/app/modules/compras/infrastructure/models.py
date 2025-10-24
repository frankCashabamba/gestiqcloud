from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Date, Float, DateTime, func
from app.config.database import Base


class Compra(Base):
    __tablename__ = "compras"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    proveedor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estado: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

