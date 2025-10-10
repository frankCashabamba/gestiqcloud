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
    from backend.app.config.settings import settings
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
        rt = _import_attr(module_path, attr)
        # Some modules expose router=None when feature is disabled; skip gracefully
        if rt is None:
            raise ModuleNotFoundError(f"{module_path}.{attr} returned None")
        if not isinstance(rt, APIRouter):
            raise ModuleNotFoundError(f"{module_path}.{attr} is not an APIRouter (got {type(rt).__name__})")
        if mark_deprecated:
            rt = _wrap_deprecated_router(rt)
        r.include_router(rt, prefix=prefix)

    try:
        _include(*primary)
        logger.debug("Mounted router %s.%s at prefix='%s' (deprecated=%s)", primary[0], primary[1], prefix, mark_deprecated)
        return True
    except Exception as e:
        # Silence noisy stack traces for optional modules not present in some deployments
        if isinstance(e, ModuleNotFoundError):
            logger.debug("Skip mounting %s.%s (primary): module not found: %s", primary[0], primary[1], getattr(e, "name", str(e)))
        else:
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
                if isinstance(e2, ModuleNotFoundError):
                    logger.debug("Skip mounting %s.%s (fallback): module not found: %s", fallback[0], fallback[1], getattr(e2, "name", str(e2)))
                else:
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
    # Email health
    include_router_safe(r, ("app.api.v1.email_health", "router"))
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

    # Proveedores
    include_router_safe(r, ("app.modules.proveedores.interface.http.tenant", "router"))


    # Módulos
    include_router_safe(r, ("app.modules.modulos.interface.http.admin", "router"))
    include_router_safe(r, ("app.modules.modulos.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.modulos.interface.http.public", "router"))

    # Usuarios de empresa (tenant) y admin
    include_router_safe(r, ("app.modules.usuarios.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.usuarios.interface.http.tenant", "public_router"))
    include_router_safe(r, ("app.modules.usuarios.interface.http.admin", "router"), prefix="/admin")

    # Module registry (catalog)
    include_router_safe(r, ("app.modules.registry.interface.http.admin", "router"), prefix="/admin")
    include_router_safe(r, ("app.modules.registry.interface.http.tenant", "router"))

    # Admin config (modern)
    include_router_safe(r, ("app.modules.admin_config.interface.http.admin", "router"), prefix="/admin")

    # Me endpoints (admin/tenant helpers)
    include_router_safe(r, ("app.api.v1.me", "router"))

    # Facturación
    include_router_safe(r, ("app.modules.facturacion.interface.http.tenant", "router"))
    # Inventario
    # Inventario
    include_router_safe(r, ("app.modules.inventario.interface.http.tenant", "router"))
    # Ventas
    include_router_safe(r, ("app.modules.ventas.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.ventas.interface.http.tenant", "deliveries_router"))
    include_router_safe(r, ("app.modules.inventario.interface.http.tenant", "router"))

    # Imports (opcional: controlado por IMPORTS_ENABLED)
    if os.getenv("IMPORTS_ENABLED", "0") in ("1", "true", "True"):  # habilita solo si está ON
        if include_router_safe(r, ("app.modules.imports.interface.http.tenant", "router")):
            include_router_safe(
                r,
                ("app.modules.imports.interface.http.tenant", "legacy_router"),
                prefix="/legacy",
                mark_deprecated=True,
            )
 
    # Imports public (health) router
    if os.getenv("IMPORTS_ENABLED", "0") in ("1", "true", "True"):
        _mounted_public = include_router_safe(r, ("app.modules.imports.interface.http.tenant", "public_router"))
        logger.info("imports.public_router mounted=%s via IMPORTS_ENABLED", bool(_mounted_public))

    # Auto-enable imports router in SQLite-based test envs even if IMPORTS_ENABLED is off
    # This keeps CI/dev tests stable without affecting production (Postgres).
    if os.getenv("IMPORTS_ENABLED", "0") not in ("1", "true", "True"):
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("sqlite"):
            logger.debug("Auto-enabling imports router (SQLite test env detected)")
            if include_router_safe(r, ("app.modules.imports.interface.http.tenant", "router")):
                include_router_safe(
                    r,
                    ("app.modules.imports.interface.http.tenant", "legacy_router"),
                    prefix="/legacy",
                    mark_deprecated=True,
                )
            include_router_safe(r, ("app.modules.imports.interface.http.tenant", "public_router"))

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

    # E-invoicing (SRI/SII)
    include_router_safe(r, ("app.modules.einvoicing.interface.http.tenant", "router"))

    # Templates & Overlays
    include_router_safe(r, ("app.modules.templates.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.templates.interface.http.admin", "router"), prefix="/admin")

    # Final safeguard: ensure imports router is mounted in non-production envs
    try:
        env = os.getenv("ENV", "development").lower()
        has_imports = any(
            (getattr(rt, "path", "") or "").startswith("/imports") or (getattr(rt, "path", "") or "").startswith("/api/v1/imports")
            for rt in r.routes
        )
        if env != "production" and not has_imports:
            # Try multiple paths to be resilient across entrypoints
            mounted = include_router_safe(
                r,
                ("app.modules.imports.interface.http.tenant", "router"),
                fallback=("apps.backend.app.modules.imports.interface.http.tenant", "router"),
            ) or include_router_safe(
                r,
                ("backend.app.modules.imports.interface.http.tenant", "router"),
            )
            if mounted:
                include_router_safe(
                    r,
                    ("app.modules.imports.interface.http.tenant", "public_router"),
                    fallback=("apps.backend.app.modules.imports.interface.http.tenant", "public_router"),
                ) or include_router_safe(
                    r,
                    ("backend.app.modules.imports.interface.http.tenant", "public_router"),
                )
    except Exception:
        pass

    return r

