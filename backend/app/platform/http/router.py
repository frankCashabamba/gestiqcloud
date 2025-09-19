from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import format_datetime
from importlib import import_module
from typing import Optional, Tuple, Callable

from fastapi import APIRouter, Depends, Response
import os

logger = logging.getLogger("app.router")


# ----------------------------
# Utilidades comunes
# ----------------------------

def _httpdate(dt: datetime) -> str:
    """Formatea a HTTP-date (IMF-fixdate) en UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return format_datetime(dt, usegmt=True)

def _legacy_deprecation_dependency(response: Response):
    """Inyecta headers de deprecación/retirada para rutas legacy."""
    from app.config.settings import settings
    # Deprecation: "true" o fecha
    dep = getattr(settings, "LEGACY_DEPRECATION", None)  # puede ser bool|datetime|str
    if isinstance(dep, datetime):
        response.headers["Deprecation"] = _httpdate(dep)
    elif dep:
        response.headers["Deprecation"] = "true"
    else:
        response.headers["Deprecation"] = "true"  # fallback conservador

    sunset = getattr(settings, "LEGACY_SUNSET", None)     # datetime|str|None
    link = getattr(settings, "LEGACY_DEPRECATION_LINK", None)
    if isinstance(sunset, datetime):
        response.headers["Sunset"] = _httpdate(sunset)
    elif sunset:
        response.headers["Sunset"] = str(sunset)
    if link:
        response.headers["Link"] = f'<{link}>; rel="deprecation"'

def _wrap_deprecated_router(rt: APIRouter) -> APIRouter:
    """Envuelve un router para marcar todas sus rutas como deprecated y añadir dependencia de headers legacy."""
    wrapper = APIRouter(dependencies=[Depends(_legacy_deprecation_dependency)])
    # marcar las rutas existentes como deprecated (si procede)
    for route in getattr(rt, "routes", []):
        try:
            route.deprecated = True  # type: ignore[attr-defined]
        except Exception:
            pass
    wrapper.include_router(rt)
    return wrapper

def _import_attr(module_path: str, attr: str = "router"):
    mod = import_module(module_path)
    return getattr(mod, attr)

def include_router_safe(
    r: APIRouter,
    primary: Tuple[str, str],                 # (module_path, attr)
    *,
    prefix: str = "",
    fallback: Optional[Tuple[str, str]] = None,
    mark_deprecated: bool = False,
) -> bool:
    """
    Intenta incluir el router `primary`. Si falla y hay `fallback`, lo intenta.
    Si `mark_deprecated=True`, envuelve con _wrap_deprecated_router antes de incluir.
    """
    def _include(module_path: str, attr: str) -> None:
        rt: APIRouter = _import_attr(module_path, attr)
        if mark_deprecated:
            rt = _wrap_deprecated_router(rt)
        r.include_router(rt, prefix=prefix)

    try:
        _include(*primary)
        logger.debug("Mounted router %s.%s at prefix='%s' (deprecated=%s)", primary[0], primary[1], prefix, mark_deprecated)
        return True
    except Exception as e:
        logger.debug(
            "Skip mounting %s.%s (primary): %s",
            primary[0], primary[1], e, exc_info=True
        )
        if fallback:
            try:
                _include(*fallback)
                logger.debug(
                    "Mounted fallback router %s.%s at prefix='%s' (deprecated=%s)",
                    fallback[0], fallback[1], prefix, mark_deprecated,
                )
                return True
            except Exception as e2:
                logger.debug(
                    "Skip mounting %s.%s (fallback): %s",
                    fallback[0], fallback[1], e2, exc_info=True
                )
    return False


# ----------------------------
# Montaje de secciones
# ----------------------------

def _mount_empresas(r: APIRouter) -> None:
    include_router_safe(r, ("app.modules.empresa.interface.http.admin", "router"))
    include_router_safe(r, ("app.modules.empresa.interface.http.tenant", "router"))

def build_api_router() -> APIRouter:
    """Agrega routers de todos los módulos, con fallback a paths legacy cuando aplique."""
    r = APIRouter()

    # Identity
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.admin", "router"),
        prefix="/admin",
        fallback=("app.api.v1.admin.auth", "router"),
    )
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.tenant", "router"),
        prefix="/tenant",
        fallback=("app.api.v1.tenant.auth", "router"),
    )
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.profile", "router"),
        fallback=("app.api.v1.profile", "router"),
    )
    # Generic auth alias (/api/v1/auth/*) + me + telemetry
    include_router_safe(r, ("app.api.v1.auth", "router"))
    include_router_safe(r, ("app.api.v1.me", "router"))
    include_router_safe(r, ("app.api.v1.telemetry", "router"))
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.sessions", "router"),
        prefix="/tenant",
        fallback=("app.api.v1.tenant.sessions", "router"),
    )

    # Productos
    include_router_safe(r, ("app.modules.productos.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.productos.interface.http.admin", "router"))

    # Empresas
    _mount_empresas(r)
    # Alta de empresas: usar router moderno únicamente

    # Clientes
    include_router_safe(r, ("app.modules.clients.interface.http.tenant", "router"))

    # Módulos
    include_router_safe(r, ("app.modules.modulos.interface.http.admin", "router"))
    include_router_safe(r, ("app.modules.modulos.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.modulos.interface.http.public", "router"))

    # Module registry (catalog)
    include_router_safe(r, ("app.modules.registry.interface.http.admin", "router"), prefix="/admin")
    include_router_safe(r, ("app.modules.registry.interface.http.tenant", "router"))

    # Admin config (modern)
    include_router_safe(r, ("app.modules.admin_config.interface.http.admin", "router"), prefix="/admin")

    # Facturación
    include_router_safe(r, ("app.modules.facturacion.interface.http.tenant", "router"))

    # Imports (opcional: controlado por IMPORTS_ENABLED)
    if os.getenv("IMPORTS_ENABLED", "0") in ("1", "true", "True"):  # habilita solo si está ON
        if include_router_safe(r, ("app.modules.imports.interface.http.tenant", "router")):
            include_router_safe(
                r,
                ("app.modules.imports.interface.http.tenant", "legacy_router"),
                prefix="/legacy",
                mark_deprecated=True,
            )

    # Contabilidad
    include_router_safe(r, ("app.modules.contabilidad.interface.http.tenant", "router"))

    # Facturae
    include_router_safe(r, ("app.modules.facturae.interface.http.tenant", "router"))

    # Importador Excel
    include_router_safe(r, ("app.modules.importador_excel.interface.http.tenant", "router"))

    # Settings (tenant)
    include_router_safe(r, ("app.modules.settings.interface.http.tenant", "router"), prefix="/tenant/settings")

    # Tenant onboarding/configuración inicial (router histórico no modular)
    include_router_safe(r, ("app.routers.configuracionincial", "router"), prefix="/tenant")

    # Admin usuarios (router histórico): mantener mientras exista el panel actual
    include_router_safe(r, ("app.routers.admin.usuarios", "router"), prefix="/admin/usuarios")

    # Roles base (histórico para admin actual): CRUD de roles
    include_router_safe(r, ("app.routers.roles", "router"))

    # Legacy endpoints: removed (modern routers in use)

    # Legacy routers retirados: no intentar montarlos para evitar ruido en logs

    return r
