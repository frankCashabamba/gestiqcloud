"""Tests del webhook de Telegram (C-04).

- El webhook valida el secret antes de procesar (403 si falta/!=).
- No usa bypass_rls para leer datos del tenant (usa tenant_session_scope).
"""

from __future__ import annotations

import inspect

from fastapi.testclient import TestClient

from app.main import app

TID = "00000000-0000-0000-0000-000000000002"
URL = f"/api/v1/telegram/webhook/{TID}"


def _patch_config(monkeypatch, config):
    from app.modules.telegram_bot.interface.http import webhook as wh

    monkeypatch.setattr(wh, "_load_telegram_config", lambda tenant_id: config)


def test_rejects_missing_secret(monkeypatch):
    _patch_config(monkeypatch, {"webhook_secret": "good", "bot_token": "x"})
    client = TestClient(app)
    r = client.post(URL, json={"message": {"text": "/stock_bajo"}})
    assert r.status_code == 403


def test_rejects_invalid_secret(monkeypatch):
    _patch_config(monkeypatch, {"webhook_secret": "good", "bot_token": "x"})
    client = TestClient(app)
    r = client.post(
        URL,
        headers={"X-Telegram-Bot-Api-Secret-Token": "bad"},
        json={"message": {"text": "/stock_bajo"}},
    )
    assert r.status_code == 403


def test_accepts_valid_secret(monkeypatch):
    _patch_config(monkeypatch, {"webhook_secret": "good", "bot_token": "x", "allowed_chat_ids": ""})
    client = TestClient(app)
    r = client.post(
        URL,
        headers={"X-Telegram-Bot-Api-Secret-Token": "good"},
        json={"message": {"text": "hola", "chat": {"id": 1}}},
    )
    assert r.status_code == 200


def test_webhook_does_not_use_bypass_rls():
    from app.modules.telegram_bot.interface.http import webhook as wh

    src = inspect.getsource(wh)
    # No debe ACTIVAR bypass (la mención en comentarios está permitida).
    assert 'db.info["bypass_rls"]' not in src
    assert "bypass_rls = True" not in src
    assert "tenant_session_scope" in src
