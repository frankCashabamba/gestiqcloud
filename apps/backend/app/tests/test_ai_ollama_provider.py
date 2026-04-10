from __future__ import annotations

import asyncio

from app.services.ai.base import AIRequest, AITask
from app.services.ai.factory import AIProviderFactory
from app.services.ai.providers.ollama import OllamaProvider


def test_ollama_provider_uses_independent_semaphores_for_same_base_url_and_concurrency():
    first = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "llama3.1:8b",
            "max_concurrency": "4",
        }
    )
    second = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "llama3.1:8b",
            "max_concurrency": "4",
        }
    )

    assert first.max_concurrency == 4
    assert second.max_concurrency == 4
    assert first._semaphore is not second._semaphore


def test_ollama_provider_chat_api_uses_request_messages(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}, "model": "llama3.1:8b"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url):
            captured["tags_url"] = url
            return type(
                "TagsResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"models": [{"name": "llama3.1:8b"}]},
                },
            )()

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "llama3.1:8b",
            "max_concurrency": "1",
        }
    )

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
    assert captured["json"]["model"] == "llama3.1:8b"


def test_ollama_provider_prefers_available_extraction_model(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "invalid-model",
            "max_concurrency": "1",
        }
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}, "model": "mistral:7b"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url):
            del url
            return type(
                "TagsResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {
                        "models": [{"name": "mistral:7b"}, {"name": "llama3.1:8b"}]
                    },
                },
            )()

        async def post(self, url, json):
            del url, json
            return FakeResponse()

    monkeypatch.setattr("app.services.ai.providers.ollama.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        provider.call(
            AIRequest(
                task=AITask.EXTRACTION,
                prompt="flattened",
            )
        )
    )

    assert response.is_error is False
    assert response.model == "llama3.1:8b"


def test_ollama_provider_falls_back_to_llama3_when_llama31_is_missing(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "llama3.1:8b",
            "max_concurrency": "1",
        }
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}, "model": "llama3:8b"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url):
            del url
            return type(
                "TagsResponse",
                (object,),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"models": [{"name": "llama3:8b"}]},
                },
            )()

        async def post(self, url, json):
            del url, json
            return FakeResponse()

    monkeypatch.setattr("app.services.ai.providers.ollama.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        provider.call(
            AIRequest(
                task=AITask.EXTRACTION,
                prompt="flattened",
            )
        )
    )

    assert response.is_error is False
    assert response.model == "llama3:8b"


def test_ollama_provider_blocks_legacy_qwen_extraction_override(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "qwen2.5-coder:3b",
            "max_concurrency": "1",
            "timeout": "30",
        }
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}, "model": "llama3.1:8b"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url):
            del url
            return type(
                "TagsResponse",
                (),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {
                        "models": [{"name": "llama3.1:8b"}, {"name": "mistral:7b"}]
                    },
                },
            )()

        async def post(self, url, json):
            del url, json
            return FakeResponse()

    monkeypatch.setattr("app.services.ai.providers.ollama.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        provider.call(
            AIRequest(
                task=AITask.EXTRACTION,
                prompt="flattened",
                model="qwen2.5-coder:3b",
            )
        )
    )

    assert response.is_error is True
    assert response.metadata["selection_reason"] == "no_allowed_extraction_model"
    assert "no permitido" in (response.error or "").lower()


def test_ollama_provider_blocks_first_available_for_extraction(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "invalid-model",
            "max_concurrency": "1",
        }
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url):
            del url
            return type(
                "TagsResponse",
                (object,),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"models": [{"name": "minicpm-v:latest"}]},
                },
            )()

        async def post(self, url, json):
            raise AssertionError("Ollama post should not run when model selection is blocked")

    monkeypatch.setattr("app.services.ai.providers.ollama.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        provider.call(
            AIRequest(
                task=AITask.EXTRACTION,
                prompt="flattened",
            )
        )
    )

    assert response.is_error is True
    assert response.metadata["selection_reason"] == "no_allowed_extraction_model"
    assert "allowed extraction model" in (response.error or "").lower()


def test_ollama_provider_rejects_missing_explicit_model_before_call(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "llama3.1:8b",
            "max_concurrency": "1",
        }
    )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url):
            del url
            return type(
                "TagsResponse",
                (object,),
                {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {
                        "models": [{"name": "llama3.1:8b"}, {"name": "mistral:7b"}]
                    },
                },
            )()

        async def post(self, url, json):
            raise AssertionError("Ollama post should not run for missing explicit model")

    monkeypatch.setattr("app.services.ai.providers.ollama.httpx.AsyncClient", FakeClient)

    response = asyncio.run(
        provider.call(
            AIRequest(
                task=AITask.EXTRACTION,
                prompt="flattened",
                model="missing-model",
            )
        )
    )

    assert response.is_error is True
    assert "no disponible" in (response.error or "").lower()


def test_ollama_factory_caps_legacy_timeout_and_model(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "300")

    config = AIProviderFactory._get_provider_config("ollama")

    assert config["model"] == "llama3.1:8b"
    assert config["timeout"] == 30.0
    assert config["model_source"] == "legacy_blocked"
    assert config["timeout_source"] == "env_capped"
