from __future__ import annotations

from sqlalchemy import Integer, String, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ProductoORM(Base):
    __tablename__ = "core_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    precio: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Tenant scope (FK a core_empresa.id)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)

