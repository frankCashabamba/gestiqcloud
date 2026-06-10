"""
Endpoint webhook para el bot de Telegram.

URL por tenant: POST /api/v1/telegram/webhook/{tenant_id}

Cada tenant registra su propio bot con su propia URL. La configuración
completa (bot_token, allowed_chat_ids, parse_mode, low_stock_threshold,
webhook_secret) se gestiona desde Settings > Notificaciones > Telegram.

No se necesita ninguna variable de entorno para el bot.

Comandos soportados:
  /stock_completo  → listado completo de inventario
  /stock_bajo      → productos por debajo del umbral configurado
  (cualquier otro) → mensaje de ayuda
"""

from __future__ import annotations

import logging
import secrets

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.config.database import tenant_session_scope
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.ai.incident import NotificationChannel as ChannelConfig
from app.modules.telegram_bot.application.bot_service import (
    HELP_TEXT,
    escape_html,
    parse_allowed_chat_ids,
    send_telegram_message,
    split_long_message,
)
from app.modules.telegram_bot.application.stock_service import get_stock_bajo, get_stock_completo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram Bot"])


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------


def _load_telegram_config(tenant_id: str) -> dict | None:
    """Lee config del canal Telegram activo desde notification_channels.

    Usa `tenant_session_scope` (GUC app.tenant_id, RLS activa) — NO bypass_rls:
    el webhook solo debe ver datos del tenant de la URL, no de otros (C-04).
    """
    try:
        with tenant_session_scope(tenant_id) as db:
            channel = (
                db.query(ChannelConfig)
                .filter(
                    ChannelConfig.tenant_id == tenant_id,
                    ChannelConfig.channel_type == "telegram",
                    ChannelConfig.is_active.is_(True),
                )
                .order_by(ChannelConfig.priority.desc())
                .first()
            )
            return dict(channel.config) if channel and channel.config else None
    except Exception as exc:
        logger.error("[telegram_bot] Error cargando config [tenant=%s]: %s", tenant_id, exc)
        return None


# ---------------------------------------------------------------------------
# Formateo
# ---------------------------------------------------------------------------


def _build_stock_completo_text(items: list[dict], parse_mode: str | None) -> str:
    if not items:
        return "No hay productos en el inventario."

    use_html = parse_mode and parse_mode.upper() == "HTML"
    if use_html:
        lines = ["<b>📦 Stock Completo</b>"]
        for item in items:
            sku_part = f" [{escape_html(item['sku'])}]" if item["sku"] else ""
            lines.append(
                f"• {escape_html(item['name'])}{sku_part}: "
                f"<b>{item['qty']}</b> {escape_html(item['unit'])}"
            )
    else:
        lines = ["📦 Stock Completo"]
        for item in items:
            sku_part = f" [{item['sku']}]" if item["sku"] else ""
            lines.append(f"• {item['name']}{sku_part}: {item['qty']} {item['unit']}")

    return "\n".join(lines)


def _build_stock_bajo_text(items: list[dict], threshold: float, parse_mode: str | None) -> str:
    if not items:
        return "No hay productos con stock bajo."

    use_html = parse_mode and parse_mode.upper() == "HTML"
    if use_html:
        lines = [f"<b>⚠️ Stock Bajo (≤ {threshold})</b>"]
        for item in items:
            sku_part = f" [{escape_html(item['sku'])}]" if item["sku"] else ""
            lines.append(
                f"• {escape_html(item['name'])}{sku_part}: "
                f"<b>{item['qty']}</b> {escape_html(item['unit'])}"
            )
    else:
        lines = [f"⚠️ Stock Bajo (≤ {threshold})"]
        for item in items:
            sku_part = f" [{item['sku']}]" if item["sku"] else ""
            lines.append(f"• {item['name']}{sku_part}: {item['qty']} {item['unit']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def _process_command(
    chat_id: str,
    command: str,
    tg_config: dict,
    tenant_id: str,
) -> None:
    bot_token: str | None = tg_config.get("bot_token")
    parse_mode: str = tg_config.get("parse_mode") or "HTML"
    threshold: float = float(tg_config.get("low_stock_threshold") or 5.0)

    if not bot_token:
        logger.error("[telegram_bot] bot_token no configurado [tenant=%s]", tenant_id)
        return

    try:
        if command == "/stock_completo":
            with tenant_session_scope(tenant_id) as db:
                items = get_stock_completo(db, tenant_id)
            response_text = _build_stock_completo_text(items, parse_mode)

        elif command == "/stock_bajo":
            with tenant_session_scope(tenant_id) as db:
                items = get_stock_bajo(db, tenant_id, threshold)
            response_text = _build_stock_bajo_text(items, threshold, parse_mode)

        else:
            response_text = HELP_TEXT

    except Exception as exc:
        logger.error("[telegram_bot] Error procesando '%s': %s", command, exc, exc_info=True)
        response_text = "Error consultando el inventario. Intenta más tarde."

    for chunk in split_long_message(response_text):
        try:
            await send_telegram_message(chat_id, chunk, bot_token=bot_token, parse_mode=parse_mode)
        except Exception as exc:
            logger.error("[telegram_bot] Error enviando mensaje: %s", exc)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/webhook/{tenant_id}", status_code=200)
async def telegram_webhook(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """
    Webhook de Telegram por tenant.

    Cada tenant registra su bot con:
      https://api.gestiqcloud.com/api/v1/telegram/webhook/{tenant_id}

    El webhook_secret se configura en Settings > Notificaciones > Telegram
    y se usa al registrar el webhook con setWebhook.
    """
    # 1. Cargar config del tenant desde DB
    tg_config = _load_telegram_config(tenant_id)
    if not tg_config:
        # Responder 200 para que Telegram no reintente; config pendiente
        logger.warning("[telegram_bot] Sin canal configurado [tenant=%s]", tenant_id)
        return {"ok": True}

    # 2. Validar secret (almacenado en config del canal, no en env)
    webhook_secret: str | None = tg_config.get("webhook_secret")
    if not webhook_secret:
        logger.warning("[telegram_bot] webhook_secret no configurado [tenant=%s]", tenant_id)
        raise HTTPException(status_code=403, detail="Forbidden")
    # Comparación timing-safe para no filtrar el secret por tiempo de respuesta.
    if not secrets.compare_digest(x_telegram_bot_api_secret_token or "", webhook_secret):
        logger.warning("[telegram_bot] Secret inválido [tenant=%s]", tenant_id)
        raise HTTPException(status_code=403, detail="Forbidden")

    # 3. Parsear Update
    try:
        body: dict = await request.json()
    except Exception:
        return {"ok": True}

    message: dict | None = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}

    text: str | None = message.get("text")
    if not text or not text.strip():
        return {"ok": True}

    chat_id = str(message.get("chat", {}).get("id", ""))
    if not chat_id:
        return {"ok": True}

    # 4. Verificar chat autorizado
    allowed_ids = parse_allowed_chat_ids(tg_config.get("allowed_chat_ids", ""))
    if allowed_ids and chat_id not in allowed_ids:
        logger.info("[telegram_bot] Chat no autorizado [tenant=%s]", tenant_id)
        return {"ok": True}

    # 5. Encolar comando → responder 200 inmediatamente
    command = text.strip().split()[0].lower()
    background_tasks.add_task(_process_command, chat_id, command, tg_config, tenant_id)

    return {"ok": True}


# ---------------------------------------------------------------------------
# Gestión del webhook (endpoints autenticados)
# ---------------------------------------------------------------------------


class RegisterWebhookRequest(BaseModel):
    custom_base_url: str | None = None  # Para desarrollo local (tunnel URL)


@router.post("/register-webhook", dependencies=[Depends(require_scope("tenant"))])
async def register_telegram_webhook(
    body: RegisterWebhookRequest,
    request: Request,
    claims=Depends(with_access_claims),
) -> dict:
    """
    Registra el webhook de Telegram para este tenant.
    Auto-detecta la URL pública del servidor desde el request.
    Si se pasa custom_base_url, tiene prioridad (útil para VPS con dominio propio
    detrás de proxy, o para desarrollo local con tunnel).
    """
    tenant_id = str(claims["tenant_id"])
    tg_config = _load_telegram_config(tenant_id)
    if not tg_config:
        raise HTTPException(
            status_code=400,
            detail="Canal Telegram no configurado. Guarda primero la configuración.",
        )

    bot_token: str | None = tg_config.get("bot_token")
    if not bot_token:
        raise HTTPException(status_code=400, detail="Bot token no configurado.")

    webhook_secret: str | None = tg_config.get("webhook_secret") or None
    if not webhook_secret:
        raise HTTPException(status_code=400, detail="Webhook secret no configurado.")

    if body.custom_base_url:
        base = body.custom_base_url.rstrip("/")
    else:
        # Auto-detecta desde el request; respeta X-Forwarded-Proto si hay proxy
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = (
            request.headers.get("x-forwarded-host")
            or request.headers.get("host")
            or request.url.netloc
        )
        base = f"{proto}://{host}"

    webhook_url = f"{base}/api/v1/telegram/webhook/{tenant_id}"

    payload: dict = {"url": webhook_url, "secret_token": webhook_secret}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/setWebhook",
                json=payload,
            )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error("[telegram_bot] No se pudo conectar con Telegram: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="No se pudo conectar con api.telegram.org. Verifica la conectividad del servidor.",
        )
    except httpx.HTTPError as exc:
        logger.error("[telegram_bot] Error HTTP llamando setWebhook: %s", exc)
        raise HTTPException(status_code=502, detail=f"Error de red con Telegram: {exc}")

    data = resp.json()
    if not resp.is_success or not data.get("ok"):
        tg_error = data.get("description", f"HTTP {resp.status_code}")
        logger.error("[telegram_bot] setWebhook rechazado [tenant=%s]: %s", tenant_id, tg_error)
        raise HTTPException(
            status_code=400,
            detail=f"Telegram rechazó el webhook: {tg_error}",
        )

    logger.info("[telegram_bot] Webhook registrado [tenant=%s url=%s]", tenant_id, webhook_url)
    return {"ok": True, "webhook_url": webhook_url, "description": data.get("description", "")}


@router.post(
    "/generate-secret", dependencies=[Depends(with_access_claims), Depends(require_scope("tenant"))]
)
def generate_webhook_secret() -> dict:
    """Genera un webhook secret aleatorio seguro."""
    return {"secret": secrets.token_urlsafe(32)}
