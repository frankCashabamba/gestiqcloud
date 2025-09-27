
from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class UsuarioEmpresaAggregate:
    """Aggregate view of a usuario-empresa with assigned modules and roles."""

    id: int
    empresa_id: int
    email: str
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    username: str | None = None
    es_admin_empresa: bool = False
    activo: bool = True
    modulos: List[int] = field(default_factory=list)
    roles: List[int] = field(default_factory=list)
    ultimo_login_at: datetime | None = None
