"""
UoM Models - Unidades de medida y conversiones
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class UoM(Base):
    """Unidad de medida"""
    __tablename__ = "uom"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self):
        return f"<UoM {self.code} - {self.name}>"


class UoMConversion(Base):
    """Conversión entre unidades de medida"""
    __tablename__ = "uom_conversion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_code: Mapped[str] = mapped_column(String(10), ForeignKey("uom.code"), nullable=False)
    to_code: Mapped[str] = mapped_column(String(10), ForeignKey("uom.code"), nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self):
        return f"<UoMConversion {self.from_code} → {self.to_code} ({self.factor})>"
