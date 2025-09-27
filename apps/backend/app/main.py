from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

import sys
import types
import importlib
try:
    # Establish module aliases so dynamic import strings work in all entrypoints
    # Derive package roots from this module name (e.g., 'apps.backend.app.main')
    _this_pkg = __package__ or "apps.backend.app"
    _app_pkg = importlib.import_module(_this_pkg)                 # apps.backend.app
    _backend_pkg = importlib.import_module(_this_pkg.rsplit('.', 1)[0])  # apps.backend

    # Map 'app' -> apps.backend.app and 'backend' -> apps.backend
    sys.modules.setdefault("app", _app_pkg)
    sys.modules.setdefault("backend", _backend_pkg)
    sys.modules.setdefault("backend.app", _app_pkg)

    # Provide 'apps' alias so 'apps.backend' works as a top-level
    _apps_alias = types.ModuleType("apps")
    _apps_alias.backend = _backend_pkg
    sys.modules.setdefault("apps", _apps_alias)
    sys.modules.setdefault("apps.backend", _backend_pkg)
    sys.modules.setdefault("apps.backend.app", _app_pkg)
except Exception:
    pass

from .platform.http.router import build_api_router
from .config.settings import settings
from .core.sessions import SessionMiddlewareServerSide
from .middleware.security_headers import security_headers_middleware


app = FastAPI(title="GestiqCloud API", version="1.0.0")

# CORS (desde settings, con fallback seguro)
allow_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Sesiones server-side (cookies seguras según entorno)
app.add_middleware(
    SessionMiddlewareServerSide,
    cookie_name=settings.SESSION_COOKIE_NAME,
    secret_key=(settings.SECRET_KEY.get_secret_value() if hasattr(settings.SECRET_KEY, "get_secret_value") else str(settings.SECRET_KEY)),
    https_only=(settings.ENV == "production"),
    cookie_domain=settings.COOKIE_DOMAIN,
)

# Security headers (CSP, HSTS, etc.)
app.middleware("http")(security_headers_middleware)


@app.get("/health", tags=["health"])  # simple healthcheck
def health():
    return {"status": "ok"}

# Archivos subidos (logos, etc.)
# En entornos como CI, la carpeta puede no existir; evitamos fallar al importar app
_uploads_dir = Path(settings.UPLOADS_DIR)
if settings.UPLOADS_MOUNT_ENABLED:
    if _uploads_dir.is_dir():
        app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")
    else:
        logging.getLogger("app.startup").info("Uploads dir no existe; omitiendo mount de /uploads")

# Debug del enrutador central (ver qué routers montan y cuáles fallan)
_router_logger = logging.getLogger("app.router")
if not _router_logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.DEBUG)
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    _router_logger.addHandler(_h)
_router_logger.setLevel(logging.DEBUG)
_router_logger.propagate = False

# Email logger to surface dev-email messages in docker logs
_email_logger = logging.getLogger("app.email")
if not _email_logger.handlers:
    _eh = logging.StreamHandler()
    _eh.setLevel(logging.INFO)
    _eh.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    _email_logger.addHandler(_eh)
_email_logger.setLevel(logging.INFO)
_email_logger.propagate = False

# REST API v1 (compat con FE): monta todos los routers bajo /api/v1
app.include_router(build_api_router(), prefix="/api/v1")

# Fallback: si por algún motivo el router de imports no quedó montado
# (p.ej., en entornos de test donde la detección condicional se ejecutó antes
# de inicializar variables de entorno), lo montamos explícitamente.
try:
    has_imports = any(getattr(r, "path", "").startswith("/api/v1/imports") for r in app.router.routes)
except Exception:
    has_imports = False
if not has_imports:
    mounted = False
    # Try relative import first
    try:
        from .modules.imports.interface.http.tenant import router as _rel_imports_router
        from .modules.imports.interface.http.tenant import public_router as _rel_imports_public
        app.include_router(_rel_imports_router, prefix="/api/v1")
        app.include_router(_rel_imports_public, prefix="/api/v1")
        mounted = True
    except Exception:
        pass
    # Try app.* path
    try:
        from app.modules.imports.interface.http.tenant import router as _imports_router
        from app.modules.imports.interface.http.tenant import public_router as _imports_public
        app.include_router(_imports_router, prefix="/api/v1")
        app.include_router(_imports_public, prefix="/api/v1")
        mounted = True
    except Exception:
        pass
    # Try backend.app.* path as fallback
    if not mounted:
        try:
            from backend.app.modules.imports.interface.http.tenant import router as _imports_router_b
            from backend.app.modules.imports.interface.http.tenant import public_router as _imports_public_b
            app.include_router(_imports_router_b, prefix="/api/v1")
            app.include_router(_imports_public_b, prefix="/api/v1")
        except Exception:
            pass

# Ensure critical admin auth routes are mounted even if dynamic resolver skips
try:
    from backend.app.api.v1.admin import auth as _admin_auth
    app.include_router(_admin_auth.router, prefix="/api/v1/admin")
except Exception:  # keep app boot resilient
    pass



try:
    from app.modules.imports.application.job_runner import job_runner as _imports_job_runner
except Exception:  # pragma: no cover - optional during tests
    _imports_job_runner = None


@app.on_event("startup")
async def _start_imports_job_runner() -> None:  # pragma: no cover - integration hook
    if _imports_job_runner is not None:
        _imports_job_runner.start()


@app.on_event("shutdown")
async def _stop_imports_job_runner() -> None:  # pragma: no cover - integration hook
    if _imports_job_runner is not None:
        _imports_job_runner.stop()
