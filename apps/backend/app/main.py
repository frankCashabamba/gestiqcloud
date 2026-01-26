import asyncio
import importlib
import logging
import os
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles
from app.routers.tenant import roles as tenant_roles_router
from .platform.http.router import build_api_router
from .telemetry.otel import init_fastapi
from .telemetry.sentry import init_sentry

# Set import aliases so both `app.*` and `apps.backend.app.*` imports work
try:
    _this_pkg = __package__ or "apps.backend.app"
    _app_pkg = importlib.import_module(_this_pkg)  # apps.backend.app
    _backend_pkg = importlib.import_module(_this_pkg.rsplit(".", 1)[0])  # apps.backend

    sys.modules.setdefault("app", _app_pkg)
    sys.modules.setdefault("backend", _backend_pkg)
    sys.modules.setdefault("backend.app", _app_pkg)

    _apps_alias = types.ModuleType("apps")
    _apps_alias.backend = _backend_pkg
    sys.modules.setdefault("apps", _apps_alias)
    sys.modules.setdefault("apps.backend", _backend_pkg)
    sys.modules.setdefault("apps.backend.app", _app_pkg)
except Exception:
    logging.getLogger("app.startup").debug(
        "Module aliasing failed (may be intentional)", exc_info=True
    )


from .config.settings import settings
from .core.sessions import SessionMiddlewareServerSide
from .core.startup_validation import ConfigValidationError, validate_critical_config
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_log import RequestLogMiddleware
from .middleware.security_headers import security_headers_middleware

# Rate limiting configuration: increased for development, stricter for production
_RATE_LIMIT_PER_MINUTE = (
    int(os.getenv("RATE_LIMIT_PER_MINUTE", "1000"))
    if os.getenv("ENVIRONMENT", "development").lower() == "development"
    else int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
)

# ============================================================================
# DOCS ASSETS SETUP
# ============================================================================

DOCS_ASSETS_DIR = Path(__file__).parent / "static" / "docs"
DOCS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

_DOCS_ASSET_SOURCES = {
    "swagger-ui-bundle.js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    "swagger-ui.css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    "swagger-favicon.png": "https://fastapi.tiangolo.com/img/favicon.png",
    "redoc.standalone.js": "https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
}


async def _ensure_docs_assets() -> None:
    missing = [name for name in _DOCS_ASSET_SOURCES if not (DOCS_ASSETS_DIR / name).is_file()]
    if not missing:
        return
    loop = asyncio.get_event_loop()

    def _download(url: str) -> bytes:
        with urlrequest.urlopen(url, timeout=30) as resp:
            return resp.read()

    for filename in missing:
        url = _DOCS_ASSET_SOURCES[filename]
        try:
            data = await loop.run_in_executor(None, _download, url)
            (DOCS_ASSETS_DIR / filename).write_bytes(data)
        except urlerror.URLError as exc:
            logging.getLogger("app.docs").warning("Failed downloading %s: %s", url, exc)
            raise


# ============================================================================
# GLOBAL STATE
# ============================================================================

_imports_job_runner = None


def _imports_enabled() -> bool:
    return str(os.getenv("IMPORTS_ENABLED", "0")).lower() in ("1", "true")


def _imports_tables_ready() -> bool:
    if _engine is None:
        return False
    try:
        from sqlalchemy import inspect

        insp = inspect(_engine)
        _REQUIRED_IMPORTS_TABLES = [
            "import_batches",
            "import_items",
            "import_mappings",
            "import_item_corrections",
            "import_lineage",
            "auditoria_importacion",
            "import_ocr_jobs",
        ]
        return all(insp.has_table(t) for t in _REQUIRED_IMPORTS_TABLES)
    except Exception:
        return False


# Lazy load engine
_engine = None
try:
    from app.config.database import engine

    _engine = engine
except Exception:
    try:
        from apps.backend.app.config.database import engine

        _engine = engine
    except Exception:
        logging.getLogger("app.startup").warning("Database engine not available", exc_info=True)


# ============================================================================
# LIFESPAN EVENTS (replaces deprecated on_event)
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_after_bind = False
    runner_to_start = None
    global _imports_job_runner

    # 🔒 Validar configuración crítica PRIMERO
    try:
        validate_critical_config()
    except ConfigValidationError as e:
        logging.getLogger("app.startup").critical(f"Configuration validation failed: {e}")
        raise

    # Initialize error tracking
    init_sentry()

    try:
        await _ensure_docs_assets()
    except Exception as exc:
        logging.getLogger("app.docs").warning("Could not prepare Swagger/ReDoc assets: %s", exc)

    try:
        if _imports_job_runner is None and _imports_enabled() and _imports_tables_ready():
            try:
                from app.modules.imports.application.job_runner import job_runner as _jr

                runner_to_start = _jr
                start_after_bind = True
            except Exception:
                logging.getLogger("app.startup").info(
                    "Imports runner not available (import failed)"
                )
        else:
            logging.getLogger("app.startup").info(
                "Imports runner skipped (disabled or missing tables)"
            )
    except Exception:
        logging.getLogger("app.startup").exception(
            "Failed preparing imports runner; continuing without it"
        )

    yield

    # Post-startup
    if start_after_bind and runner_to_start is not None:
        try:

            def _start_runner():
                try:
                    runner_to_start.start()
                finally:
                    globals()["_imports_job_runner"] = runner_to_start

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, _start_runner)
        except Exception:
            logging.getLogger("app.startup").exception("Failed starting imports runner post-bind")

    # Shutdown
    if _imports_job_runner:
        try:
            _imports_job_runner.stop()
        except Exception:
            logging.getLogger("app.startup").warning(
                "Error stopping imports runner during shutdown", exc_info=True
            )


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="GestiqCloud API",
    version="1.1.0",
    docs_url=None,
    redoc_url=None,
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    lifespan=lifespan,
)

init_fastapi(app)

app.mount("/docs/assets", StaticFiles(directory=str(DOCS_ASSETS_DIR)), name="docs-assets")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> Response:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} – Docs",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/docs/assets/swagger-ui-bundle.js",
        swagger_css_url="/docs/assets/swagger-ui.css",
        swagger_favicon_url="/docs/assets/swagger-favicon.png",
        swagger_ui_parameters={"syntaxHighlight.theme": "idea"},
    )


@app.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect() -> Response:
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def custom_redoc() -> Response:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} – ReDoc",
        redoc_js_url="/docs/assets/redoc.standalone.js",
        redoc_favicon_url="/docs/assets/swagger-favicon.png",
        with_google_fonts=False,
    )


# Rewrite /v1 → /api/v1 so legacy SPA routes continue working while API lives under /api/v1
@app.middleware("http")
async def _rewrite_v1_to_api_v1(request: Request, call_next):
    path = request.scope.get("path", "")
    if path == "/v1" or path.startswith("/v1/"):
        new_path = "/api" + path
        request.scope["path"] = new_path
        raw_path = request.scope.get("raw_path")
        if isinstance(raw_path, (bytes, bytearray)) and raw_path.startswith(b"/v1"):
            request.scope["raw_path"] = b"/api" + raw_path
        elif isinstance(raw_path, str) and raw_path.startswith("/v1"):
            request.scope["raw_path"] = "/api" + raw_path
    response = await call_next(request)
    return response


# UTF-8 middleware
@app.middleware("http")
async def force_utf8_response(request, call_next):
    response = await call_next(request)
    if "application/json" in response.headers.get("content-type", ""):
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


# Sessions
app.add_mmiddleware = app.add_middleware  # optional alias
app.add_middleware(
    SessionMiddlewareServerSide,
    cookie_name=settings.SESSION_COOKIE_NAME,
    secret_key=(
        settings.SECRET_KEY.get_secret_value()
        if hasattr(settings.SECRET_KEY, "get_secret_value")
        else str(settings.SECRET_KEY)
    ),
    https_only=(settings.ENV == "production"),
    cookie_domain=settings.COOKIE_DOMAIN,
)

# Request logging and rate limiting
app.add_middleware(RequestLogMiddleware)

# Global rate limit (todos los endpoints)
try:
    if str(os.getenv("RATE_LIMIT_ENABLED", "1")).lower() in ("1", "true"):
        app.add_middleware(
            RateLimitMiddleware,
            limit_per_minute=_RATE_LIMIT_PER_MINUTE,
        )
except Exception:
    pass

# CORS (mantenerlo al final para que se aplique incluso cuando otros middlewares cortan la respuesta)
allow_origins = (
    settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
)
raw_methods = getattr(
    settings, "CORS_ALLOW_METHODS", ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
if isinstance(raw_methods, str):
    allow_methods = [m.strip().upper() for m in raw_methods.split(",") if m.strip()]
else:
    allow_methods = [str(m).strip().upper() for m in raw_methods]
if "*" not in allow_methods:
    # Browsers require OPTIONS for CORS preflight and HEAD for fetch metadata, so inject them if missing.
    for mandatory in ("OPTIONS", "HEAD"):
        if mandatory not in allow_methods:
            allow_methods.append(mandatory)
try:
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        if not allow_origins:
            logging.getLogger("app.cors").warning(
                "⚠️  CORS_ORIGINS is empty in production. "
                "This may cause frontend requests to be blocked."
            )
        else:
            logging.getLogger("app.cors").info(
                "✅ CORS configured (production): allow_origins=%s allow_origin_regex=%s",
                allow_origins,
                getattr(settings, "CORS_ALLOW_ORIGIN_REGEX", None),
            )
    else:
        logging.getLogger("app.cors").debug(
            "CORS configured (development): allow_origins=%s allow_origin_regex=%s",
            allow_origins,
            getattr(settings, "CORS_ALLOW_ORIGIN_REGEX", None),
        )
except Exception:
    pass
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=getattr(settings, "CORS_ALLOW_ORIGIN_REGEX", None),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=allow_methods,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    max_age=86400,
)

# Endpoint-specific rate limiting (críticos: login, password reset, etc.)
try:
    from app.middleware.endpoint_rate_limit import EndpointRateLimiter

    if str(os.getenv("ENDPOINT_RATE_LIMIT_ENABLED", "1")).lower() in ("1", "true"):
        app.add_middleware(
            EndpointRateLimiter,
            limits={
                "/api/v1/tenant/auth/login": (10, 60),  # 10 intentos/min por IP
                "/api/v1/admin/auth/login": (10, 60),
                "/api/v1/auth/login": (10, 60),
                "/api/v1/tenant/auth/password-reset": (5, 300),  # 5 req/5min
                "/api/v1/tenant/auth/password-reset-confirm": (5, 300),
                "/api/v1/admin/users": (30, 60),
                "/api/v1/admin/companies": (20, 60),
            },
        )
        logging.getLogger("app.startup").info("Endpoint-specific rate limiting enabled")
except Exception as e:
    logging.getLogger("app.startup").warning(f"Could not enable endpoint rate limiting: {e}")
    pass

# Security headers
app.middleware("http")(security_headers_middleware)


# Health and readiness
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["health"], include_in_schema=False)
def ready():
    """Healthcheck profundo: verifica DB y Redis"""
    checks = {"database": False, "redis": False}

    # Check database
    try:
        from app.config.database import ping as db_ping  # type: ignore

        checks["database"] = bool(db_ping())
    except Exception as e:
        logging.getLogger("app.health").warning(f"DB health check failed: {e}")
        checks["database"] = False

    # Check Redis (si está configurado)
    if settings.REDIS_URL:
        try:
            import redis

            r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            r.ping()
            checks["redis"] = True
        except Exception as e:
            logging.getLogger("app.health").warning(f"Redis health check failed: {e}")
            checks["redis"] = False
    else:
        checks["redis"] = True  # No required, mark as OK

    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503
    return Response(
        content=f'{{"status": "{"ok" if all_ok else "fail"}", "checks": {checks}}}'.encode(),
        media_type="application/json",
        status_code=status_code,
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


@app.head("/healthz", include_in_schema=False)
def healthz_head():
    return Response(status_code=200)


@app.head("/health", include_in_schema=False)
def health_head():
    return Response(status_code=200)


@app.head("/ready", include_in_schema=False)
def ready_head():
    return Response(status_code=200)


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "GestiqCloud API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


@app.head("/", include_in_schema=False)
def root_head():
    return Response(status_code=200)


# Static uploads
_uploads_dir = Path(settings.UPLOADS_DIR)
if settings.UPLOADS_MOUNT_ENABLED and _uploads_dir.is_dir():
    app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


# Loggers
_router_logger = logging.getLogger("app.router")
if not _router_logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.DEBUG)
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    _router_logger.addHandler(_h)
_router_logger.setLevel(logging.DEBUG)
_router_logger.propagate = False

_email_logger = logging.getLogger("app.email")
if not _email_logger.handlers:
    _eh = logging.StreamHandler()
    _eh.setLevel(logging.INFO)
    _eh.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    _email_logger.addHandler(_eh)
_email_logger.setLevel(logging.INFO)
_email_logger.propagate = False


# API routers
app.include_router(build_api_router(), prefix="/api/v1")

# UI Configuration router (Sistema Sin Hardcodes)
try:
    from app.modules.ui_config.interface.http.admin import router as ui_config_router

    app.include_router(ui_config_router, prefix="/api/v1/admin")
    _router_logger.info("UI Configuration router mounted at /api/v1/admin")
except Exception as e:
    _router_logger.error(f"Error mounting UI Configuration router: {e}")

# ============================================================================
# LEGACY ROUTERS ELIMINADOS (2025-11-06)
# ============================================================================
# Todos los routers han sido migrados a módulos modernos en app/modules/
# Ver: app/platform/http/router.py para el montaje moderno
#
# Routers eliminados:
# - POS → app/modules/pos/interface/http/tenant.py
# - Products → app/modules/productos/interface/http/tenant.py
# - Payments → app/modules/reconciliation/interface/http/tenant.py (pendiente)
# - E-invoicing → app/modules/einvoicing/interface/http/tenant.py
# - Finance → app/modules/finanzas/interface/http/tenant.py
# - HR → app/modules/rrhh/interface/http/tenant.py
# - Production → app/modules/produccion/interface/http/tenant.py
# - Accounting → app/modules/contabilidad/interface/http/tenant.py
# - Sales → app/modules/ventas/interface/http/tenant.py
# - Suppliers → app/modules/suppliers/interface/http/tenant.py
# - Purchases → app/modules/compras/interface/http/tenant.py
# - Expenses → app/modules/expenses/interface/http/tenant.py
#
# Si necesitas restaurar alguno, ver git history antes de 2025-11-06
# ============================================================================

# Tenant Settings (Configuración centralizada del Tenant)
# Consolidado en CompanySettings - única fuente de verdad para configuración por tenant
_router_logger.info("Company Settings routers mounted via build_api_router()")

# Sector Templates (Plantillas de Sector)
try:
    from app.routers.sector_plantillas import router as sector_plantillas_router

    app.include_router(sector_plantillas_router)  # Prefix="/api/v1/sectores"
    _router_logger.info("Sector Templates router mounted")
except Exception as e:
    _router_logger.error(f"Error mounting Sector Templates router: {e}")

# Sectors (FASE 1 - Consolidación)
try:
    from app.routers.sectors import router as sectors_router

    app.include_router(sectors_router)  # Prefix="/api/v1/sectors"
    _router_logger.info("Sectors router mounted")
except Exception as e:
    _router_logger.error(f"Error mounting Sectors router: {e}")

# ============================================================================
# TODOS LOS MÓDULOS PROFESIONALES YA ESTÁN EN app/modules/
# Ver app/platform/http/router.py:253-315 para montaje automático
# ============================================================================

# Dashboard KPIs
try:
    from app.routers.dashboard_kpis import router as dashboard_kpis_router

    app.include_router(dashboard_kpis_router, prefix="/api/v1")
    _router_logger.info("Dashboard KPIs router mounted at /api/v1/dashboard/kpis")
except Exception as e:
    _router_logger.error(f"Error mounting Dashboard KPIs router: {e}")

# Dashboard Stats - PENDIENTE DE MIGRACIÓN A MÓDULO MODERNO

# Admin Stats
try:
    from app.routers.admin_stats import router as admin_stats_router

    app.include_router(admin_stats_router, prefix="")
    _router_logger.info("Admin Stats router mounted at /api/v1/admin/stats")
except Exception as e:
    _router_logger.error(f"Error mounting Admin Stats router: {e}")

# Settings
try:
    from app.routers.settings_router import router as settings_router

    app.include_router(settings_router, prefix="/api/v1")
    _router_logger.info("Settings router mounted at /api/v1/settings")
except Exception as e:
    _router_logger.error(f"Error mounting Settings router: {e}")

# Public Tenant Settings (unified)
try:
    from app.routers.company_settings_public import router as company_settings_public_router

    app.include_router(company_settings_public_router, prefix="/api/v1")
    _router_logger.info("Company Settings (public) mounted at /api/v1/company/settings/config")
except Exception as e:
    _router_logger.error(f"Error mounting Tenant Settings public router: {e}")

# Incidents + IA
try:
    from app.routers.incidents import router as incidents_router

    app.include_router(incidents_router, prefix="/api/v1")
    _router_logger.info("Incidents router mounted at /api/v1/incidents")
except Exception as e:
    _router_logger.error(f"Error mounting Incidents router: {e}")

# Notifications
try:
    from app.routers.notifications import router as notifications_router

    app.include_router(notifications_router, prefix="/api/v1")
    _router_logger.info("Notifications router mounted at /api/v1/notifications")
except Exception as e:
    _router_logger.error(f"Error mounting Notifications router: {e}")

# E-invoicing - Montado por platform/http/router.py (ver línea ~360)


# ElectricSQL shapes
try:
    from app.modules.electric_shapes import router as electric_router

    app.include_router(electric_router, prefix="/api/v1")
    _router_logger.info("ElectricSQL shapes router mounted at /api/v1/electric")
except Exception as e:
    _router_logger.error(f"Error mounting ElectricSQL router: {e}")
    import traceback

    _router_logger.error(traceback.format_exc())

# Imports router fallback safeguard
_IMPORTS_PRIVATE_MARKERS = ("/api/v1/imports/batches",)
try:

    def _has_imports_with_post(routes):
        markers = {m.rstrip("/") for m in _IMPORTS_PRIVATE_MARKERS}
        for rt in routes:
            path = (getattr(rt, "path", "") or "").rstrip("/")
            methods = getattr(rt, "methods", None) or set()
            if "POST" in methods and path in markers:
                return True
        return False

    has_imports = _has_imports_with_post(app.router.routes)
except Exception:
    has_imports = False
if not has_imports:
    mounted = False
    try:
        from .modules.imports.interface.http.tenant import public_router as _rel_imports_public
        from .modules.imports.interface.http.tenant import router as _rel_imports_router

        app.include_router(_rel_imports_router, prefix="/api/v1")
        app.include_router(_rel_imports_public, prefix="/api/v1")
        mounted = True
    except Exception:
        pass
    try:
        from app.modules.imports.interface.http.preview import router as _preview_router
        from app.modules.imports.interface.http.tenant import public_router as _imports_public
        from app.modules.imports.interface.http.tenant import router as _imports_router

        app.include_router(_imports_router, prefix="/api/v1")
        app.include_router(_imports_public, prefix="/api/v1")
        app.include_router(_preview_router, prefix="/api/v1/imports")
        mounted = True
    except Exception:
        pass
    if not mounted:
        try:
            from backend.app.modules.imports.interface.http.tenant import (
                public_router as _imports_public_b,
            )
            from backend.app.modules.imports.interface.http.tenant import (
                router as _imports_router_b,
            )

            app.include_router(_imports_router_b, prefix="/api/v1")
            app.include_router(_imports_public_b, prefix="/api/v1")
        except Exception:
            pass

# Preview router (standalone)
try:
    from app.modules.imports.interface.http.preview import router as preview_router

    app.include_router(preview_router, prefix="/api/v1/imports")
    print("[INFO] Preview router mounted at /api/v1/imports/preview")
except Exception as e:
    print(f"[DEBUG] Preview router mount failed: {e}")

# IA Classification router (Fase D)
try:
    from app.modules.imports.ai.http_endpoints import router as ai_router

    app.include_router(ai_router, prefix="/api/v1/imports")
    _router_logger.info("IA Classification router mounted at /api/v1/imports/ai")
except Exception as e:
    _router_logger.warning(f"IA Classification router mount failed: {e}")

# Feedback router for classification improvement
try:
    from app.modules.imports.interface.http.feedback import router as feedback_router

    app.include_router(feedback_router, prefix="/api/v2/imports")
    _router_logger.info("Feedback router mounted at /api/v2/imports/feedback")
except Exception as e:
    _router_logger.warning(f"Feedback router mount failed: {e}")

# OCR router for PDF/image text extraction
try:
    from app.modules.imports.interface.http.ocr import router as ocr_router

    app.include_router(ocr_router, prefix="/api/v1/imports")
    _router_logger.info("OCR router mounted at /api/v1/imports/ocr")
except Exception as e:
    _router_logger.warning(f"OCR router mount failed: {e}")

# Ensure admin routes
try:
    from backend.app.api.v1.admin import auth as _admin_auth

    app.include_router(_admin_auth.router, prefix="/api/v1/admin")
except Exception:
    _router_logger.debug("Admin auth router not available", exc_info=True)
try:
    from backend.app.routers.admin import ops as _admin_ops

    app.include_router(_admin_ops.router, prefix="/api/v1/admin")
except Exception:
    _router_logger.debug("Admin ops router not available", exc_info=True)
try:
    from app.routers.admin_scripts import router as _admin_scripts_router

    app.include_router(_admin_scripts_router, prefix="")
except Exception:
    _router_logger.debug("Admin scripts router not available", exc_info=True)
try:
    from app.api.v1 import auth as _generic_auth

    app.include_router(_generic_auth.router, prefix="/api/v1")
except Exception:
    _router_logger.debug("Generic auth router not available", exc_info=True)
try:
    from app.api.v1.tenant import auth as _tenant_auth

    app.include_router(_tenant_auth.router, prefix="/api/v1/tenant")
    app.include_router(tenant_roles_router.router, prefix="/api/v1")
except Exception:
    _router_logger.debug("Tenant auth router not available", exc_info=True)
