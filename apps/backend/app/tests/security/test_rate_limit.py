"""Tests del rate limiting por endpoint (punto 6).

Cubren el fallback en memoria (sin Redis): el límite por endpoint bloquea tras
N requests dentro de la ventana, y el decorador muerto fue eliminado.
"""

from __future__ import annotations

from app.middleware.endpoint_rate_limit import EndpointRateLimiter


def _limiter():
    # app=None: BaseHTTPMiddleware solo lo guarda; _check_memory no lo usa.
    return EndpointRateLimiter(app=None, limits={"/x": (2, 60)}, redis_url=None)


def test_memory_allows_up_to_limit_then_blocks():
    lim = _limiter()
    a1, _, rem1 = lim._check_memory("ip1", "/x", 2, 60)
    a2, _, _ = lim._check_memory("ip1", "/x", 2, 60)
    a3, retry, _ = lim._check_memory("ip1", "/x", 2, 60)
    assert a1 is True and a2 is True
    assert a3 is False
    assert retry > 0


def test_memory_is_per_key():
    lim = _limiter()
    lim._check_memory("ip1", "/x", 1, 60)
    blocked, _, _ = lim._check_memory("ip1", "/x", 1, 60)
    other_ok, _, _ = lim._check_memory("ip2", "/x", 1, 60)
    assert blocked is False  # ip1 agotó su cuota
    assert other_ok is True  # ip2 tiene la suya


def test_redis_url_picked_from_arg():
    lim = EndpointRateLimiter(app=None, limits={}, redis_url="redis://example:6379/0")
    assert lim.redis_url == "redis://example:6379/0"


def test_decorator_rate_limit_removed():
    import app.middleware.endpoint_rate_limit as mod

    # El decorador en memoria (tercera vía, código muerto) fue eliminado.
    assert not hasattr(mod, "rate_limit")
