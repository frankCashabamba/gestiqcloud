"""Module: tenant_middleware.py

Auto-generated module docstring."""

# app/middleware/tenant_middleware.py

from app.modules.identity.infrastructure.jwt_service import JwtService
from fastapi import Request
from jwt import ExpiredSignatureError, InvalidTokenError
from starlette.responses import JSONResponse


class TenantMiddleware:
    """Class TenantMiddleware - auto-generated docstring."""

    def __init__(self, app):
        """Function __init__ - auto-generated docstring."""
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
                payload = JwtService().decode(token, expected_kind="access")
                scope.setdefault("state", {})
                scope["state"]["user"] = payload
            except ExpiredSignatureError:
                response = JSONResponse(
                    {"detail": "Token expirado"},
                    status_code=401,
                    headers={"X-Token-Expired": "true"},
                )
                await response(scope, receive, send)
                return
            except InvalidTokenError:
                response = JSONResponse({"detail": "Token inválido"}, status_code=401)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
