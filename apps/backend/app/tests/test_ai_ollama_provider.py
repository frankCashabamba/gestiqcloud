from __future__ import annotations

import asyncio

from app.services.ai.base import AIModel, AIRequest, AITask
from app.services.ai.factory import AIProviderFactory
from app.services.ai.providers.ollama import OllamaProvider

_MODEL = AIModel.QWEN3_8B.value
_MODEL_1_7B = "qwen3:1.7b"


def test_ollama_provider_uses_independent_semaphores_for_same_base_url_and_concurrency():
    first = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": _MODEL,
            "max_concurrency": "4",
        }
    )
    second = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": _MODEL,
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
            return {"message": {"content": '{"ok": true}'}, "model": _MODEL}

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
                    "json": lambda self: {"models": [{"name": _MODEL}]},
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
            "model": _MODEL,
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
    assert captured["json"]["model"] == _MODEL


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
            return {"message": {"content": '{"ok": true}'}, "model": _MODEL}

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
                    "json": lambda self: {"models": [{"name": _MODEL}]},
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
    assert response.model == _MODEL


def test_ollama_provider_prefers_qwen_1_7b_when_it_is_allowed_and_available(monkeypatch):
    provider = OllamaProvider(
        {
            "url": "http://127.0.0.1:11434",
            "endpoint": "/api/chat",
            "model": "invalid-model",
            "allowed_extraction_models": [_MODEL_1_7B, _MODEL],
            "max_concurrency": "1",
        }
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}, "model": _MODEL_1_7B}

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
                    "json": lambda self: {"models": [{"name": _MODEL_1_7B}]},
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
    assert response.model == _MODEL_1_7B


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
            return {"message": {"content": '{"ok": true}'}, "model": _MODEL}

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
                    "json": lambda self: {"models": [{"name": _MODEL}]},
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
            "model": _MODEL,
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
                    "json": lambda self: {"models": [{"name": _MODEL}]},
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
    monkeypatch.setenv("OLLAMA_BLOCKED_PREFIXES", "qwen2.5-coder,qwen2.5")
    monkeypatch.setenv("OLLAMA_MAX_TIMEOUT", "30")

    # Re-importar las constantes del módulo para que lean los nuevos env vars
    import importlib
    import app.services.ai.factory as factory_mod
    importlib.reload(factory_mod)

    config = factory_mod.AIProviderFactory._get_provider_config("ollama")

    assert config["model"] == _MODEL
    assert config["timeout"] == 30.0
    assert config["model_source"] == "legacy_blocked"
    assert config["timeout_source"] == "env_capped"
