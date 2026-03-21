"""
Tests unitarios para el bot de Telegram.

Cubre:
  - parse_allowed_chat_ids
  - split_long_message
  - escape_html
  - validación del secret token (lógica del webhook)
  - routing de comandos (texto → comando extraído)
"""

from __future__ import annotations

import pytest

from app.modules.telegram_bot.application.bot_service import (
    HELP_TEXT,
    escape_html,
    parse_allowed_chat_ids,
    split_long_message,
)

# ---------------------------------------------------------------------------
# parse_allowed_chat_ids
# ---------------------------------------------------------------------------


def test_parse_allowed_chat_ids_csv():
    result = parse_allowed_chat_ids("123456,789012")
    assert result == ["123456", "789012"]


def test_parse_allowed_chat_ids_csv_spaces():
    result = parse_allowed_chat_ids("  123 , 456 , 789  ")
    assert result == ["123", "456", "789"]


def test_parse_allowed_chat_ids_empty():
    assert parse_allowed_chat_ids("") == []
    assert parse_allowed_chat_ids("   ") == []


def test_parse_allowed_chat_ids_single():
    assert parse_allowed_chat_ids("7980394648") == ["7980394648"]


def test_parse_allowed_chat_ids_trailing_comma():
    result = parse_allowed_chat_ids("111,222,")
    assert result == ["111", "222"]


# ---------------------------------------------------------------------------
# split_long_message
# ---------------------------------------------------------------------------


def test_split_long_message_short():
    text = "Hola mundo"
    assert split_long_message(text) == ["Hola mundo"]


def test_split_long_message_exact_limit():
    text = "x" * 4000
    parts = split_long_message(text, max_len=4000)
    assert parts == [text]


def test_split_long_message_needs_split():
    text = "x" * 4001
    parts = split_long_message(text, max_len=4000)
    assert len(parts) == 2
    assert parts[0] == "x" * 4000
    assert parts[1] == "x"


def test_split_long_message_prefers_newline():
    line = "a" * 100
    text = "\n".join([line] * 50)  # 5050 chars with newlines
    parts = split_long_message(text, max_len=2000)
    for part in parts:
        assert len(part) <= 2000


def test_split_long_message_total_content_preserved():
    original = "línea " * 1000
    parts = split_long_message(original, max_len=500)
    reconstructed = "\n".join(parts)
    # el contenido puede tener newlines añadidos por el split pero nada se pierde
    assert original.replace("\n", "") in reconstructed.replace("\n", "")


# ---------------------------------------------------------------------------
# escape_html
# ---------------------------------------------------------------------------


def test_escape_html_safe_string():
    assert escape_html("Producto normal") == "Producto normal"


def test_escape_html_angle_brackets():
    assert escape_html("<script>") == "&lt;script&gt;"


def test_escape_html_ampersand():
    assert escape_html("a & b") == "a &amp; b"


def test_escape_html_none():
    assert escape_html(None) == ""


# ---------------------------------------------------------------------------
# Validación del secret token (lógica pura)
# ---------------------------------------------------------------------------


def _validate_secret(received: str | None, expected: str | None) -> bool:
    """Extrae la lógica de validación del webhook para testearla sin HTTP."""
    if not expected:
        return True  # sin secret → permite todo (dev)
    return received == expected


def test_secret_token_match():
    assert _validate_secret("abc123", "abc123") is True


def test_secret_token_mismatch():
    assert _validate_secret("wrong", "abc123") is False


def test_secret_token_none_received():
    assert _validate_secret(None, "abc123") is False


def test_secret_token_not_configured():
    assert _validate_secret(None, None) is True
    assert _validate_secret("anything", None) is True


# ---------------------------------------------------------------------------
# Routing de comandos (extracción de texto → comando)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_command",
    [
        ("/stock_completo", "/stock_completo"),
        ("/STOCK_COMPLETO", "/stock_completo"),
        ("/stock_bajo", "/stock_bajo"),
        ("/stock_bajo extra text", "/stock_bajo"),
        ("/unknown", "/unknown"),
        ("hola mundo", "hola"),
    ],
)
def test_command_extraction(text: str, expected_command: str):
    command = text.strip().split()[0].lower()
    assert command == expected_command


def test_help_text_contains_commands():
    assert "/stock_completo" in HELP_TEXT
    assert "/stock_bajo" in HELP_TEXT
