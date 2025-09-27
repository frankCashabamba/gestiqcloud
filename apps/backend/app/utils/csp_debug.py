# app/utils/csp_debug.py
import logging
from fastapi import APIRouter, Request
from starlette.requests import Request as StarRequest
from app.config.settings import settings
from app.middleware.security_headers import _csp_for_request

router = APIRouter(tags=["debug"], include_in_schema=False)

@router.get("/__csp")
def csp_preview(request: Request):
    """Dev-only endpoint to inspect the effective CSP string for the given request."""
    return {
        "env": settings.ENV,
        "csp": _csp_for_request(request),
    }

def attach(app):
    """Attach /__csp (in non-production) and log CSP on startup."""
    # Expose the endpoint only outside production
    if settings.ENV != "production":
        app.include_router(router)

    @app.on_event("startup")
    async def _log_csp_on_startup():
        # Build a minimal Starlette Request to render CSP once on startup
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            # Use https here so any https-gated logic inside middleware is safe to preview
            "scheme": "https",
            "headers": [],
        }
        req = StarRequest(scope)
        csp = _csp_for_request(req)
        logging.getLogger("uvicorn").info("[CSP] ENV=%s | %s", settings.ENV, csp)
