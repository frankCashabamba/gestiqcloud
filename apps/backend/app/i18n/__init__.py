"""Internationalization support for API error messages."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_translations: dict[str, dict[str, Any]] = {}
_fallback_lang = "en"


def _load_translations() -> None:
    """Load translation files from locales directory."""
    global _translations
    locales_dir = Path(__file__).parent / "locales"

    if not locales_dir.exists():
        return

    for file in locales_dir.glob("*.json"):
        lang = file.stem
        try:
            with open(file, encoding="utf-8") as f:
                _translations[lang] = json.load(f)
        except Exception:
            pass


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Translate a key to the specified language.

    Args:
        key: Dot-separated key path (e.g., "errors.notFound")
        lang: Language code (e.g., "en", "es")
        **kwargs: Interpolation variables

    Returns:
        Translated string or the key if not found.

    Example:
        t("errors.notFound", "es")  # "No encontrado"
        t("errors.itemNotFound", "en", item="Product")  # "Product not found"
    """
    if not _translations:
        _load_translations()

    # Get translation dict for language, fallback to default
    trans = _translations.get(lang, _translations.get(_fallback_lang, {}))

    # Navigate nested keys
    value = trans
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
            break

    if value is None:
        # Try fallback language
        if lang != _fallback_lang:
            return t(key, _fallback_lang, **kwargs)
        return key

    # Interpolate variables
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except KeyError:
            return value

    return str(value)


def get_lang_from_header(accept_language: str | None) -> str:
    """Extract preferred language from Accept-Language header.

    Args:
        accept_language: The Accept-Language header value

    Returns:
        Language code (e.g., "en", "es")
    """
    if not accept_language:
        return _fallback_lang

    # Parse Accept-Language header (simplified)
    # Format: "es-ES,es;q=0.9,en;q=0.8"
    for part in accept_language.split(","):
        lang = part.split(";")[0].strip().split("-")[0].lower()
        if lang in _translations:
            return lang

    return _fallback_lang


# Load translations on import
_load_translations()
