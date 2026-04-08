from __future__ import annotations

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
