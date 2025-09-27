"""Module: clients.py

Auto-generated module docstring."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.config.database import Base


class Cliente(Base):
    """ Class Cliente - auto-generated docstring. """
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    identificacion: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    telefono: Mapped[str] = mapped_column(String, nullable=True)
    direccion: Mapped[str] = mapped_column(String, nullable=True)
    localidad: Mapped[str] = mapped_column(String, nullable=True)
    provincia: Mapped[str] = mapped_column(String, nullable=True)
    pais: Mapped[str] = mapped_column(String, nullable=True)
    codigo_postal: Mapped[str] = mapped_column(String, nullable=True)

    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
