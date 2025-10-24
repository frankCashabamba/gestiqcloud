from __future__ import annotations

from app.modules.identity.application.ports import RateLimiter
from app.core.login_rate_limit import check as _check, incr_fail as _incr_fail, reset as _reset


class SimpleRateLimiter(RateLimiter):
    def check(self, request, ident: str):
        return _check(request, ident)

    def incr_fail(self, request, ident: str):
        return _incr_fail(request, ident)

    def reset(self, request, ident: str) -> None:
        _reset(request, ident)

