from __future__ import annotations

from app.modules.identity.application.ports import TokenService
from app.modules.identity.infrastructure.jwt_service import JwtService


class PyJWTTokenService(TokenService):
    """Adapter that conforms to TokenService using the new JwtService."""

    def __init__(self) -> None:
        self._svc = JwtService()

    def issue_access(self, payload: dict) -> str:
        return self._svc.encode(payload, kind="access")

    def issue_refresh(self, payload: dict, *, jti: str, prev_jti: str | None) -> str:
        return self._svc.encode({**payload, "jti": jti, "prev_jti": prev_jti}, kind="refresh")

    def decode_and_validate(self, token: str, *, expected_type: str) -> dict:
        return dict(self._svc.decode(token, expected_kind=expected_type))
