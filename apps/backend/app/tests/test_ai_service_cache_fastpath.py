from __future__ import annotations

import asyncio

from app.services.ai.base import AITask
from app.services.ai.service import AIService


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
