from __future__ import annotations

import asyncio

from app.services.ai.base import AIRequest, AIResponse, AITask
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

    class _Provider:
        name = "ollama"
        default_model = "llama3.1:8b"

        async def call(self, request):
            captured["prompt"] = request.prompt
            captured["messages"] = request.messages
            return AIResponse(
                task=request.task,
                content='{"ok": true}',
                model="llama3.1:8b",
            )

    monkeypatch.setattr("app.services.ai.service.cache_get", _fake_cache_get)
    monkeypatch.setattr("app.services.ai.service.cache_set", _fake_cache_set)
    monkeypatch.setattr(
        "app.services.ai.service.AIProviderFactory.get_provider", lambda name=None: _Provider()
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


def test_ai_service_keeps_ollama_when_it_succeeds_even_with_complexity_context(monkeypatch):
    captured: dict[str, int] = {"ollama_calls": 0, "openai_calls": 0}

    async def _fake_cache_get(_key: str):
        return None

    async def _fake_cache_set(*args, **kwargs):
        del args, kwargs
        return None

    class _OllamaProvider:
        name = "ollama"
        default_model = "llama3.1:8b"

        async def call(self, request):
            del request
            captured["ollama_calls"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content='{"provider":"ollama"}',
                model="llama3.1:8b",
                processing_time_ms=2200,
            )

    class _OpenAIProvider:
        name = "openai"
        default_model = "gpt-4o"

        async def call(self, request):
            del request
            captured["openai_calls"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content='{"provider":"openai"}',
                model="gpt-4o",
                processing_time_ms=1800,
            )

    def _provider_lookup(name=None):
        if name == "openai":
            return _OpenAIProvider()
        return _OllamaProvider()

    monkeypatch.setattr("app.services.ai.service.cache_get", _fake_cache_get)
    monkeypatch.setattr("app.services.ai.service.cache_set", _fake_cache_set)
    monkeypatch.setattr("app.services.ai.service.AIProviderFactory.get_provider", _provider_lookup)

    response = asyncio.run(
        AIService.query(
            task=AITask.EXTRACTION,
            prompt="X" * 9000,
            context={
                "ai_fallback_policy": {
                    "allow_on_error": True,
                    "allow_on_slow": True,
                    "allow_on_complex": True,
                    "slow_threshold_ms": 15000,
                    "complexity_score": 0.91,
                    "complexity_threshold": 0.72,
                }
            },
            enable_recovery=False,
        )
    )

    assert response.is_error is False
    assert response.content == '{"provider":"ollama"}'
    assert response.model == "llama3.1:8b"
    assert captured["ollama_calls"] == 1
    assert captured["openai_calls"] == 0


def test_ai_service_falls_back_to_openai_on_real_ollama_error(monkeypatch):
    captured: dict[str, int] = {"ollama_calls": 0, "openai_calls": 0}

    async def _fake_cache_get(_key: str):
        return None

    async def _fake_cache_set(*args, **kwargs):
        del args, kwargs
        return None

    class _OllamaProvider:
        name = "ollama"
        default_model = "llama3.1:8b"

        async def call(self, request):
            del request
            captured["ollama_calls"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content="",
                model="llama3.1:8b",
                error="Ollama timeout",
            )

    class _OpenAIProvider:
        name = "openai"
        default_model = "gpt-4o"

        async def call(self, request):
            del request
            captured["openai_calls"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content='{"provider":"openai"}',
                model="gpt-4o",
            )

    def _provider_lookup(name=None):
        if name == "openai":
            return _OpenAIProvider()
        return _OllamaProvider()

    monkeypatch.setattr("app.services.ai.service.cache_get", _fake_cache_get)
    monkeypatch.setattr("app.services.ai.service.cache_set", _fake_cache_set)
    monkeypatch.setattr("app.services.ai.service.AIProviderFactory.get_provider", _provider_lookup)

    response = asyncio.run(
        AIService.query(
            task=AITask.EXTRACTION,
            prompt="texto simple",
            enable_recovery=False,
        )
    )

    assert response.is_error is False
    assert response.content == '{"provider":"openai"}'
    assert response.model == "gpt-4o"
    assert captured["ollama_calls"] == 1
    assert captured["openai_calls"] == 1


def test_ai_service_skips_openai_when_rate_limited(monkeypatch):
    captured: dict[str, int] = {"ollama_calls": 0, "openai_calls": 0}

    async def _fake_cache_get(key: str):
        if "openai_rate_limit" in key:
            return {"until": 9999999999, "reason": "429"}
        return None

    async def _fake_cache_set(*args, **kwargs):
        del args, kwargs
        return None

    class _OllamaProvider:
        name = "ollama"
        default_model = "llama3.1:8b"

        async def call(self, request):
            del request
            captured["ollama_calls"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content="",
                model="llama3.1:8b",
                error="Ollama timeout",
            )

    class _OpenAIProvider:
        name = "openai"
        default_model = "gpt-4o"

        async def call(self, request):
            del request
            captured["openai_calls"] += 1
            return AIResponse(
                task=AITask.EXTRACTION,
                content='{"provider":"openai"}',
                model="gpt-4o",
            )

    def _provider_lookup(name=None):
        if name == "openai":
            return _OpenAIProvider()
        return _OllamaProvider()

    monkeypatch.setattr("app.services.ai.service.cache_get", _fake_cache_get)
    monkeypatch.setattr("app.services.ai.service.cache_set", _fake_cache_set)
    monkeypatch.setattr("app.services.ai.service.AIProviderFactory.get_provider", _provider_lookup)

    response = asyncio.run(
        AIService.query(
            task=AITask.EXTRACTION,
            prompt="X" * 9000,
            context={
                "ai_fallback_policy": {
                    "allow_on_error": True,
                    "allow_on_slow": True,
                    "allow_on_complex": True,
                    "slow_threshold_ms": 15000,
                    "complexity_score": 0.91,
                    "complexity_threshold": 0.72,
                }
            },
            enable_recovery=False,
        )
    )

    assert response.is_error is True
    assert captured["ollama_calls"] == 1
    assert captured["openai_calls"] == 0
