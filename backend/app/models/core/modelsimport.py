"""Module: modelsimport.py

Auto-generated module docstring."""

from sqlalchemy import JSON, ForeignKey, text,UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

class DatosImportados(Base):
    __tablename__ = "datos_importados"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tipo: Mapped[str] = mapped_column()  # "factura", "recibo", "movimiento"
    origen: Mapped[str] = mapped_column()  # "ocr", "excel", "manual"
    datos: Mapped[dict] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(default="pendiente")  # pendiente, validado, rechazado
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
    fecha_creacion: Mapped[str] = mapped_column(server_default=text("now()"))
    hash: Mapped[str] = mapped_column(unique=True)  
    
    __table_args__ = (
        UniqueConstraint("hash", name="uq_hash_documento"),
    )
   
