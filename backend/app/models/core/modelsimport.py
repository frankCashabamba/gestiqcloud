"""Module: modelsimport.py

Auto-generated module docstring."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime  # <- faltaban
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

UUID = PGUUID(as_uuid=True)  # para columnas UUID Postgres
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
   
class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    source_type = mapped_column(String, nullable=False)     # 'invoices'|'bank'|'receipts'|'documento'
    origin = mapped_column(String, nullable=False)          # 'excel'|'ocr'|'api'
    file_key = mapped_column(String)                        # ruta S3/MinIO
    mapping_id = mapped_column(UUID, nullable=True)
    status = mapped_column(String, default="PENDING")       # PENDING|PARSING|READY|VALIDATED|PARTIAL|ERROR|PROMOTED
    created_by = mapped_column(UUID, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    items = relationship("ImportItem", back_populates="batch", cascade="all, delete-orphan")

class ImportItem(Base):
    __tablename__ = "import_items"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    batch_id = mapped_column(ForeignKey("import_batches.id"), index=True, nullable=False)
    idx = mapped_column(Integer, nullable=False)            # posición en el archivo
    raw = mapped_column(JSON, nullable=False)               # tal cual llegó
    normalized = mapped_column(JSON)                        # tras aplicar plantilla
    status = mapped_column(String, default="PENDING")       # PENDING|OK|ERROR_VALIDATION|ERROR_PROMOTION|PROMOTED
    errors = mapped_column(JSON, default=list)              # [{campo, mensaje}]
    dedupe_hash = mapped_column(String, index=True)         # sha256(...)
    idempotency_key = mapped_column(String, index=True)     # empresa+file+idx
    promoted_to = mapped_column(String)                     # 'invoices'|'expenses'|'bank_txn'
    promoted_id = mapped_column(UUID, nullable=True)
    promoted_at = mapped_column(DateTime(timezone=True), nullable=True)

    batch = relationship("ImportBatch", back_populates="items")
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_import_item_idem"),)