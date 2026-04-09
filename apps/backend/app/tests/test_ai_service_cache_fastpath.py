from __future__ import annotations

import asyncio

from app.services.ai.base import AITask
from app.services.ai.service import AIResponse, AIService


def test_ai_service_returns_cached_response_without_provider_lookup(monkeypatch):
    provider_calls = {"count": 0}

    async def _fake_cache_get(_key: str):
        return {
            "content": '{"ok": true}',
            "model": "cache-model",
            "tokens_used": 12,
            "confidence": 0.88,
            "metadata": {"cached": True},
        }

    def _unexpected_provider_lookup(name=None):
        provider_calls["count"] += 1
        raise AssertionError("provider lookup should not run on cache hit")

    monkeypatch.setattr("app.services.ai.service.cache_get", _fake_cache_get)
    monkeypatch.setattr(
        "app.services.ai.service.AIProviderFactory.get_provider",
        _unexpected_provider_lookup,
    )

    response = asyncio.run(
        AIService.query(
            task=AITask.EXTRACTION,
            prompt="same prompt",
            tenant_id="tenant-1",
            enable_recovery=False,
        )
    )

    assert response.is_error is False
    assert response.content == '{"ok": true}'
    assert response.model == "cache-model"
    assert response.metadata["source"] == "redis_cache"
    assert provider_calls["count"] == 0


def test_ai_service_bypasses_cache_and_hits_provider(monkeypatch):
    cache_calls = {"get": 0, "set": 0}
    provider_calls = {"count": 0}

    async def _unexpected_cache_get(_key: str):
        cache_calls["get"] += 1
        raise AssertionError("cache lookup should be bypassed")

    async def _unexpected_cache_set(*args, **kwargs):
        del args, kwargs
        cache_calls["set"] += 1
        raise AssertionError("cache store should be bypassed")

    class FakeProvider:
        name = "fake"
        default_model = "fake-model"

        async def call(self, request):
            del request
            provider_calls["count"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content='{"ok": true}',
                model="fake-model",
                metadata={"source": "provider"},
            )

    monkeypatch.setattr("app.services.ai.service.cache_get", _unexpected_cache_get)
    monkeypatch.setattr("app.services.ai.service.cache_set", _unexpected_cache_set)
    monkeypatch.setattr(
        "app.services.ai.service.AIProviderFactory.get_provider",
        lambda name=None: FakeProvider(),
    )

    response = asyncio.run(
        AIService.query(
            task=AITask.EXTRACTION,
            prompt="fresh prompt",
            tenant_id="tenant-1",
            enable_recovery=False,
            bypass_cache=True,
        )
    )

    assert response.is_error is False
    assert response.content == '{"ok": true}'
    assert response.model == "fake-model"
    assert response.metadata["source"] == "provider"
    assert provider_calls["count"] == 1
    assert cache_calls == {"get": 0, "set": 0}
