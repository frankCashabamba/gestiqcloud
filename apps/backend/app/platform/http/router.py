from __future__ import annotations

import logging
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
    from app.config.settings import settings

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
    # Generic auth alias (/api/v1/auth/*) + telemetry
    include_router_safe(r, ("app.api.v1.auth", "router"))
    include_router_safe(r, ("app.api.v1.telemetry", "router"))
    # Prometheus metrics
    include_router_safe(r, ("app.api.v1.metrics", "router"))
    # AI providers health
    include_router_safe(r, ("app.routers.ai_health", "router"))
    include_router_safe(r, ("app.api.v1.einvoicing", "router"))
    # Email health
    include_router_safe(r, ("app.api.v1.email_health", "router"))
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.sessions", "router"),
        prefix="/tenant",
    )

    # MFA (TOTP + recovery codes)
    include_router_safe(
        r,
        ("app.modules.identity.interface.http.mfa", "router"),
        prefix="/tenant",
    )

    # Products - mount under /tenant like clientes
    include_router_safe(r, ("app.modules.products.interface.http.public", "router"))
    include_router_safe(
        r, ("app.modules.products.interface.http.tenant", "router"), prefix="/tenant"
    )
    # Product Variants
    include_router_safe(r, ("app.modules.products.variants.router", "router"), prefix="/tenant")
    # Empresas
    _mount_empresas(r)
    include_router_safe(r, ("app.modules.billing.interface.http.admin", "router"), prefix="/admin")
    include_router_safe(
        r, ("app.modules.billing.interface.http.admin", "catalog_router"), prefix="/admin"
    )
    # Onboarding initialization
    include_router_safe(r, ("app.modules.onboarding.interface.http.tenant", "router"))
    # Tenant subscription billing
    include_router_safe(
        r, ("app.modules.billing.interface.http.tenant", "router"), prefix="/tenant"
    )
    include_router_safe(
        r, ("app.modules.billing.interface.http.tenant", "webhook_router"), prefix="/tenant"
    )
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

    # Admin config (modern)
    include_router_safe(
        r, ("app.modules.admin_config.interface.http.admin", "router"), prefix="/admin"
    )
    include_router_safe(
        r, ("app.modules.admin_config.interface.http.payroll_params", "router"), prefix="/admin"
    )
    include_router_safe(
        r, ("app.modules.admin_config.interface.http.system_defaults", "router"), prefix="/admin"
    )
    # Tenant-facing global catalogs (read-only)
    include_router_safe(
        r, ("app.modules.admin_config.interface.http.tenant_catalogs", "router"), prefix="/tenant"
    )

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
    # Stock Transfers (inventario)
    include_router_safe(
        r, ("app.modules.inventory.interface.http.transfers", "router"), prefix="/tenant"
    )
    # Sales
    include_router_safe(r, ("app.modules.sales.interface.http.tenant", "router"), prefix="/tenant")
    # Promotions
    include_router_safe(
        r, ("app.modules.sales.interface.http.promotions", "router"), prefix="/tenant"
    )
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
        ("app.modules.documents.interface.http.tenant", "documents_router"),
        prefix="/tenant",
    )
    # Documents Storage (list, detail, upload)
    include_router_safe(
        r,
        ("app.modules.documents.interface.http.document_storage", "router"),
        prefix="/tenant",
    )
    # Quotes (presupuestos)
    include_router_safe(
        r,
        ("app.modules.documents.interface.http.quotes", "router"),
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

    # Accounting
    include_router_safe(
        r,
        ("app.modules.accounting.interface.http.tenant", "router"),
        prefix="/tenant",
    )

    # RRHH (Human Resources)
    include_router_safe(r, ("app.modules.hr.interface.http.tenant", "router"), prefix="/tenant")

    # Finance
    include_router_safe(
        r, ("app.modules.finance.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Production
    include_router_safe(
        r, ("app.modules.production.interface.http.tenant", "router"), prefix="/tenant"
    )

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

    # HR lookups
    include_router_safe(r, ("app.modules.hr.routes.lookups", "router"))

    # Settings (company)
    include_router_safe(
        r,
        ("app.modules.settings.interface.http.tenant", "router"),
        prefix="/company/settings",
    )
    # Settings admin (field-config + ui-plantillas): se monta en register_all_routers
    # directamente sobre `app` con prefix="/api/v1". Montarlo aquí (build_api_router ya
    # añade /api/v1) producía el doble-prefijo /api/v1/api/v1/admin/field-config.

    # Dashboard KPIs (analytics) — canonical mount under /tenant
    include_router_safe(
        r, ("app.modules.analytics.interface.http.tenant", "router"), prefix="/tenant"
    )

    # El alias legacy /api/v1/dashboard/kpis se retiró (2026-06-10): el canónico es
    # /api/v1/tenant/dashboard/kpis (montado arriba) y el frontend ya lo usa.

    # Tenant roles management
    include_router_safe(r, ("app.modules.identity.interface.http.tenant_roles", "router"))

    # Migrations management (admin)
    include_router_safe(r, ("app.modules.admin_config.interface.http.migrations", "router"))
    include_router_safe(r, ("app.routers.admin.ops", "router"), prefix="/admin")

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

    # Business Categories, Sectors y Sector Config Editor: estos routers ya incluyen
    # /api/v1 en su prefix interno, por lo que se montan en register_all_routers
    # directamente sobre `app` (montarlos aquí duplicaba el prefijo → /api/v1/api/v1/...).

    # Tenant Settings (Configuración consolidada por tenant)
    include_router_safe(r, ("app.routers.company_settings", "router"))
    include_router_safe(r, ("app.routers.company_settings", "router_admin"))

    # E-invoicing (SRI/SII)
    include_router_safe(
        r, ("app.modules.einvoicing.interface.http.tenant", "router"), prefix="/tenant"
    )
    include_router_safe(
        r, ("app.modules.einvoicing.interface.http.admin", "router"), prefix="/admin"
    )

    # Templates & Overlays
    include_router_safe(
        r, ("app.modules.templates.interface.http.tenant", "router"), prefix="/tenant"
    )
    include_router_safe(
        r, ("app.modules.templates.interface.http.admin", "router"), prefix="/admin"
    )

    # RimayPilot (tenant-first)
    include_router_safe(
        r, ("app.modules.copilot.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Feature Flags
    include_router_safe(
        r, ("app.modules.feature_flags.interface.http.admin", "router"), prefix="/admin"
    )

    # Branches (Sucursales)
    include_router_safe(
        r, ("app.modules.branches.interface.http.tenant", "router"), prefix="/tenant"
    )

    # POS / Caja
    include_router_safe(r, ("app.modules.pos.interface.http.tenant", "router"), prefix="/tenant")

    # Restaurant (mesas, comandas, items)
    include_router_safe(
        r,
        ("app.modules.restaurant.interface.http.tenant", "router"),
        prefix="/tenant",
    )

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

    # Reports
    include_router_safe(
        r, ("app.modules.reports.interface.http.tenant", "router"), prefix="/tenant"
    )

    # Reports - Profit analysis
    include_router_safe(
        r, ("app.modules.reports.interface.http.profit", "router"), prefix="/tenant"
    )

    # Telegram Bot Webhook (recepción de comandos entrantes)
    include_router_safe(r, ("app.modules.telegram_bot.interface.http.webhook", "router"))

    # Historical (import & query historical data)
    include_router_safe(
        r, ("app.modules.historical.interface.http.tenant", "router"), prefix="/tenant"
    )

    return r


def register_all_routers(app) -> None:
    """ÚNICA fuente de verdad para el montaje de routers de la aplicación.

    `main.py` NO debe montar routers de módulo directamente: todo se registra aquí.
    El test de invariante `app/tests/security/test_router_mounting.py` verifica que
    `main.py` solo llama a esta función y que no existen rutas duplicadas.

    Los routers transversales/legacy conservan su prefijo absoluto histórico para no
    cambiar las URLs públicas (no rompe el frontend). Lo que se garantiza es que el
    montaje vive en un solo sitio.
    """
    # Router de API moderno (módulos en app/modules/*) bajo /api/v1.
    app.include_router(build_api_router(), prefix="/api/v1")

    # UI Configuration router (Sistema Sin Hardcodes)
    try:
        from app.modules.ui_config.interface.http.admin import router as ui_config_router

        app.include_router(ui_config_router, prefix="/api/v1/admin")
        logger.info("UI Configuration router mounted at /api/v1/admin")
    except Exception as e:
        logger.error(f"Error mounting UI Configuration router: {e}")

    # Sector Templates (Plantillas de Sector)
    try:
        from app.routers.sector_templates import router as sector_templates_router

        app.include_router(sector_templates_router)  # Prefix="/api/v1/sectores"
        logger.info("Sector Templates router mounted")
    except Exception as e:
        logger.error(f"Error mounting Sector Templates router: {e}")

    # Sectors (FASE 1 - Consolidación)
    try:
        from app.routers.sectors import router as sectors_router

        app.include_router(sectors_router)  # Prefix="/api/v1/sectors"
        logger.info("Sectors router mounted")
    except Exception as e:
        logger.error(f"Error mounting Sectors router: {e}")

    # Business Categories (Tipos de negocio) — el router ya incluye /api/v1 en su prefix.
    try:
        from app.routers.business_categories import router as business_categories_router

        app.include_router(business_categories_router)  # Prefix="/api/v1/business-categories"
        logger.info("Business Categories router mounted at /api/v1/business-categories")
    except Exception as e:
        logger.error(f"Error mounting Business Categories router: {e}")

    # Admin: Sector Config Editor (FASE 6) — el router ya incluye /api/v1 en su prefix.
    try:
        from app.routers.admin_sector_config import router as admin_sector_config_router

        app.include_router(admin_sector_config_router)  # Prefix="/api/v1/admin"
        logger.info("Admin Sector Config router mounted at /api/v1/admin/sectors")
    except Exception as e:
        logger.error(f"Error mounting Admin Sector Config router: {e}")

    # Admin Stats
    try:
        from app.routers.admin_stats import router as admin_stats_router

        app.include_router(admin_stats_router, prefix="")
        logger.info("Admin Stats router mounted at /api/v1/admin/stats")
    except Exception as e:
        logger.error(f"Error mounting Admin Stats router: {e}")

    # Admin Field Config (imports/templates catalog)
    try:
        from app.modules.settings.interface.http.tenant import admin_router as field_admin_router

        app.include_router(field_admin_router, prefix="/api/v1")
        logger.info("Field-config admin router mounted at /api/v1/admin/field-config")
    except Exception as e:
        logger.error(f"Error mounting Field-config admin router: {e}")

    # Settings
    try:
        from app.routers.settings_router import router as settings_router

        app.include_router(settings_router, prefix="/api/v1")
        logger.info("Settings router mounted at /api/v1/settings")
    except Exception as e:
        logger.error(f"Error mounting Settings router: {e}")

    # Public Tenant Settings (unified)
    try:
        from app.routers.company_settings_public import router as company_settings_public_router

        app.include_router(company_settings_public_router, prefix="/api/v1")
        logger.info("Company Settings (public) mounted at /api/v1/company/settings/config")
    except Exception as e:
        logger.error(f"Error mounting Tenant Settings public router: {e}")

    # Incidents + IA
    try:
        from app.modules.support.interface.http.incidents import router as incidents_router

        app.include_router(incidents_router, prefix="/api/v1/admin")
        logger.info("Incidents router mounted at /api/v1/admin/incidents")
    except Exception as e:
        logger.error(f"Error mounting Incidents router: {e}")

    # Admin Logs (NotificationLog → /api/v1/admin/logs)
    try:
        from app.routers.admin_logs import router as admin_logs_router

        app.include_router(admin_logs_router, prefix="/api/v1/admin")
        logger.info("Admin Logs router mounted at /api/v1/admin/logs")
    except Exception as e:
        logger.error(f"Error mounting Admin Logs router: {e}")

    # Notifications, HR y Profit: se montan vía build_api_router bajo /api/v1/tenant.
    # Sus montajes legacy duplicados (/api/v1/notifications, /api/v1/hr, /api/v1/reports/profit)
    # y el alias /api/v1/dashboard/kpis se retiraron (2026-06-10).

    # Feature Flags
    try:
        from app.modules.feature_flags.interface.http.tenant import router as feature_flags_router

        app.include_router(feature_flags_router, prefix="/api/v1")
        logger.info("Feature Flags router mounted at /api/v1/feature-flags")
    except Exception as e:
        logger.warning(f"Feature Flags router mount failed: {e}")

    # Importador Contable Universal
    try:
        from app.modules.importador.router import router as importador_router

        app.include_router(importador_router, prefix="/api/v1")
        logger.info("Importador router mounted at /api/v1/importador")
    except Exception as e:
        logger.warning(f"Importador router mount failed: {e}")

    try:
        from app.modules.importador.admin_router import router as importador_admin_router

        app.include_router(importador_admin_router, prefix="/api/v1")
        logger.info("Importador admin routing router mounted at /api/v1/admin/importador")
    except Exception as e:
        logger.warning(f"Importador admin routing router mount failed: {e}")

    try:
        from app.modules.importador.recipes_router import router as importador_recipes_router

        app.include_router(importador_recipes_router, prefix="/api/v1")
        logger.info("Importador recipes router mounted at /api/v1/importador")
    except Exception as e:
        logger.warning(f"Importador recipes router mount failed: {e}")

    # Document Storage
    try:
        from app.modules.documents.interface.http.document_storage import (
            router as doc_storage_router,
        )

        app.include_router(doc_storage_router, prefix="/api/v1")
        logger.info("Document Storage router mounted at /api/v1/documents/storage")
    except Exception as e:
        logger.warning(f"Document Storage router mount failed: {e}")
