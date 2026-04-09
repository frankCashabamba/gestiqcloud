import asyncio
import importlib
import json
import logging
import os
import sys
import traceback
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
from .services.ai.startup import initialize_ai_providers

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


def _configure_logging() -> None:
    """Configure logging with rotation to prevent unbounded log file growth."""
    from logging.handlers import RotatingFileHandler

    log_file = os.getenv("LOG_FILE", "backend.log")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB default
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Add rotating file handler if not already present
    log_path = None
    if log_file:
        log_path = Path(log_file).expanduser()
        if not log_path.is_absolute():
            log_path = Path(__file__).resolve().parents[1] / log_path

    has_rotating = any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers)
    if not has_rotating and log_path:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        except OSError as exc:
            has_plain_stream = any(type(h) is logging.StreamHandler for h in root_logger.handlers)
            if not has_plain_stream:
                fallback_handler = logging.StreamHandler()
                fallback_handler.setFormatter(formatter)
                root_logger.addHandler(fallback_handler)
            logging.getLogger("app.startup").warning(
                "File logging disabled for %s: %s",
                log_path,
                exc,
            )
        else:
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

    # Suppress verbose uvicorn access logs (200 OK for every request)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _imports_job_runner

    # Configure logging with rotation
    _configure_logging()

    # 🔒 Validar configuración crítica PRIMERO
    try:
        validate_critical_config()
    except ConfigValidationError as e:
        logging.getLogger("app.startup").critical(f"Configuration validation failed: {e}")
        raise

    # Initialize error tracking
    init_sentry()

    # Initialize AI providers early to expose real connection status.
    try:
        await initialize_ai_providers()
    except Exception:
        logging.getLogger("app.startup").warning(
            "AI providers initialization failed; continuing startup",
            exc_info=True,
        )

    try:
        from app.config.database import SessionLocal
        from app.services.product_raw_materials import (
            backfill_bakery_raw_material_products,
            ensure_products_raw_material_column,
        )

        with SessionLocal() as db:
            ensure_products_raw_material_column(db)
            backfill_bakery_raw_material_products(db)
    except Exception:
        logging.getLogger("app.startup").warning(
            "Raw-material product bootstrap failed; continuing startup",
            exc_info=True,
        )

    # Evitar que la descarga de assets bloquee el bind del puerto en plataformas con timeouts estrictos
    skip_docs_assets = str(os.getenv("DOCS_ASSETS_SKIP", "0")).lower() in ("1", "true", "yes")
    try:
        if not skip_docs_assets:
            if settings.ENV == "production":
                # No bloquear startup; se espera que el contenedor ya tenga los assets copiados
                asyncio.create_task(_ensure_docs_assets())
            else:
                # En dev permitimos esperar pero con límite corto
                await asyncio.wait_for(_ensure_docs_assets(), timeout=8)
    except Exception as exc:
        logging.getLogger("app.docs").warning("Could not prepare Swagger/ReDoc assets: %s", exc)

    # OLD imports runner disabled (module renamed to _old_imports)
    logging.getLogger("app.startup").info("Imports runner skipped (old module disabled)")

    yield

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

_error_logger = logging.getLogger("app.errors")


from fastapi.encoders import jsonable_encoder  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402


def _extract_incident_context(request: Request) -> tuple[str | None, str | None]:
    tenant_id = None
    user_id = None

    try:
        claims = getattr(request.state, "access_claims", None) or {}
        if isinstance(claims, dict):
            tenant_id = claims.get("tenant_id")
            user_id = claims.get("user_id")
    except Exception:
        pass

    try:
        session = getattr(request.state, "session", None) or {}
        if tenant_id is None and isinstance(session, dict):
            tenant_id = session.get("tenant_id")
        if user_id is None and isinstance(session, dict):
            user_id = session.get("tenant_user_id") or session.get("user_id")
    except Exception:
        pass

    return (
        str(tenant_id) if tenant_id else None,
        str(user_id) if user_id else None,
    )


def _record_auto_incident(request: Request, exc: Exception) -> None:
    tenant_id, user_id = _extract_incident_context(request)
    if not tenant_id:
        return

    try:
        from app.config.database import SessionLocal
        from app.models.ai.incident import Incident
    except Exception:
        _error_logger.warning("Auto-incident imports unavailable", exc_info=True)
        return

    request_id = getattr(getattr(request, "state", object()), "request_id", None)
    stack_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    title = f"500 Internal Error | {request.method} {request.url.path}"[:255]
    description = f"{type(exc).__name__}: {exc}"
    context = {
        "req_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "query": request.url.query or None,
        "user_id": user_id,
        "ip": request.client.host if request.client else None,
        "exception_type": type(exc).__name__,
    }

    try:
        with SessionLocal() as db:
            db.add(
                Incident(
                    tenant_id=tenant_id,
                    type="error",
                    severity="high",
                    title=title,
                    description=description,
                    stack_trace=stack_trace,
                    context=context,
                    auto_detected=True,
                )
            )
            db.commit()
    except Exception:
        _error_logger.warning("Auto-incident persistence failed", exc_info=True)


@app.exception_handler(RequestValidationError)
async def validation_exception_log(request: Request, exc: RequestValidationError):
    detail = jsonable_encoder(
        exc.errors(),
        custom_encoder={
            ValueError: str,
            Exception: str,
        },
    )
    _error_logger.warning(
        "422 Validation Error | %s %s | %s",
        request.method,
        request.url.path,
        detail,
    )
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unhandled_exception_log(request: Request, exc: Exception):
    _error_logger.error(
        "500 Internal Error | %s %s | %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    _record_auto_incident(request, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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

# Preparar config de CORS (el add_middleware está al final del bloque, DESPUÉS de todos los demás)
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

raw_headers = getattr(
    settings,
    "CORS_ALLOW_HEADERS",
    [
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-CSRFToken",
        "X-CSRF",
        "X-Client-Version",
        "X-Client-Revision",
    ],
)
if isinstance(raw_headers, str):
    s = raw_headers.strip()
    parsed = None
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
        except Exception:
            parsed = None
    if isinstance(parsed, list):
        allow_headers = [str(h).strip() for h in parsed if str(h).strip()]
    else:
        allow_headers = [h.strip() for h in s.split(",") if h.strip()]
else:
    allow_headers = [str(h).strip() for h in raw_headers if str(h).strip()]

_must_allow_headers = ["X-Confirm-Delete-Tenant", "X-Offline-Managed", "X-Tenant-Slug"]
for h in _must_allow_headers:
    if h.lower() not in {x.lower() for x in allow_headers}:
        allow_headers.append(h)
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

# CORS debe ser el último add_middleware (= más exterior) para que su header
# aparezca en TODAS las respuestas, incluidas las de EndpointRateLimiter (429)
# y security_headers_middleware. En Starlette, el último add_middleware es el
# middleware más exterior en el stack.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=getattr(settings, "CORS_ALLOW_ORIGIN_REGEX", None),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
    max_age=86400,
)


# App version — public, no auth required
@app.get("/api/version", include_in_schema=False)
def api_version():
    from app.config.database import SessionLocal
    from app.services.system_defaults_service import get_system_default_text

    with SessionLocal() as db:
        version = get_system_default_text(db, "app.version", settings.APP_VERSION)
    return {"version": version}


# Health and readiness
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["health"], include_in_schema=False)
def ready():
    """Deep healthcheck: verifies DB, Redis, Celery, and migrations."""
    import json as _json

    checks: dict[str, bool] = {}

    # Check database
    try:
        from app.config.database import ping as db_ping

        checks["database"] = bool(db_ping())
    except Exception as e:
        logging.getLogger("app.health").warning(f"DB health check failed: {e}")
        checks["database"] = False

    # Check Redis
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
        checks["redis"] = True  # Not required

    # Check Celery broker connectivity
    celery_url = os.getenv("CELERY_BROKER_URL") or settings.REDIS_URL
    if celery_url:
        try:
            import redis

            r = redis.from_url(celery_url, socket_connect_timeout=2)
            r.ping()
            checks["celery_broker"] = True
        except Exception as e:
            logging.getLogger("app.health").warning(f"Celery broker check failed: {e}")
            checks["celery_broker"] = False
    else:
        checks["celery_broker"] = True  # Not configured

    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503
    body = _json.dumps({"status": "ok" if all_ok else "fail", "checks": checks})
    return Response(
        content=body.encode(),
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
_uploads_dir = settings.uploads_path
if settings.UPLOADS_MOUNT_ENABLED:
    _uploads_dir.mkdir(parents=True, exist_ok=True)
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
# - Products → app/modules/products/interface/http/tenant.py
# - Payments → app/modules/reconciliation/interface/http/tenant.py (pendiente)
# - E-invoicing → app/modules/einvoicing/interface/http/tenant.py
# - Finance → app/modules/finance/interface/http/tenant.py
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
    from app.routers.sector_templates import router as sector_templates_router

    app.include_router(sector_templates_router)  # Prefix="/api/v1/sectores"
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

# Dashboard Stats - PENDIENTE DE MIGRACIÓN A MÓDULO MODERNO

# Admin Stats
try:
    from app.routers.admin_stats import router as admin_stats_router

    app.include_router(admin_stats_router, prefix="")
    _router_logger.info("Admin Stats router mounted at /api/v1/admin/stats")
except Exception as e:
    _router_logger.error(f"Error mounting Admin Stats router: {e}")

# Admin Field Config (imports/templates catalog)
try:
    from app.modules.settings.interface.http.tenant import admin_router as field_admin_router

    app.include_router(field_admin_router, prefix="/api/v1")
    _router_logger.info("Field-config admin router mounted at /api/v1/admin/field-config")
except Exception as e:
    _router_logger.error(f"Error mounting Field-config admin router: {e}")

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
    from app.modules.support.interface.http.incidents import router as incidents_router

    app.include_router(incidents_router, prefix="/api/v1/admin")
    _router_logger.info("Incidents router mounted at /api/v1/admin/incidents")
except Exception as e:
    _router_logger.error(f"Error mounting Incidents router: {e}")

# Admin Logs (NotificationLog → /api/v1/admin/logs)
try:
    from app.routers.admin_logs import router as admin_logs_router

    app.include_router(admin_logs_router, prefix="/api/v1/admin")
    _router_logger.info("Admin Logs router mounted at /api/v1/admin/logs")
except Exception as e:
    _router_logger.error(f"Error mounting Admin Logs router: {e}")

# Notifications
try:
    from app.modules.notifications.interface.http.tenant import router as notifications_router

    app.include_router(notifications_router, prefix="/api/v1")
    _router_logger.info("Notifications router mounted at /api/v1/notifications")
except Exception as e:
    _router_logger.error(f"Error mounting Notifications router: {e}")

# Feature Flags
try:
    from app.modules.feature_flags.interface.http.tenant import router as feature_flags_router

    app.include_router(feature_flags_router, prefix="/api/v1")
    _router_logger.info("Feature Flags router mounted at /api/v1/feature-flags")
except Exception as e:
    _router_logger.warning(f"Feature Flags router mount failed: {e}")

# HR payroll
try:
    from app.modules.hr.interface.http.tenant import router as hr_router

    app.include_router(hr_router, prefix="/api/v1")
    _router_logger.info("HR router mounted at /api/v1/hr")
except Exception as e:
    _router_logger.warning(f"HR router mount failed: {e}")

# Profit Reports
try:
    from app.modules.reports.interface.http.profit import router as profit_router

    app.include_router(profit_router, prefix="/api/v1")
    _router_logger.info("Profit Reports router mounted at /api/v1/reports")
except Exception as e:
    _router_logger.warning(f"Profit Reports router mount failed: {e}")

# E-invoicing - Montado por platform/http/router.py (ver línea ~360)


# -----------------------------------------------------------
# Módulo Importador Contable Universal v1.3
# -----------------------------------------------------------
try:
    from app.modules.importador.router import router as importador_router

    app.include_router(importador_router, prefix="/api/v1")
    _router_logger.info("Importador router mounted at /api/v1/importador")
except Exception as e:
    _router_logger.warning(f"Importador router mount failed: {e}")

try:
    from app.modules.importador.admin_router import router as importador_admin_router

    app.include_router(importador_admin_router, prefix="/api/v1")
    _router_logger.info("Importador admin routing router mounted at /api/v1/admin/importador")
except Exception as e:
    _router_logger.warning(f"Importador admin routing router mount failed: {e}")

try:
    from app.modules.importador.recipes_router import router as importador_recipes_router

    app.include_router(importador_recipes_router, prefix="/api/v1")
    _router_logger.info("Importador recipes router mounted at /api/v1/importador")
except Exception as e:
    _router_logger.warning(f"Importador recipes router mount failed: {e}")

# Document Storage
try:
    from app.modules.documents.interface.http.document_storage import router as doc_storage_router

    app.include_router(doc_storage_router, prefix="/api/v1")
    _router_logger.info("Document Storage router mounted at /api/v1/documents/storage")
except Exception as e:
    _router_logger.warning(f"Document Storage router mount failed: {e}")

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("UVICORN_LOG_LEVEL", "info").lower()
    uvicorn.run("app.main:app", host=host, port=port, log_level=log_level)
