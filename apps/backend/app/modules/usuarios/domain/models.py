from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UsuarioEmpresaAggregate:
    """Aggregate view of a usuario-empresa with assigned modules and roles."""

    id: int
    tenant_id: int
    email: str
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    username: str | None = None
    es_admin_empresa: bool = False
    activo: bool = True
    modulos: list[int] = field(default_factory=list)
    roles: list[int] = field(default_factory=list)
    ultimo_login_at: datetime | None = None
