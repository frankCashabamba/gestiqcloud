# app/models/auditoria_importacion.py
from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

# Column type for Postgres UUID
PG_UUID = PGUUID(as_uuid=True)


class ImportAudit(Base):
    __tablename__ = "import_audits"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(index=True)  # id temporal o definitivo (legacy)
    # Nuevos campos para enlazar con staging por lotes
    batch_id: Mapped[PyUUID | None] = mapped_column(PG_UUID, nullable=True, index=True)
    item_id: Mapped[PyUUID | None] = mapped_column(PG_UUID, nullable=True, index=True)
    tenant_id: Mapped[PyUUID | None] = mapped_column(
        PG_UUID, ForeignKey("tenants.id"), index=True, nullable=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("company_users.id"))

    changes: Mapped[dict] = mapped_column(JSONB)  # aquí guardamos el diff completo
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    user = relationship("CompanyUser")  # si quieres acceder a info usuario
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
