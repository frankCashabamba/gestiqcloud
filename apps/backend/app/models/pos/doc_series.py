"""Document numbering series model for POS/backoffice."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class DocSeries(Base):
    """Document numbering series."""

    __tablename__ = "doc_series"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    register_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pos_registers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        # NULL = backoffice/general
    )
    doc_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="R=receipt, F=invoice, C=credit_note",
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    current_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reset_policy: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="yearly",
        # yearly, never
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    register = relationship("POSRegister", foreign_keys=[register_id])

    def __repr__(self):
        return f"<DocSeries {self.name} - {self.current_no}>"
