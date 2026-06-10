"""Tests de redacción de PII/secretos (punto 7)."""

from __future__ import annotations

from app.core.redact import redact_sensitive


def test_masks_sensitive_keys():
    out = redact_sensitive(
        {
            "password": "hunter2",
            "access_token": "abc.def",
            "bot_token": "123:xyz",
            "webhook_secret": "s3cr3t",
            "name": "Ada",
        }
    )
    assert out["password"] == "***"
    assert out["access_token"] == "***"
    assert out["bot_token"] == "***"
    assert out["webhook_secret"] == "***"
    assert out["name"] == "Ada"  # no sensible


def test_masks_by_substring():
    out = redact_sensitive({"stripe_api_key": "sk_live_x", "user_password_hash": "h"})
    assert out["stripe_api_key"] == "***"
    assert out["user_password_hash"] == "***"


def test_masks_email_local_part():
    out = redact_sensitive({"email": "ada.lovelace@example.com"})
    assert out["email"] == "a***@example.com"


def test_recurses_into_nested_structures():
    out = redact_sensitive(
        {"user": {"name": "Ada", "token": "t"}, "items": [{"secret": "x"}, {"qty": 3}]}
    )
    assert out["user"]["name"] == "Ada"
    assert out["user"]["token"] == "***"
    assert out["items"][0]["secret"] == "***"
    assert out["items"][1]["qty"] == 3


def test_non_sensitive_passthrough():
    assert redact_sensitive(42) == 42
    assert redact_sensitive("hola mundo") == "hola mundo"


def test_old_metrics_store_removed():
    import importlib

    import pytest

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.metrics.store")
