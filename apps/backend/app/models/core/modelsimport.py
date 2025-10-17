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
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

UUID = PGUUID(as_uuid=True)  # UUID columns for Postgres
# Dialect-aware tenant UUID: on SQLite use String(36) to accept plain strings
from sqlalchemy import String as _String
TENANT_UUID = PGUUID(as_uuid=True).with_variant(_String(36), "sqlite")

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
        {"extend_existing": True},
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # Tenant isolation (primary key for multi-tenant)
    tenant_id = mapped_column(TENANT_UUID, index=True, nullable=True)
    # DEPRECATED: empresa_id will be removed in v2.0 - use tenant_id instead
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    source_type = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'receipts'|'documento'
    origin = mapped_column(String, nullable=False)  # 'excel'|'ocr'|'api'
    file_key = mapped_column(String)  # S3/MinIO path
    mapping_id = mapped_column(UUID, nullable=True)
    status = mapped_column(String, default="PENDING")  # PENDING|PARSING|READY|VALIDATED|PARTIAL|ERROR|PROMOTED
    # Use String for created_by to keep SQLite-friendly tests; store user UUID string if available
    created_by = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    items = relationship("ImportItem", back_populates="batch", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_import_batches_tenant_status_created", "tenant_id", "status", "created_at"),
    )


class ImportItem(Base):
    __tablename__ = "import_items"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # Tenant isolation (primary key for multi-tenant)
    tenant_id = mapped_column(TENANT_UUID, index=True, nullable=True)
    batch_id = mapped_column(ForeignKey("import_batches.id"), index=True, nullable=False)
    idx = mapped_column(Integer, nullable=False)  # index within the file
    # JSONB columns for PostgreSQL (better indexing), JSON for SQLite compatibility
    raw = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)  # as received
    normalized = mapped_column(JSONB().with_variant(JSON(), "sqlite"))  # after template applied
    status = mapped_column(String, default="PENDING")  # PENDING|OK|ERROR_VALIDATION|ERROR_PROMOTION|PROMOTED
    errors = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list)  # [{field, message}]
    dedupe_hash = mapped_column(String, index=True)  # sha256(...)
    idempotency_key = mapped_column(String, index=True)  # tenant+file+idx (tenant-scoped)
    promoted_to = mapped_column(String)  # 'invoices'|'expenses'|'bank_txn'
    promoted_id = mapped_column(UUID, nullable=True)
    promoted_at = mapped_column(DateTime(timezone=True), nullable=True)

    batch = relationship("ImportBatch", back_populates="items")

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_import_items_tenant_idem"),
        Index("ix_import_items_tenant_dedupe", "tenant_id", "dedupe_hash"),
        Index("ix_import_items_normalized_gin", "normalized", postgresql_using="gin"),
        Index("ix_import_items_raw_gin", "raw", postgresql_using="gin"),
        Index(
            "ix_import_items_doc_type",
            text("((normalized->>'doc_type'))"),
            postgresql_where=text("normalized ? 'doc_type'"),
        ),
    )


class ImportAttachment(Base):
    __tablename__ = "import_attachments"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # Tenant isolation (primary key for multi-tenant)
    tenant_id = mapped_column(TENANT_UUID, index=True, nullable=True)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    kind = mapped_column(String, nullable=False)  # 'photo'|'file'
    file_key = mapped_column(String, nullable=False)  # path in S3/MinIO or local path
    sha256 = mapped_column(String, nullable=True)
    ocr_text = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportMapping(Base):
    __tablename__ = "import_mappings"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # Tenant isolation (primary key for multi-tenant)
    tenant_id = mapped_column(TENANT_UUID, index=True, nullable=True)
    # DEPRECATED: empresa_id will be removed in v2.0 - use tenant_id instead
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    name = mapped_column(String, nullable=False)
    source_type = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'receipts'|...
    version = mapped_column(Integer, default=1)
    # JSONB columns for PostgreSQL (better indexing), JSON for SQLite compatibility
    mappings = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)  # {'dest': 'src'}
    transforms = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)  # {'field': 'date'|{type:'date'}}
    defaults = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)  # {'field': value}
    dedupe_keys = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)  # ['issuer_tax_id','invoice_number',...]
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_import_mappings_tenant_source", "tenant_id", "source_type"),
        Index("ix_import_mappings_mappings_gin", "mappings", postgresql_using="gin"),
    )


class ImportItemCorrection(Base):
    __tablename__ = "import_item_corrections"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # Tenant isolation (primary key for multi-tenant)
    tenant_id = mapped_column(TENANT_UUID, index=True, nullable=True)
    # DEPRECATED: empresa_id will be removed in v2.0 - use tenant_id instead
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
    # Tenant isolation (primary key for multi-tenant)
    tenant_id = mapped_column(TENANT_UUID, index=True, nullable=True)
    # DEPRECATED: empresa_id will be removed in v2.0 - use tenant_id instead
    empresa_id = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    promoted_to = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'expenses'
    promoted_ref = mapped_column(String, nullable=True)  # domain identifier (string)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportOCRJob(Base):
    __tablename__ = "import_ocr_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # Tenant isolation (primary key for multi-tenant)
    tenant_id: Mapped[uuid.UUID] = mapped_column(TENANT_UUID, index=True, nullable=True)
    # DEPRECATED: empresa_id will be removed in v2.0 - use tenant_id instead
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    # JSONB for PostgreSQL (better indexing), JSON for SQLite compatibility
    result: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
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
        Index("ix_import_ocr_jobs_tenant_status_created", "tenant_id", "status", "created_at"),
    )
