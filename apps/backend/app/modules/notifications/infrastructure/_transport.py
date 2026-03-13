"""
Funciones de envío síncronas compartidas entre:
  - notification_service.py  (llamadas desde asyncio.to_thread)
  - workers/notifications.py (Celery tasks, contexto síncrono)
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Email (SMTP)
# ---------------------------------------------------------------------------

def send_smtp(
    config: dict[str, Any],
    to: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """
    Envía email vía SMTP.

    Config keys (todos opcionales — caen a env vars):
      smtp_host, smtp_port, smtp_user, smtp_password, from_email, use_tls
    """
    smtp_host = config.get("smtp_host") or os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port") or os.getenv("SMTP_PORT", "587"))
    smtp_user = config.get("smtp_user") or os.getenv("SMTP_USER")
    smtp_pass = config.get("smtp_password") or os.getenv("SMTP_PASSWORD")
    from_email = config.get("from_email") or smtp_user
    use_tls: bool = config.get("use_tls", True)

    if not smtp_user or not smtp_pass:
        raise ValueError("Credenciales SMTP no configuradas (smtp_user / smtp_password)")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg.attach(MIMEText(body, "html", "utf-8"))

    if use_tls:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    return {"sent": True, "to": to, "from": from_email}


# ---------------------------------------------------------------------------
# WhatsApp (Twilio o API genérica)
# ---------------------------------------------------------------------------

def send_whatsapp(
    config: dict[str, Any],
    phone: str,
    message: str,
) -> dict[str, Any]:
    """
    Envía WhatsApp vía Twilio o API genérica.

    Config para Twilio:
      provider='twilio', account_sid, auth_token, from_number

    Config para API genérica:
      provider='generic', api_url, api_key
    """
    provider = config.get("provider", "twilio")

    if provider == "twilio":
        try:
            from twilio.rest import Client  # type: ignore[import]
        except ImportError:
            raise ImportError("Instalar twilio: pip install twilio")

        account_sid = config.get("account_sid")
        auth_token = config.get("auth_token")
        from_number = config.get("from_number")

        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Configuración Twilio incompleta (account_sid, auth_token, from_number)")

        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=f"whatsapp:{from_number}",
            body=message,
            to=f"whatsapp:{phone}",
        )
        return {"sent": True, "provider": "twilio", "message_sid": msg.sid, "status": msg.status}

    if provider == "generic":
        api_url = config.get("api_url")
        api_key = config.get("api_key")
        if not api_url or not api_key:
            raise ValueError("API URL y API Key requeridos para provider genérico")

        resp = requests.post(
            api_url,
            json={"phone": phone, "message": message},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        return {"sent": True, "provider": "generic", "response": resp.json()}

    raise ValueError(f"Provider WhatsApp no soportado: {provider}")


# ---------------------------------------------------------------------------
# Telegram (Bot API)
# ---------------------------------------------------------------------------

def send_telegram(
    config: dict[str, Any],
    chat_id: str,
    message: str,
) -> dict[str, Any]:
    """
    Envía mensaje vía Telegram Bot API.

    Config keys: bot_token, parse_mode (default: HTML), api_base (opcional)
    """
    bot_token = config.get("bot_token")
    if not bot_token:
        raise ValueError("bot_token no configurado")

    api_base = (config.get("api_base") or os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")).rstrip("/")
    parse_mode = config.get("parse_mode", "HTML")

    resp = requests.post(
        f"{api_base}/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"sent": True, "message_id": data["result"]["message_id"], "chat_id": chat_id}
