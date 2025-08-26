# app/models/auditoria_importacion.py
from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.config.database import Base
from sqlalchemy.dialects.postgresql import JSONB

class AuditoriaImportacion(Base):
    __tablename__ = "auditoria_importacion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    documento_id: Mapped[int] = mapped_column(index=True)  # id temporal o definitivo
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"))

    cambios: Mapped[dict] = mapped_column(JSONB)  # aquí guardamos el diff completo
    fecha: Mapped[datetime] = mapped_column(server_default=text("now()"))

    usuario = relationship("UsuarioEmpresa")  # si quieres acceder a info usuario
