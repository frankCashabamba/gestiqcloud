import asyncio
import json

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
