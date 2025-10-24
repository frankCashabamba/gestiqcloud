"""Module: usuarioempresa.py

Auto-generated module docstring."""

# app/models/usuario.py

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String,Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from sqlalchemy.orm import relationship


from sqlalchemy.dialects.postgresql import UUID
from app.config.database import Base

class UsuarioEmpresa(Base):
    """
    Modelo de usuario vinculado a una empresa (usuarios_usuarioempresa).

    Atributos:
        id (int): Identificador primario.
        empresa_id (int): Clave foránea a la tabla de empresas.
        nombre_encargado (str): Nombre del responsable.
        apellido_encargado (str): Apellido del responsable.
        email (str): Correo electrónico único del usuario.
        username (str): Nombre de usuario único.
        activo (bool): Indica si el usuario está activo.
        es_admin_empresa (bool): Marca si el usuario tiene rol de administrador.
        password_hash (str): Hash de la contraseña.
        password_token_created (datetime): Fecha de creación del token de recuperación.
    """

   
    __tablename__ = "usuarios_usuarioempresa"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))

    nombre_encargado: Mapped[str] = mapped_column(String(100))
    apellido_encargado: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True)

    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    es_admin_empresa: Mapped[bool] = mapped_column(Boolean, default=False)

    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    password_token_created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
        # 🔹 Relación unidireccional hacia Empresa
    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # Multi-tenant (ajusta a tu tipo real: UUID si tus tenants son UUID; si no, String)
    # Keep ORM nullable for test (SQLite) friendliness; DB enforces NOT NULL via migrations on Postgres
    tenant_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)  # pylint: ignore

    # Auditoría de acceso / seguridad
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_password_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()# pylint: disable=not-callable
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()# pylint: disable=not-callable
    )

    def __repr__(self):
        """ Function __repr__ - auto-generated docstring. """
        return f"<UsuarioEmpresa email={self.email}>"

    @property
    def is_active(self) -> bool:
        """ Function is_active - auto-generated docstring. """
        return self.activo

    @property
    def is_superuser(self) -> bool:
        """ Function is_superuser - auto-generated docstring. """
        return self.es_admin_empresa

    @property
    def is_staff(self) -> bool:
        """ Function is_staff - auto-generated docstring. """
        return self.es_admin_empresa
