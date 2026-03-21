"""
Lógica pura del bot de Telegram (sin dependencias de DB).

Responsabilidades:
  - Parsear lista de chat IDs autorizados desde CSV
  - Dividir mensajes largos respetando límites de Telegram
  - Enviar mensajes vía Telegram Bot API (reutiliza send_telegram de _transport)
  - Escapar HTML para parse_mode=HTML
"""
from __future__ import annotations

import asyncio
import html
import logging

from app.modules.notifications.infrastructure._transport import send_telegram as _sync_send_telegram

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Comandos disponibles:\n"
    "/stock_completo\n"
    "/stock_bajo"
)

# Telegram limita mensajes a 4096 caracteres; usamos margen.
_MAX_MSG_LEN = 4000


def parse_allowed_chat_ids(csv_value: str) -> list[str]:
    """Parsea CSV de chat IDs autorizados. Devuelve lista de strings."""
    if not csv_value or not csv_value.strip():
        return []
    return [item.strip() for item in csv_value.split(",") if item.strip()]


def split_long_message(text: str, max_len: int = _MAX_MSG_LEN) -> list[str]:
    """
    Divide texto en chunks de hasta max_len caracteres.
    Intenta dividir en newline para no cortar en medio de una línea.
    """
    if len(text) <= max_len:
        return [text]

    parts: list[str] = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


def escape_html(value: str | None) -> str:
    """Escapa caracteres HTML para parse_mode=HTML."""
    return html.escape(str(value or ""), quote=False)


async def send_telegram_message(
    chat_id: str,
    text: str,
    *,
    bot_token: str,
    parse_mode: str | None = "HTML",
) -> None:
    """
    Envía un mensaje a un chat de Telegram.

    Delega en send_telegram() de _transport (ya probado, ya existe),
    ejecutándolo en un thread pool para no bloquear el event loop.
    """
    config = {
        "bot_token": bot_token,
        "parse_mode": parse_mode or "HTML",
    }
    await asyncio.to_thread(_sync_send_telegram, config, chat_id, text)
    logger.debug("[telegram_bot] Mensaje enviado a chat (enmascarado)")
