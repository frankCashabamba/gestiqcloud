from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from email.utils import format_datetime
from importlib import import_module

from fastapi import APIRouter, Depends, Response

logger = logging.getLogger("app.router")


# ----------------------------
# Utilidades comunes
# ----------------------------


def _httpdate(dt: datetime) -> str:
    """Formatea a HTTP-date (IMF-fixdate) en UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
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

    sunset = getattr(settings, "LEGACY_SUNSET", None)  # datetime|str|None
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
    primary: tuple[str, str],  # (module_path, attr)
    *,
    prefix: str = "",
    fallback: tuple[str, str] | None = None,
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
            raise ModuleNotFoundError(
                f"{module_path}.{attr} is not an APIRouter (got {type(rt).__name__})"
            )
        if mark_deprecated:
            rt = _wrap_deprecated_router(rt)
        r.include_router(rt, prefix=prefix)

    try:
        _include(*primary)
        logger.debug(
            "Mounted router %s.%s at prefix='%s' (deprecated=%s)",
            primary[0],
            primary[1],
            prefix,
            mark_deprecated,
        )
        return True
    except Exception as e:
        # Silence noisy stack traces for optional modules not present in some deployments
        if isinstance(e, ModuleNotFoundError):
            logger.debug(
                "Skip mounting %s.%s (primary): module not found: %s",
                primary[0],
                primary[1],
                getattr(e, "name", str(e)),
            )
        else:
            logger.debug(
                "Skip mounting %s.%s (primary): %s",
                primary[0],
                primary[1],
                e,
                exc_info=True,
            )
        if fallback:
            try:
                _include(*fallback)
                logger.debug(
                    "Mounted fallback router %s.%s at prefix='%s' (deprecated=%s)",
                    fallback[0],
                    fallback[1],
                    prefix,
                    mark_deprecated,
                )
                return True
            except Exception as e2:
                if isinstance(e2, ModuleNotFoundError):
                    logger.debug(
                        "Skip mounting %s.%s (fallback): module not found: %s",
                        fallback[0],
                        fallback[1],
                        getattr(e2, "name", str(e2)),
                    )
                else:
                    logger.debug(
                        "Skip mounting %s.%s (fallback): %s",
                        fallback[0],
                        fallback[1],
                        e2,
                        exc_info=True,
                    )
    return False


# ----------------------------
# Montaje de secciones
# ----------------------------


def _mount_empresas(r: APIRouter) -> None:
    include_router_safe(r, ("app.modules.company.interface.http.admin", "router"))
    include_router_safe(r, ("app.modules.company.interface.http.purge", "router"))
    include_router_safe(r, ("app.modules.company.interface.http.tenant", "router"))


def build_api_router() -> APIRouter:
    """Agrega routers de todos los módulos, con fallback a paths legacy cuando aplique."""
    r = APIRouter()

    # Identity
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.admin", "router"),
        prefix="/admin",
    )
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.tenant", "router"),
        prefix="/tenant",
    )
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.profile", "router"),
    )
    # Generic auth alias (/api/v1/auth/*) + me + telemetry
    include_router_safe(r, ("app.api.v1.auth", "router"))
    include_router_safe(r, ("app.api.v1.me", "router"))
    include_router_safe(r, ("app.api.v1.telemetry", "router"))
    # Prometheus metrics
    include_router_safe(r, ("app.api.v1.metrics", "router"))
    include_router_safe(r, ("app.api.v1.einvoicing", "router"))
    # Email health
    include_router_safe(r, ("app.api.v1.email_health", "router"))
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.sessions", "router"),
        prefix="/tenant",
    )

    # Products - mount under /tenant like clientes
    include_router_safe(r, ("app.modules.products.interface.http.public", "router"))
    include_router_safe(
        r, ("app.modules.products.interface.http.tenant", "router"), prefix="/tenant"
    )
    # Empresas
    _mount_empresas(r)
    # Onboarding initialization
    include_router_safe(r, ("app.routers.onboarding_init", "router"))
    # Alta de empresas: usar router moderno únicamente

    # Clientes (mount under /tenant to align FE endpoints)
    include_router_safe(
        r, ("app.modules.clients.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Suppliers (mount under /tenant)
    include_router_safe(
        r, ("app.modules.suppliers.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Módulos
    include_router_safe(r, ("app.modules.modules_catalog.interface.http.admin", "router"))
    include_router_safe(r, ("app.modules.modules_catalog.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.modules_catalog.interface.http.public", "router"))

    # Users (tenant) and admin
    include_router_safe(r, ("app.modules.users.interface.http.tenant", "router"))
    include_router_safe(r, ("app.modules.users.interface.http.tenant", "public_router"))
    include_router_safe(r, ("app.modules.users.interface.http.admin", "router"), prefix="/admin")

    # Module registry (catalog)
    include_router_safe(r, ("app.modules.registry.interface.http.admin", "router"), prefix="/admin")
    include_router_safe(r, ("app.modules.registry.interface.http.tenant", "router"))

    # Admin config (modern)
    include_router_safe(
        r, ("app.modules.admin_config.interface.http.admin", "router"), prefix="/admin"
    )

    # Me endpoints (admin/tenant helpers)
    include_router_safe(r, ("app.api.v1.me", "router"))

    # Invoicing
    include_router_safe(
        r, ("app.modules.invoicing.interface.http.tenant", "router"), prefix="/tenant"
    )
    include_router_safe(
        r,
        ("app.modules.invoicing.interface.http.send_email", "router"),
        prefix="/tenant",
    )
    # Inventario
    include_router_safe(
        r, ("app.modules.inventory.interface.http.tenant", "router"), prefix="/tenant"
    )
    # Sales
    include_router_safe(r, ("app.modules.sales.interface.http.tenant", "router"), prefix="/tenant")
    include_router_safe(
        r,
        ("app.modules.sales.interface.http.tenant", "deliveries_router"),
        prefix="/tenant",
    )
    # Documents (draft/issue)
    include_router_safe(
        r,
        ("app.modules.documents.interface.http.tenant", "router"),
        prefix="/tenant",
    )
    include_router_safe(
        r,
        ("app.modules.documents.interface.http.tenant", "legacy_router"),
        prefix="/tenant",
        mark_deprecated=True,
    )
    include_router_safe(
        r,
        ("app.modules.documents.interface.http.tenant", "documents_router"),
        prefix="/tenant",
    )

    # Purchases
    include_router_safe(
        r, ("app.modules.purchases.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Expenses
    include_router_safe(
        r, ("app.modules.expenses.interface.http.tenant", "router"), prefix="/tenant"
    )

    # (deduplicated) Inventario router is already mounted above

    # Imports (controlado por IMPORTS_ENABLED)
    if os.getenv("IMPORTS_ENABLED", "0").lower() in ("1", "true"):
        include_router_safe(
            r, ("app.modules.imports.interface.http.tenant", "router"), prefix="/tenant"
        )

        # Smart Preview endpoints
        include_router_safe(
            r, ("app.modules.imports.interface.http.preview", "router"), prefix="/imports"
        )

        # Import Files endpoints (classification, etc.)
        include_router_safe(
            r, ("app.modules.imports.interface.http.preview", "files_router"), prefix="/imports"
        )

        # Smart Router analyze endpoint
        include_router_safe(
            r, ("app.modules.imports.interface.http.analyze", "router"), prefix="/imports"
        )

        # Batch confirmation endpoint
        include_router_safe(
            r, ("app.modules.imports.interface.http.confirm", "router"), prefix="/imports"
        )

        # OCR Metrics endpoint
        include_router_safe(r, ("app.modules.imports.interface.http.metrics", "router"), prefix="")

        # Imports public (health) router
        _mounted_public = include_router_safe(
            r, ("app.modules.imports.interface.http.tenant", "public_router")
        )
        logger.info(
            "imports.public_router mounted=%s via IMPORTS_ENABLED",
            bool(_mounted_public),
        )
    else:
        logger.debug("Imports routers skipped (IMPORTS_ENABLED=0)")

    # Accounting
    include_router_safe(
        r,
        ("app.modules.accounting.interface.http.tenant", "router"),
        prefix="/tenant",
    )

    # RRHH (Human Resources) - TODO: Create module
    # include_router_safe(r, ("app.modules.rrhh.interface.http.tenant", "router"), prefix="/tenant")

    # Finance
    include_router_safe(
        r, ("app.modules.finance.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Production
    include_router_safe(
        r, ("app.modules.production.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Importador Excel
    if os.getenv("IMPORTS_ENABLED", "0").lower() in ("1", "true"):
        include_router_safe(
            r, ("app.modules.imports.interface.http.tenant", "router"), prefix="/tenant"
        )
    else:
        logger.debug("Importador Excel skipped (IMPORTS_ENABLED=0)")

    include_router_safe(
        r, ("app.modules.printing.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Document conversions
    include_router_safe(
        r, ("app.modules.sales.interface.http.conversions", "router"), prefix="/tenant"
    )
    include_router_safe(
        r, ("app.modules.pos.interface.http.conversions", "router"), prefix="/tenant"
    )

    # CRM
    include_router_safe(r, ("app.modules.crm.presentation.tenant", "router"), prefix="/tenant")

    # Settings (company)
    include_router_safe(
        r,
        ("app.modules.settings.interface.http.tenant", "router"),
        prefix="/company/settings",
    )
    # Settings admin: field-config + ui-plantillas
    include_router_safe(r, ("app.modules.settings.interface.http.tenant", "admin_router"))

    # Dashboard KPIs
    include_router_safe(r, ("app.routers.dashboard_stats", "router"))

    # Tenant roles management
    include_router_safe(r, ("app.routers.tenant.roles", "router"))

    # Migrations management (admin)
    include_router_safe(r, ("app.routers.migrations", "router"))

    # (removed) Tenant onboarding/configuración inicial router (legacy)

    # Admin usuarios (router histórico): mantener mientras exista el panel actual
    include_router_safe(
        r, ("app.modules.users.interface.http.admin_users", "router"), prefix="/admin/users"
    )

    # Roles base: CRUD for roles and global permissions
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.roles", "router"),
        fallback=("app.routers.roles", "router"),
    )

    # Legacy endpoints: removed (modern routers in use)

    # Legacy routers retirados: no intentar montarlos para evitar ruido en logs

    # Business Categories (Tipos de negocio) - dinámico desde BD
    include_router_safe(r, ("app.routers.business_categories", "router"))

    # Tenant Settings (Configuración consolidada por tenant)
    include_router_safe(r, ("app.routers.company_settings", "router"))
    include_router_safe(r, ("app.routers.company_settings", "router_admin"))

    # Sectors (Plantillas de negocio) - Units, Config, etc.
    include_router_safe(r, ("app.routers.sectors", "router"))

    # Admin: Sector Config Editor (FASE 6)
    include_router_safe(r, ("app.routers.admin_sector_config", "router"))

    # E-invoicing (SRI/SII)
    include_router_safe(
        r, ("app.modules.einvoicing.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Templates & Overlays
    include_router_safe(
        r, ("app.modules.templates.interface.http.tenant", "router"), prefix="/tenant"
    )
    include_router_safe(
        r, ("app.modules.templates.interface.http.admin", "router"), prefix="/admin"
    )

    # Copilot (tenant-first)
    include_router_safe(
        r, ("app.modules.copilot.interface.http.tenant", "router"), prefix="/tenant"
    )

    # POS / Caja
    include_router_safe(r, ("app.modules.pos.interface.http.tenant", "router"), prefix="/tenant")

    # Reconciliation (Payments AR/AP)
    include_router_safe(
        r,
        ("app.modules.reconciliation.interface.http.tenant", "router"),
        prefix="/tenant",
    )

    # Export CSV
    include_router_safe(r, ("app.modules.export.interface.http.tenant", "router"), prefix="/tenant")

    # Webhooks per tenant
    include_router_safe(
        r, ("app.modules.webhooks.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Notifications
    include_router_safe(
        r, ("app.modules.notifications.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Final safeguard: ensure imports router is mounted in non-production envs
    try:
        env = os.getenv("ENV", "development").lower()

        def _has_import_batches(routes) -> bool:
            markers = {
                "/imports/batches",
                "/api/v1/imports/batches",
                "/tenant/imports/batches",
            }
            for rt in routes:
                path = (getattr(rt, "path", "") or "").rstrip("/")
                if path in markers:
                    return True
            return False

        has_imports = _has_import_batches(r.routes)
        if env != "production" and not has_imports:
            # Try multiple paths to be resilient across entrypoints
            mounted = include_router_safe(
                r,
                ("app.modules.imports.interface.http.tenant", "router"),
                prefix="/tenant",
                fallback=(
                    "apps.backend.app.modules.imports.interface.http.tenant",
                    "router",
                ),
            ) or include_router_safe(
                r,
                ("backend.app.modules.imports.interface.http.tenant", "router"),
                prefix="/tenant",
            )
            if mounted:
                include_router_safe(
                    r,
                    ("app.modules.imports.interface.http.tenant", "public_router"),
                    fallback=(
                        "apps.backend.app.modules.imports.interface.http.tenant",
                        "public_router",
                    ),
                ) or include_router_safe(
                    r,
                    (
                        "backend.app.modules.imports.interface.http.tenant",
                        "public_router",
                    ),
                )
    except Exception:
        pass

    return r
