"""Module: modelsimport.py

Auto-generated module docstring."""
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

UUID = PGUUID(as_uuid=True)  # para columnas UUID Postgres

from app.config.database import Base

class DatosImportados(Base):
    __tablename__ = "datos_importados"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tipo: Mapped[str] = mapped_column()  # "factura", "recibo", "movimiento" datos
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
    # Use String for created_by to keep SQLite-friendly tests; store user UUID string if available
    created_by = mapped_column(String, nullable=False)
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


class ImportAttachment(Base):
    __tablename__ = "import_attachments"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    kind = mapped_column(String, nullable=False)            # 'photo'|'file'
    file_key = mapped_column(String, nullable=False)        # ruta en S3/MinIO o path local
    sha256 = mapped_column(String, nullable=True)
    ocr_text = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class ImportMapping(Base):
    __tablename__ = "import_mappings"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    name = mapped_column(String, nullable=False)
    source_type = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'receipts'|...
    version = mapped_column(Integer, default=1)
    mappings = mapped_column(JSON, nullable=True)        # {'dest': 'src'}
    transforms = mapped_column(JSON, nullable=True)      # {'field': 'date'|{type:'date'}}
    defaults = mapped_column(JSON, nullable=True)        # {'field': value}
    dedupe_keys = mapped_column(JSON, nullable=True)     # ['issuer_tax_id','invoice_number',...]
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportItemCorrection(Base):
    __tablename__ = "import_item_corrections"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    field = mapped_column(String, nullable=False)
    old_value = mapped_column(JSON, nullable=True)
    new_value = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)



class ImportLineage(Base):
    __tablename__ = "import_lineage"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    promoted_to = mapped_column(String, nullable=False)    # 'invoices'|'bank'|'expenses'
    promoted_ref = mapped_column(String, nullable=True)    # domain identifier (string)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportOCRJob(Base):
    __tablename__ = "import_ocr_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_import_ocr_jobs_status_created", "status", "created_at"),
        Index("ix_import_ocr_jobs_empresa_created", "empresa_id", "created_at"),
    )
