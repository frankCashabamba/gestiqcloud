from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.security_headers import security_headers_middleware
from app.config.settings import settings
from app.core.sessions import SessionMiddlewareServerSide

from app.api.v1.admin.auth import router as admin_auth_router
from app.api.v1.tenant.auth import router as tenant_auth_router
# ⛔️ eliminado: from backend.app.api.v1.me import router as tenant_me_router
import app.models  # asegura registro de modelos

from app.middleware.require_csrf import RequireCSRFMiddleware
from app.api.common.lang import router as lang_router
from app.middleware.i18n_header import ContentLanguageMiddleware

from app.api.v1.tenant.sessions import router as me_sessions_router
from app.api.v1.profile import router as me_profile_router
from app.api.v1.me import router as me_router  # ✅ tu /api/v1/me y /api/v1/me/tenant

app = FastAPI(title="Secure Multi-tenant BFF")


def _to_str(v):
    return v.get_secret_value() if hasattr(v, "get_secret_value") else v


def _to_list(v, default):
    if hasattr(v, "get_secret_value"):
        v = v.get_secret_value()
    if v is None:
        return list(default)
    if isinstance(v, (list, tuple, set)):
        return list(v)
    if isinstance(v, str):
        parts = [s.strip() for s in v.split(",")]
        return [p for p in parts if p] or list(default)
    return list(default)


# Session middleware primero (para que request.state.session exista)
app.add_middleware(
    SessionMiddlewareServerSide,
    cookie_name="sid",
    secret_key=_to_str(settings.SECRET_KEY),
    https_only=False,  # en tests/local
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_to_list(getattr(settings, "CORS_ORIGINS", ["*"]), ["*"]),
    allow_credentials=bool(getattr(settings, "CORS_ALLOW_CREDENTIALS", True)),
    allow_methods=_to_list(getattr(settings, "CORS_ALLOW_METHODS", ["*"]), ["*"]),
    allow_headers=_to_list(getattr(settings, "CORS_ALLOW_HEADERS", ["*"]), ["*"]),
    allow_origin_regex=getattr(settings, "CORS_ALLOW_ORIGIN_REGEX", None),
    expose_headers=["Content-Length"],
)
app.add_middleware(ContentLanguageMiddleware)
app.middleware("http")(security_headers_middleware)
app.add_middleware(RequireCSRFMiddleware)

# Routers
app.include_router(admin_auth_router, prefix="/api/v1/admin")           # /api/v1/auth/...
app.include_router(tenant_auth_router, prefix="/api/v1/tenant")   # /api/v1/tenant/auth/...
# ⛔️ eliminado: app.include_router(tenant_me_router, prefix="/api/v1/tenant")
app.include_router(lang_router)                                   # usa su propio prefijo interno
app.include_router(me_sessions_router, prefix="/api/v1/tenant")   # /api/v1/tenant/me/sessions
app.include_router(me_profile_router, prefix="/api/v1")           # /api/v1/...
app.include_router(me_router, prefix="/api/v1")                   # /api/v1/me y /api/v1/me/tenant

@app.get("/")
def root():
    return {"status": "ok", "app": settings.app_name}

@app.get("/health")
def health():
    return {"ok": True}
