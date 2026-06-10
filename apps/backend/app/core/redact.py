"""Redacción centralizada de PII / secretos para logs y telemetría.

Usar antes de loguear o emitir a telemetría cualquier estructura que pueda
contener datos sensibles (tokens, contraseñas, emails, claves, OCR/IA, etc.).

    from app.core.redact import redact_sensitive
    logger.info("evento %s", redact_sensitive(payload))
"""

from __future__ import annotations

from typing import Any

# Claves cuyo valor se oculta por completo.
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "csrf",
        "csrf_token",
        "authorization",
        "api_key",
        "apikey",
        "bot_token",
        "webhook_secret",
        "secret_token",
        "private_key",
        "certificate",
        "cert",
        "jwt",
        "raw_ai_json",
        "storage_uri",
        "card",
        "cvv",
        "iban",
    }
)

# Subcadenas que, si aparecen en el nombre de la clave, también disparan ocultación.
SENSITIVE_SUBSTRINGS = ("password", "secret", "token", "api_key", "apikey", "private")

_MASK = "***"


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    if k in SENSITIVE_KEYS:
        return True
    return any(sub in k for sub in SENSITIVE_SUBSTRINGS)


def _mask_email(value: str) -> str:
    """Enmascara la parte local del email: ada@x.com -> a***@x.com."""
    if "@" not in value:
        return value
    local, _, domain = value.partition("@")
    head = local[0] if local else ""
    return f"{head}***@{domain}"


def redact_sensitive(data: Any, *, _depth: int = 0) -> Any:
    """Devuelve una copia de `data` con valores sensibles ocultados.

    - dict: oculta valores de claves sensibles; recurre en el resto.
    - list/tuple/set: recurre en cada elemento.
    - str con forma de email: enmascara la parte local.
    - Profundidad limitada para evitar recursión patológica.
    """
    if _depth > 6:
        return data

    if isinstance(data, dict):
        out: dict[Any, Any] = {}
        for key, value in data.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                out[key] = _MASK
            else:
                out[key] = redact_sensitive(value, _depth=_depth + 1)
        return out

    if isinstance(data, (list, tuple)):
        return type(data)(redact_sensitive(v, _depth=_depth + 1) for v in data)

    if isinstance(data, set):
        return {redact_sensitive(v, _depth=_depth + 1) for v in data}

    if isinstance(data, str) and "@" in data and " " not in data and "." in data:
        return _mask_email(data)

    return data
