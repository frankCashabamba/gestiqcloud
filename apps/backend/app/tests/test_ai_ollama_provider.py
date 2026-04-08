from __future__ import annotations

import asyncio

from app.services.ai.base import AIRequest, AITask
from app.services.ai.providers.ollama import OllamaProvider


def test_ollama_provider_reuses_semaphore_for_same_base_url_and_concurrency():
    first = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5:3b",
            "max_concurrency": "3",
        }
    )
    second = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5:3b",
            "max_concurrency": "3",
        }
    )
    third = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5:3b",
            "max_concurrency": "1",
        }
    )

    assert first.max_concurrency == 3
    assert second.max_concurrency == 3
    assert third.max_concurrency == 1
    assert first._semaphore is second._semaphore
    assert first._semaphore is not third._semaphore


def test_ollama_provider_chat_api_uses_request_messages(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}, "model": "qwen2.5:3b"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5:3b",
            "max_concurrency": "1",
        }
    )

    async def _healthy():
        return True

    monkeypatch.setattr(provider, "health_check", _healthy)
    monkeypatch.setattr("app.services.ai.providers.ollama.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        provider.call(
            AIRequest(
                task=AITask.EXTRACTION,
                prompt="flattened",
                messages=[
                    {"role": "system", "content": "System"},
                    {"role": "user", "content": "User"},
                ],
            )
        )
    )

    assert response.is_error is False
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "User"},
    ]


def test_ollama_provider_prefers_stronger_extraction_models(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5-coder:3b",
            "max_concurrency": "1",
        }
    )

    monkeypatch.setattr(
        provider,
        "_get_available_models",
        lambda timeout=3.0: [
            "qwen2.5-coder:3b",
            "qwen2.5-coder:14b",
            "qwen3-coder:latest",
        ],
    )

    assert provider.get_default_model(AITask.EXTRACTION) == "qwen3-coder:latest"


def test_ollama_provider_respects_explicit_extraction_model_override(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5-coder:3b",
            "max_concurrency": "1",
        }
    )

    monkeypatch.setenv("OLLAMA_EXTRACTION_MODEL", "qwen2.5-coder:14b")
    monkeypatch.setattr(
        provider,
        "_get_available_models",
        lambda timeout=3.0: [
            "qwen2.5-coder:3b",
            "qwen2.5-coder:14b",
            "qwen3-coder:latest",
        ],
    )

    assert provider.get_default_model(AITask.EXTRACTION) == "qwen2.5-coder:14b"
