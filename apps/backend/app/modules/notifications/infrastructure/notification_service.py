"""
Servicio de notificaciones unificado.

Responsabilidades:
  - Seleccionar el canal correcto según tipo
  - Cargar configuración desde notification_channels (BD por tenant)
  - Delegar el envío a _transport.py (funciones síncronas corridas en executor)
  - Registrar cada envío en notification_logs (audit log)
  - Gestionar notificaciones in-app en la tabla notifications
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.ai.incident import NotificationChannel as ChannelConfig
from app.models.ai.incident import NotificationLog
from app.modules.notifications.infrastructure._transport import (
    send_smtp,
    send_telegram,
    send_whatsapp,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums públicos
# ---------------------------------------------------------------------------


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ---------------------------------------------------------------------------
# Servicio principal
# ---------------------------------------------------------------------------


class NotificationService:
    """
    Servicio de notificaciones unificado.

    Uso desde endpoints FastAPI (async):
        service = NotificationService(db, tenant_id=tenant_uuid)
        result = await service.send(channel=..., recipient=..., subject=..., body=...)

    Uso desde workers Celery (sync):
        Usar directamente las funciones en _transport.py o
        asyncio.run(NotificationService(...).send(...))
    """

    def __init__(self, db: Session, tenant_id: UUID | str | None = None):
        self.db = db
        self.tenant_id = UUID(str(tenant_id)) if tenant_id else None

    # ------------------------------------------------------------------
    # Envío principal
    # ------------------------------------------------------------------

    async def send(
        self,
        *,
        channel: NotificationChannel | str,
        recipient: str,
        subject: str,
        body: str,
        priority: NotificationPriority | str = NotificationPriority.MEDIUM,
        metadata: dict | None = None,
        ref_type: str | None = None,
        ref_id: str | None = None,
    ) -> dict:
        """
        Envía notificación por el canal indicado.
        Registra el resultado en notification_logs (todos los canales externos).
        """
        channel_val = channel.value if isinstance(channel, NotificationChannel) else channel

        try:
            config = self._load_channel_config(channel_val)
            result = await self._dispatch(channel_val, recipient, subject, body, config)
            result["success"] = True
        except Exception as exc:
            logger.error("Error enviando notificación [%s → %s]: %s", channel_val, recipient, exc)
            result = {"success": False, "error": str(exc)}

        # Audit log para canales externos
        if channel_val != NotificationChannel.IN_APP.value:
            self._write_log(
                channel_type=channel_val,
                recipient=recipient,
                subject=subject,
                body=body,
                status="sent" if result["success"] else "failed",
                error_message=result.get("error"),
                extra_data=result,
                ref_type=ref_type,
                ref_id=ref_id,
            )

        return result

    # ------------------------------------------------------------------
    # Despacho por canal
    # ------------------------------------------------------------------

    async def _dispatch(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        config: dict,
    ) -> dict:
        loop = asyncio.get_event_loop()

        if channel == "email":
            return await loop.run_in_executor(None, send_smtp, config, recipient, subject, body)

        if channel == "whatsapp":
            return await loop.run_in_executor(None, send_whatsapp, config, recipient, body)

        if channel == "telegram":
            return await loop.run_in_executor(None, send_telegram, config, recipient, body)

        if channel == "sms":
            # ACLARACION: el canal 'sms' en este módulo usa WhatsApp/Twilio, no SMS real
            return await loop.run_in_executor(None, send_whatsapp, config, recipient, body)

        if channel == "in_app":
            return {"success": True, "notification_id": str(uuid4())}

        raise ValueError(f"Canal no soportado: {channel}")

    # ------------------------------------------------------------------
    # Carga de configuración de canal desde BD
    # ------------------------------------------------------------------

    def _load_channel_config(self, channel_type: str) -> dict:
        """
        Devuelve el config JSON del canal activo para este tenant.
        Si no hay canal configurado (o canal in_app), devuelve dict vacío
        — los transportes caen a variables de entorno.
        """
        if channel_type == "in_app" or not self.tenant_id:
            return {}

        channel_row = (
            self.db.query(ChannelConfig)
            .filter(
                ChannelConfig.tenant_id == self.tenant_id,
                ChannelConfig.channel_type == channel_type,
                ChannelConfig.is_active.is_(True),
            )
            .order_by(ChannelConfig.priority.desc())
            .first()
        )

        base_config: dict = dict(channel_row.config) if channel_row else {}
        # Inyectar tenant_id como hint para logs de fallback en _transport.py
        base_config.setdefault("_tenant_id", str(self.tenant_id))
        return base_config

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def _write_log(
        self,
        *,
        channel_type: str,
        recipient: str,
        subject: str,
        body: str,
        status: str,
        error_message: str | None = None,
        extra_data: dict | None = None,
        ref_type: str | None = None,
        ref_id: str | None = None,
    ) -> None:
        try:
            log = NotificationLog(
                tenant_id=self.tenant_id,
                notification_type=channel_type,
                recipient=recipient,
                subject=subject,
                body=body,
                status=status,
                error_message=error_message,
                extra_data=extra_data,
                sent_at=datetime.now(UTC) if status == "sent" else None,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as exc:
            logger.warning("No se pudo escribir notification_log: %s", exc)

    # ------------------------------------------------------------------
    # Helpers de conveniencia
    # ------------------------------------------------------------------

    async def send_to_multiple(
        self,
        recipients: list[str],
        channels: list[NotificationChannel | str],
        subject: str,
        body: str,
        priority: NotificationPriority | str = NotificationPriority.MEDIUM,
    ) -> dict[str, dict]:
        tasks = {
            f"{r}:{c}": self.send(
                channel=c, recipient=r, subject=subject, body=body, priority=priority
            )
            for r in recipients
            for c in channels
        }
        results = {}
        for key, coro in tasks.items():
            results[key] = await coro
        return results
