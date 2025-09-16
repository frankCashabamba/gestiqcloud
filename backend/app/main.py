from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from app.platform.http.router import build_api_router
from app.config.settings import settings
from app.core.sessions import SessionMiddlewareServerSide
from app.middleware.security_headers import security_headers_middleware


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

# Sesiones server-side (cookies seguras segÃºn entorno)
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
    return {"ok": True}

# Archivos subidos (logos, etc.)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Debug del enrutador central (ver quÃ© routers montan y cuÃ¡les fallan)
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


