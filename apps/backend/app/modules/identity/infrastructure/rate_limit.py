from __future__ import annotations

from app.core.login_rate_limit import check as _check
from app.core.login_rate_limit import incr_fail as _incr_fail
from app.core.login_rate_limit import reset as _reset
from app.modules.identity.application.ports import RateLimiter


class SimpleRateLimiter(RateLimiter):
    def check(self, request, ident: str):
        return _check(request, ident)

    def incr_fail(self, request, ident: str):
        return _incr_fail(request, ident)

    def reset(self, request, ident: str) -> None:
        _reset(request, ident)
