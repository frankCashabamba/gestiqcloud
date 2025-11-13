from __future__ import annotations

from typing import Protocol, Tuple, Optional

from app.core.login_rate_limit import RLStatus  # reuse existing type


class TokenService(Protocol):
    def issue_access(self, payload: dict) -> str: ...

    def issue_refresh(
        self, payload: dict, *, jti: str, prev_jti: Optional[str]
    ) -> str: ...

    def decode_and_validate(self, token: str, *, expected_type: str) -> dict: ...


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> Tuple[bool, Optional[str]]: ...


class RateLimiter(Protocol):
    def check(self, request, ident: str) -> RLStatus:  # request is FastAPI Request
        ...

    def incr_fail(self, request, ident: str) -> RLStatus: ...

    def reset(self, request, ident: str) -> None: ...


class RefreshTokenRepo(Protocol):
    def create_family(self, *, user_id: str, tenant_id: str | None) -> str: ...

    def issue_token(
        self,
        *,
        family_id: str,
        prev_jti: str | None,
        user_agent: str,
        ip: str,
    ) -> str:  # returns new jti
        ...

    def mark_used(self, *, jti: str) -> None: ...

    def is_reused_or_revoked(self, *, jti: str) -> bool: ...

    def revoke_family(self, *, family_id: str) -> None: ...

    def get_family(self, *, jti: str) -> str | None: ...
