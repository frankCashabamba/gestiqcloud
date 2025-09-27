# app/models/auditoria_importacion.py
from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.config.database import Base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import UUID as PyUUID

# Column type for Postgres UUID
PG_UUID = PGUUID(as_uuid=True)

class AuditoriaImportacion(Base):
    __tablename__ = "auditoria_importacion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    documento_id: Mapped[int] = mapped_column(index=True)  # id temporal o definitivo (legacy)
    # Nuevos campos para enlazar con staging por lotes
    batch_id: Mapped[PyUUID | None] = mapped_column(PG_UUID, nullable=True, index=True)
    item_id: Mapped[PyUUID | None] = mapped_column(PG_UUID, nullable=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"))

    cambios: Mapped[dict] = mapped_column(JSONB)  # aquí guardamos el diff completo
    fecha: Mapped[datetime] = mapped_column(server_default=text("now()"))

    usuario = relationship("UsuarioEmpresa")  # si quieres acceder a info usuario
