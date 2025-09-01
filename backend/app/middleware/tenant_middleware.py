"""Module: tenant_middleware.py

Auto-generated module docstring."""

# app/middleware/tenant_middleware.py

from fastapi import Request
from starlette.responses import JSONResponse

from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService


class TenantMiddleware:
    """ Class TenantMiddleware - auto-generated docstring. """
    def __init__(self, app):
        """ Function __init__ - auto-generated docstring. """
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        token = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get("access_token")

        if token:
            try:
                # Centralizado en PyJWTTokenService (valida issuer/audience/tipo)
                payload = PyJWTTokenService().decode_and_validate(token, expected_type="access")
                scope.setdefault("state", {})
                scope["state"]["user"] = payload
            except Exception as e:
                # Unificar manejo de errores como 401
                detail = getattr(e, "detail", None) or "Token inválido"
                headers = getattr(e, "headers", None) or {}
                # Propaga cabecera de expiración si viene del validador
                if isinstance(headers, dict) and "WWW-Authenticate" in headers and "expired" in headers.get("WWW-Authenticate", ""):
                    # Marcar para FE que expiró
                    headers = {**headers, "X-Token-Expired": "true"}
                response = JSONResponse({"detail": detail}, status_code=401, headers=headers)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)

