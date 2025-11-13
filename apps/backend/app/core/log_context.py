"""
Contexto de logging para multi-tenant.
Permite agregar tenant_id y request_id a todos los logs automáticamente.
"""
from contextvars import ContextVar
from typing import Optional

# Context variables para tenant y request
tenant_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
request_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_tenant_context(tenant_id: str) -> None:
    """Establece el tenant_id en el contexto actual"""
    tenant_ctx.set(tenant_id)


def get_tenant_context() -> Optional[str]:
    """Obtiene el tenant_id del contexto actual"""
    return tenant_ctx.get()


def set_request_context(request_id: str) -> None:
    """Establece el request_id en el contexto actual"""
    request_ctx.set(request_id)


def get_request_context() -> Optional[str]:
    """Obtiene el request_id del contexto actual"""
    return request_ctx.get()


def clear_context() -> None:
    """Limpia el contexto (útil en tests)"""
    tenant_ctx.set(None)
    request_ctx.set(None)


def get_log_extra() -> dict:
    """
    Devuelve un dict con el contexto actual para agregar a logs.
    
    Uso:
        logger.info("evento", extra=get_log_extra())
    """
    extra = {}
    tenant_id = tenant_ctx.get()
    request_id = request_ctx.get()
    
    if tenant_id:
        extra["tenant_id"] = tenant_id
    if request_id:
        extra["request_id"] = request_id
        
    return extra
