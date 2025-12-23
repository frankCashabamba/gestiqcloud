"""Module: modelsimport.py

Auto-generated module docstring."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

UUID = PGUUID(as_uuid=True)  # UUID columns for Postgres
# Dialect-aware tenant UUID: on SQLite use String(36) to accept plain strings
from sqlalchemy import String as _String  # noqa: E402

TENANT_UUID = PGUUID(as_uuid=True).with_variant(_String(36), "sqlite")

from app.config.database import Base  # noqa: E402


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False)
    source_type = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'receipts'|'documento'
    origin = mapped_column(String, nullable=False)  # 'excel'|'ocr'|'api'
    file_key = mapped_column(String)  # S3/MinIO path
    mapping_id = mapped_column(UUID, nullable=True)
    parser_id = mapped_column(
        String, nullable=True
    )  # Parser elegido (products_excel, csv_invoices, etc)
    parser_choice_confidence = mapped_column(
        String, nullable=True
    )  # Confianza de clasificación (JSON score)
    # Fase A - Clasificación persistida
    suggested_parser = mapped_column(String, nullable=True)  # Parser sugerido por IA/heurística
    classification_confidence = mapped_column(Float, nullable=True)  # Score 0.0-1.0
    ai_enhanced = mapped_column(Boolean, default=False)  # ¿Fue mejorado por IA?
    ai_provider = mapped_column(String, nullable=True)  # 'local'|'openai'|'azure'
    status = mapped_column(
        String, default="PENDING"
    )  # PENDING|PARSING|EMPTY|READY|VALIDATED|PARTIAL|ERROR|PROMOTED
    # Use String for created_by to keep SQLite-friendly tests; store user UUID string if available
    created_by = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Confirmation flow fields (when confidence < threshold)
    requires_confirmation = mapped_column(Boolean, default=False)
    confirmed_at = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_parser = mapped_column(String, nullable=True)
    user_override = mapped_column(Boolean, default=False)

    items = relationship("ImportItem", back_populates="batch", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_import_batches_tenant_status_created",
            "tenant_id",
            "status",
            "created_at",
        ),
        Index("ix_import_batches_ai_provider", "ai_provider"),
        Index("ix_import_batches_ai_enhanced", "ai_enhanced"),
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
    canonical_doc = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )  # CanonicalDocument (SPEC-1) extracted/normalized
    status = mapped_column(
        String, default="PENDING"
    )  # PENDING|OK|ERROR_VALIDATION|ERROR_PROMOTION|PROMOTED
    errors = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=list
    )  # [{field, message}]
    dedupe_hash = mapped_column(String, index=True)  # sha256(...)
    idempotency_key = mapped_column(String, index=True)  # tenant+file+idx (tenant-scoped)
    promoted_to = mapped_column(String)  # 'invoices'|'expenses'|'bank_txn'
    promoted_id = mapped_column(UUID, nullable=True)
    promoted_at = mapped_column(DateTime(timezone=True), nullable=True)

    batch = relationship("ImportBatch", back_populates="items")

    @property
    def validation_errors(self) -> list:
        """Alias para compatibilidad con tests antiguos."""
        return self.errors or []

    @validation_errors.setter
    def validation_errors(self, value: list) -> None:
        self.errors = value

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
    tenant_id = mapped_column(TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False)
    name = mapped_column(String, nullable=False)
    source_type = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'receipts'|...
    version = mapped_column(Integer, default=1)
    # JSONB columns for PostgreSQL (better indexing), JSON for SQLite compatibility
    mappings = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )  # {'dest': 'src'}
    transforms = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )  # {'field': 'date'|{type:'date'}}
    defaults = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )  # {'field': value}
    dedupe_keys = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )  # ['issuer_tax_id','invoice_number',...]
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_import_mappings_tenant_source", "tenant_id", "source_type"),
        Index("ix_import_mappings_mappings_gin", "mappings", postgresql_using="gin"),
    )


class ImportItemCorrection(Base):
    __tablename__ = "import_item_corrections"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    user_id = mapped_column(UUID, nullable=False)
    field = mapped_column(String, nullable=False)
    old_value = mapped_column(JSON, nullable=True)
    new_value = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ImportLineage(Base):
    __tablename__ = "import_lineage"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = mapped_column(TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False)
    item_id = mapped_column(ForeignKey("import_items.id"), index=True, nullable=False)
    promoted_to = mapped_column(String, nullable=False)  # 'invoices'|'bank'|'expenses'
    promoted_ref = mapped_column(String, nullable=True)  # domain identifier (string)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    @property
    def destination_table(self) -> str:
        return self.promoted_to

    @destination_table.setter
    def destination_table(self, value: str) -> None:
        self.promoted_to = value

    @property
    def destination_id(self) -> str | None:
        return self.promoted_ref

    @destination_id.setter
    def destination_id(self, value: str | None) -> None:
        self.promoted_ref = value


class ImportOCRJob(Base):
    __tablename__ = "import_ocr_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    # JSONB for PostgreSQL (better indexing), JSON for SQLite compatibility
    result: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_import_ocr_jobs_status_created", "status", "created_at"),
        Index(
            "ix_import_ocr_jobs_tenant_status_created",
            "tenant_id",
            "status",
            "created_at",
        ),
    )
