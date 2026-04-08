from __future__ import annotations

import asyncio

from app.services.ai.base import AIRequest, AITask
from app.services.ai.service import AIService


def test_ai_request_derives_prompt_from_messages():
    request = AIRequest(
        task=AITask.EXTRACTION,
        messages=[
            {"role": "system", "content": "You are a parser."},
            {"role": "user", "content": "Extract fields."},
        ],
    )

    assert request.prompt == "[system]\nYou are a parser.\n\n[user]\nExtract fields."


def test_ai_service_cache_fingerprint_changes_with_messages():
    from app.services.ai.service import _cache_fingerprint_for_request

    one = AIRequest(
        task=AITask.EXTRACTION,
        prompt="same",
        messages=[{"role": "user", "content": "one"}],
    )
    two = AIRequest(
        task=AITask.EXTRACTION,
        prompt="same",
        messages=[{"role": "user", "content": "two"}],
    )

    assert _cache_fingerprint_for_request(one) != _cache_fingerprint_for_request(two)


def test_ai_service_query_passes_messages_into_request(monkeypatch):
    captured: dict[str, object] = {}

    async def _fake_cache_get(_key: str):
        return None

    async def _fake_cache_set(*args, **kwargs):
        del args, kwargs
        return None

    async def _fake_provider_lookup(_task):
        class _Provider:
            name = "fake"
            default_model = "fake-model"

            async def call(self, request):
                captured["prompt"] = request.prompt
                captured["messages"] = request.messages
                from app.services.ai.base import AIResponse

                return AIResponse(
                    task=request.task,
                    content='{"ok": true}',
                    model="fake-model",
                )

        return _Provider()

    monkeypatch.setattr("app.services.ai.service.cache_get", _fake_cache_get)
    monkeypatch.setattr("app.services.ai.service.cache_set", _fake_cache_set)
    monkeypatch.setattr(
        "app.services.ai.service.AIProviderFactory.get_available_provider",
        _fake_provider_lookup,
    )

    response = asyncio.run(
        AIService.query(
            task=AITask.EXTRACTION,
            prompt="system and user merged",
            messages=[
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
            ],
            enable_recovery=False,
        )
    )

    assert response.is_error is False
    assert captured["prompt"] == "system and user merged"
    assert captured["messages"] == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "User"},
    ]
