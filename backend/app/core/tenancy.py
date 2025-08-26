# app/core/tenancy.py
from uuid import UUID, uuid5
from app.config.settings import settings

_NAMESPACE = UUID(settings.TENANT_NAMESPACE_UUID)

def tenant_uuid_for_user_empresa(user_id: str | int, empresa_id: str | int) -> UUID:
    """UUID estable para un usuario dentro de una empresa."""
    return uuid5(_NAMESPACE, f"user:{user_id}|empresa:{empresa_id}")

def tenant_uuid_for_admin(user_id: str | int) -> UUID:
    """UUID estable para sesiones admin (si tu admin no tiene empresa)."""
    return uuid5(_NAMESPACE, f"admin:{user_id}")
