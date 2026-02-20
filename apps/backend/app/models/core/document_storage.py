"""Document Layer – WORM file storage models.

Tracks uploaded files (DocumentFile) and their immutable versions
(DocumentVersion) with SHA-256 content-addressable deduplication.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

UUID = PGUUID(as_uuid=True)
from sqlalchemy import String as _String  # noqa: E402

TENANT_UUID = PGUUID(as_uuid=True).with_variant(_String(36), "sqlite")

from app.config.database import Base  # noqa: E402


class DocumentFile(Base):
    __tablename__ = "document_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata_", JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    versions = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_document_files_tenant_doc_type", "tenant_id", "doc_type"),
        Index("ix_document_files_tenant_status", "tenant_id", "status"),
        {"extend_existing": True},
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(TENANT_UUID, index=True, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("document_files.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    mime: Mapped[str | None] = mapped_column(String, nullable=True)
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("DocumentFile", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("tenant_id", "sha256", name="uq_docver_tenant_sha256"),
        UniqueConstraint("document_id", "version", name="uq_docver_doc_version"),
        Index("ix_docver_tenant_sha256", "tenant_id", "sha256"),
        Index("ix_docver_doc_version_desc", "document_id", desc("version")),
        {"extend_existing": True},
    )
