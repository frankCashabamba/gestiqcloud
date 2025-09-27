from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Date, String, Float, DateTime, func
from app.config.database import Base


class CajaMovimiento(Base):
    __tablename__ = "caja_movimientos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BancoMovimiento(Base):
    __tablename__ = "banco_movimientos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[Date] = mapped_column(Date, nullable=False)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

