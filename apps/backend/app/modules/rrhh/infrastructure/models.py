from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Date, String, DateTime, func
from app.config.database import Base


class Vacacion(Base):
    __tablename__ = "vacaciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=False)
    inicio: Mapped[Date] = mapped_column(Date, nullable=False)
    fin: Mapped[Date] = mapped_column(Date, nullable=False)
    estado: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

