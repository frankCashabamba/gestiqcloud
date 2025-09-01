from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.security_headers import security_headers_middleware
from app.config.settings import settings
from app.core.sessions import SessionMiddlewareServerSide


import app.models  # asegura registro de modelos

from app.middleware.require_csrf import RequireCSRFMiddleware
from app.api.common.lang import router as lang_router
from app.middleware.i18n_header import ContentLanguageMiddleware
from app.middleware.request_log import RequestLogMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.metrics.store import snapshot as metrics_snapshot

from app.platform.http.router import build_api_router

app = FastAPI(title="Secure Multi-tenant BFF")


# Session middleware primero (para que request.state.session exista)
app.add_middleware(
    SessionMiddlewareServerSide,
    cookie_name="sid",
    secret_key=settings.SECRET_KEY.get_secret_value(),
    https_only=False,  # en tests/local
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(getattr(settings, "CORS_ORIGINS", ["*"])),
    allow_credentials=bool(getattr(settings, "CORS_ALLOW_CREDENTIALS", True)),
    allow_methods=list(getattr(settings, "CORS_ALLOW_METHODS", ["*"])),
    allow_headers=list(getattr(settings, "CORS_ALLOW_HEADERS", ["*"])),
    allow_origin_regex=getattr(settings, "CORS_ALLOW_ORIGIN_REGEX", None),
    expose_headers=["Content-Length"],
)
app.add_middleware(ContentLanguageMiddleware)
app.middleware("http")(security_headers_middleware)
app.add_middleware(RequireCSRFMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(MetricsMiddleware)

# Routers
app.include_router(lang_router)                                   # usa su propio prefijo interno
app.include_router(build_api_router(), prefix="/api/v1")          # todos los routers API v1

@app.get("/")
def root():
    return {"status": "ok", "app": settings.app_name}

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/metrics")
def metrics():
    counts, dur_sum = metrics_snapshot()
    # Prometheus exposition (básico)
    lines = []
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    for (method, path, status), val in sorted(counts.items()):
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {val}'
        )
    lines.append("# HELP http_request_duration_ms_sum Cumulative request duration in ms")
    lines.append("# TYPE http_request_duration_ms_sum counter")
    for (method, path, status), val in sorted(dur_sum.items()):
        lines.append(
            f'http_request_duration_ms_sum{{method="{method}",path="{path}",status="{status}"}} {val}'
        )
    from fastapi import Response

    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")

@app.get("/health/redis")
def health_redis():
    """Optional Redis healthcheck.
    - If REDIS_URL not set: returns enabled: False, ok: True (not required).
    - If set: attempts a PING. On failure returns 503 with ok: False.
    """
    from fastapi import Response
    try:
        from app.config.settings import settings
        redis_url = getattr(settings, "REDIS_URL", None)
    except Exception:
        redis_url = None

    if not redis_url:
        return {"enabled": False, "ok": True}

    try:
        import redis  # type: ignore
        r = redis.Redis.from_url(redis_url, decode_responses=True)
        r.ping()
        return {"enabled": True, "ok": True}
    except Exception as e:  # pragma: no cover - only runs when Redis down/missing
        return Response(
            content=f'{ {"enabled": True, "ok": False, "error": str(e)} }',
            media_type="application/json",
            status_code=503,
        )
