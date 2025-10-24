from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import os
import sys
import types
import importlib
from contextlib import asynccontextmanager
import asyncio

# Set import aliases so both `app.*` and `apps.backend.app.*` imports work
try:
    _this_pkg = __package__ or "apps.backend.app"
    _app_pkg = importlib.import_module(_this_pkg)                       # apps.backend.app
    _backend_pkg = importlib.import_module(_this_pkg.rsplit('.', 1)[0]) # apps.backend

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

from .platform.http.router import build_api_router
from .config.settings import settings
from .core.sessions import SessionMiddlewareServerSide
from .middleware.security_headers import security_headers_middleware
from .telemetry.otel import init_fastapi
from .middleware.request_log import RequestLogMiddleware
from .middleware.rate_limit import RateLimitMiddleware


app = FastAPI(title="GestiqCloud API", version="1.0.0")
init_fastapi(app)

# CORS
allow_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
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
    allow_methods=settings.CORS_ALLOW_METHODS,
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
try:
    if str(os.getenv("RATE_LIMIT_ENABLED", "1")).lower() in ("1", "true"):
        app.add_middleware(
            RateLimitMiddleware,
            limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MIN", "120") or 120),
        )
except Exception:
    pass

# Security headers
app.middleware("http")(security_headers_middleware)


# Health and readiness
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["health"], include_in_schema=False)
def ready():
    ok = True
    try:
        from app.config.database import ping as db_ping  # type: ignore

        db_ok = bool(db_ping())
        ok = ok and db_ok
    except Exception:
        ok = False
    if not ok:
        return Response(content=b'{"status":"fail"}', media_type="application/json", status_code=503)
    return {"status": "ok"}


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

# POS
try:
    from app.routers.pos import router as pos_router
    # Mount under /api/v1 to align with FE/tests expectations
    app.include_router(pos_router, prefix="/api/v1")
    _router_logger.info("POS router mounted at /api/v1/pos")
except Exception as e:
    _router_logger.error(f"Error mounting POS router: {e}")

# Payments
try:
    from app.routers.payments import router as payments_router
    app.include_router(payments_router, prefix="/api/v1")
    _router_logger.info("Payments router mounted at /api/v1/payments")
except Exception as e:
    _router_logger.error(f"Error mounting Payments router: {e}")

# E-invoicing
try:
    from app.routers.einvoicing import router as einvoicing_router
    app.include_router(einvoicing_router, prefix="/api/v1")
    _router_logger.info("E-invoicing router mounted at /api/v1/einvoicing")
except Exception as e:
    _router_logger.error(f"Error mounting E-invoicing router: {e}")
    # Fallback stub to keep tests working if full router import fails
    try:
        from fastapi import APIRouter, Depends, HTTPException, status
        from uuid import UUID
        from app.schemas.einvoicing import (
            EinvoicingSendRequest,
            EinvoicingStatusResponse,
        )
        from app.core.security import get_current_active_tenant_user  # type: ignore
        from app.schemas.auth import User  # type: ignore
        from app.modules.einvoicing.application import use_cases as _euc  # type: ignore

        _stub = APIRouter(prefix="/einvoicing", tags=["E-invoicing (stub)"])

        @_stub.post("/send", response_model=dict)
        async def _send_stub(
            request: EinvoicingSendRequest,
            current_user: User = Depends(get_current_active_tenant_user),
        ):
            try:
                res = await _euc.send_einvoice_use_case(
                    tenant_id=current_user.tenant_id,
                    invoice_id=request.invoice_id,
                    country=request.country,
                )
                return {"message": "E-invoice processing initiated", "task_id": res.task_id}
            except HTTPException as he:  # pragma: no cover
                raise he
            except Exception as ex:  # pragma: no cover
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initiate e-invoice processing: {ex}",
                )

        @_stub.get("/status/{invoice_id}", response_model=EinvoicingStatusResponse)
        async def _status_stub(
            invoice_id: UUID,
            current_user: User = Depends(get_current_active_tenant_user),
        ):
            res = await _euc.get_einvoice_status_use_case(
                tenant_id=current_user.tenant_id, invoice_id=invoice_id
            )
            if not res:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="E-invoice status not found",
                )
            return res

        app.include_router(_stub, prefix="/api/v1")
        _router_logger.info("E-invoicing stub router mounted at /api/v1/einvoicing")
    except Exception as e2:  # pragma: no cover
        _router_logger.error(f"Error mounting E-invoicing stub router: {e2}")

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
try:
    has_imports = any(getattr(r, "path", "").startswith("/api/v1/imports") for r in app.router.routes)
except Exception:
    has_imports = False
if not has_imports:
    mounted = False
    try:
        from .modules.imports.interface.http.tenant import (
            router as _rel_imports_router,
            public_router as _rel_imports_public,
        )

        app.include_router(_rel_imports_router, prefix="/api/v1")
        app.include_router(_rel_imports_public, prefix="/api/v1")
        mounted = True
    except Exception:
        pass
    try:
        from app.modules.imports.interface.http.tenant import (
            router as _imports_router,
            public_router as _imports_public,
        )

        app.include_router(_imports_router, prefix="/api/v1")
        app.include_router(_imports_public, prefix="/api/v1")
        mounted = True
    except Exception:
        pass
    if not mounted:
        try:
            from backend.app.modules.imports.interface.http.tenant import (
                router as _imports_router_b,
                public_router as _imports_public_b,
            )

            app.include_router(_imports_router_b, prefix="/api/v1")
            app.include_router(_imports_public_b, prefix="/api/v1")
        except Exception:
            pass

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
from sqlalchemy import inspect  # type: ignore

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
                logging.getLogger("app.startup").info("Imports runner not available (import failed)")
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
            logging.getLogger("app.startup").exception(
                "Failed starting imports runner post-bind"
            )
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
