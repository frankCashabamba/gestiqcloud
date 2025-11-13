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
    pass

from .config.settings import settings
from .core.sessions import SessionMiddlewareServerSide
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.request_log import RequestLogMiddleware
from .middleware.security_headers import security_headers_middleware
from .platform.http.router import build_api_router
from .telemetry.otel import init_fastapi

app = FastAPI(
    title="GestiqCloud API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
)
init_fastapi(app)

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


@app.on_event("startup")
async def _bootstrap_docs_assets() -> None:
    try:
        await _ensure_docs_assets()
    except Exception as exc:
        logging.getLogger("app.docs").warning("Could not prepare Swagger/ReDoc assets: %s", exc)


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


# CORS
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
    logging.getLogger("app.cors").info(
        "CORS configured: allow_origins=%s allow_origin_regex=%s",
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
            limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MIN", "120") or 120),
        )
except Exception:
    pass

# Endpoint-specific rate limiting (críticos: login, password reset, etc.)
try:
    from app.middleware.endpoint_rate_limit import EndpointRateLimiter

    app.add_middleware(
        EndpointRateLimiter,
        limits={
            "/api/v1/tenant/auth/login": (10, 60),  # 10 intentos/min por IP
            "/api/v1/admin/auth/login": (10, 60),
            "/api/v1/auth/login": (10, 60),
            "/api/v1/tenant/auth/password-reset": (5, 300),  # 5 req/5min
            "/api/v1/tenant/auth/password-reset-confirm": (5, 300),
            "/api/v1/admin/usuarios": (30, 60),
            "/api/v1/admin/empresas": (20, 60),
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
# - Suppliers → app/modules/proveedores/interface/http/tenant.py
# - Purchases → app/modules/compras/interface/http/tenant.py
# - Expenses → app/modules/gastos/interface/http/tenant.py
#
# Si necesitas restaurar alguno, ver git history antes de 2025-11-06
# ============================================================================

# Sector Templates (Plantillas de Sector) - MANTENER (único no migrado)
try:
    from app.routers.sector_plantillas import router as sector_plantillas_router

    app.include_router(sector_plantillas_router)  # Ya tiene prefix="/api/v1/sectores"
    _router_logger.info("Sector Templates router mounted at /api/v1/sectores")
except Exception as e:
    _router_logger.error(f"Error mounting Sector Templates router: {e}")

# Tenant Configuration (Configuración del Tenant)
try:
    from app.routers.tenant_config import router as tenant_config_router

    app.include_router(tenant_config_router)  # Ya tiene prefix="/api/v1/settings"
    _router_logger.info("Tenant Config router mounted at /api/v1/settings")
except Exception as e:
    _router_logger.error(f"Error mounting Tenant Config router: {e}")

# Admin field configuration (nuevos endpoints de settings)
try:
    from app.modules.settings.interface.http.tenant import admin_router as _admin_field_router

    app.include_router(_admin_field_router, prefix="/api/v1")
except Exception:
    # Silenciar si el módulo aún no está disponible en entornos parciales
    pass

# Tenant field config (lectura pública por tenant)
try:
    from app.modules.settings.interface.http.tenant import router as _tenant_settings_router

    app.include_router(_tenant_settings_router, prefix="/api/v1/tenant/settings")
except Exception:
    pass

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
    from app.routers.tenant_settings_public import router as tenant_settings_public_router

    app.include_router(tenant_settings_public_router, prefix="/api/v1")
    _router_logger.info("Tenant Settings (public) mounted at /api/v1/settings/tenant")
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
_IMPORTS_PRIVATE_MARKERS = (
    "/api/v1/imports/excel",
    "/api/v1/imports/procesar",
    "/api/v1/imports/documento",
    "/api/v1/imports/uploads",
)
try:
    has_imports = any(
        getattr(r, "path", "").startswith(marker)
        for r in app.router.routes
        for marker in _IMPORTS_PRIVATE_MARKERS
    )
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

# Ensure admin routes
try:
    from backend.app.api.v1.admin import auth as _admin_auth

    app.include_router(_admin_auth.router, prefix="/api/v1/admin")
except Exception:
    pass
try:
    from backend.app.routers.admin import ops as _admin_ops

    app.include_router(_admin_ops.router, prefix="/api/v1/admin")
except Exception:
    pass
try:
    from app.routers.admin_scripts import router as _admin_scripts_router

    app.include_router(_admin_scripts_router, prefix="")
except Exception:
    pass
try:
    from app.api.v1 import auth as _generic_auth

    app.include_router(_generic_auth.router, prefix="/api/v1")
except Exception:
    pass
try:
    from app.api.v1.tenant import auth as _tenant_auth

    app.include_router(_tenant_auth.router, prefix="/api/v1/tenant")
except Exception:
    pass


# Imports runner gating and lifespan
_imports_job_runner = None
from sqlalchemy import inspect  # type: ignore # noqa: E402

try:
    from app.config.database import engine  # type: ignore
except Exception:
    try:
        from apps.backend.app.config.database import engine  # type: ignore
    except Exception:
        engine = None  # type: ignore

_REQUIRED_IMPORTS_TABLES = [
    "import_batches",
    "import_items",
    "import_mappings",
    "import_item_corrections",
    "import_lineage",
    "auditoria_importacion",
    "import_ocr_jobs",
]


def _imports_enabled() -> bool:
    return str(os.getenv("IMPORTS_ENABLED", "0")).lower() in ("1", "true")


def _imports_tables_ready() -> bool:
    if engine is None:
        return False
    try:
        insp = inspect(engine)
        return all(insp.has_table(t) for t in _REQUIRED_IMPORTS_TABLES)
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_after_bind = False
    runner_to_start = None
    global _imports_job_runner
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
    # startup done
    yield
    # post-start
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
    # shutdown
    if _imports_job_runner:
        try:
            _imports_job_runner.stop()
        except Exception:
            pass


@app.head("/", include_in_schema=False)
def root_head():
    return Response(status_code=200)


# Attach lifespan
app.router.lifespan_context = lifespan
