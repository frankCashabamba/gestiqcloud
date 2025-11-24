import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CompanyUserAggregate:
    """Aggregate view of a company user with assigned modules and roles."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    is_company_admin: bool = False
    is_active: bool = True
    modules: list[uuid.UUID] = field(default_factory=list)
    roles: list[uuid.UUID] = field(default_factory=list)
    last_login_at: datetime | None = None
