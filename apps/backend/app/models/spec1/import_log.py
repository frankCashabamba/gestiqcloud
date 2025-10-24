"""
Import Log Model - Trazabilidad de importaciones
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ImportLog(Base):
    """Log de trazabilidad de importaciones"""
    __tablename__ = "import_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    sheet: Mapped[str] = mapped_column(Text, nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    
    entity: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    digest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self):
        return f"<ImportLog {self.source_file} - {self.entity} {self.entity_id}>"
