import asyncio
import json

import app.core.cache as cache_module
from app.core.cache import CacheTTL, cache_set


class _FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str]] = []

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self.calls.append((key, ttl, value))
        return True


def test_cache_set_casts_ttl_intenum(monkeypatch):
    fake = _FakeRedis()

    async def _fake_get_client():
        return fake

    monkeypatch.setattr("app.core.cache.get_redis_client", _fake_get_client)

    ok = asyncio.run(cache_set("cache:test:key", {"ok": True}, ttl=CacheTTL.MEDIUM))

    assert ok is True
    assert fake.calls == [("cache:test:key", 300, json.dumps({"ok": True}))]


def test_cache_set_resets_client_on_closed_loop_error(monkeypatch):
    class _BrokenRedis:
        async def setex(self, key: str, ttl: int, value: str) -> bool:
            del key, ttl, value
            raise RuntimeError("Event loop is closed")

    broken = _BrokenRedis()

    async def _fake_get_client():
        return broken

    monkeypatch.setattr("app.core.cache.get_redis_client", _fake_get_client)
    monkeypatch.setattr(cache_module, "_redis_client", broken)
    monkeypatch.setattr(cache_module, "_redis_client_loop", object())

    ok = asyncio.run(cache_set("cache:test:key", {"ok": True}, ttl=CacheTTL.MEDIUM))

    assert ok is False
    assert cache_module._redis_client is None
    assert cache_module._redis_client_loop is None
