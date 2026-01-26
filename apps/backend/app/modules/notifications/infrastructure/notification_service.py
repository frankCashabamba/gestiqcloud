"""Notification service with multi-channel support"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    """Notification priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class BaseNotificationProvider(ABC):
    """Abstract base for notification providers"""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send notification"""
        pass


class EmailProvider(BaseNotificationProvider):
    """Email notification provider"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("provider", "smtp")  # smtp, sendgrid, etc.
        self.api_key = config.get("api_key")
        self.from_address = config.get("from_address")

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send email"""
        try:
            if self.provider == "sendgrid":
                return await self._send_via_sendgrid(recipient, subject, body)
            elif self.provider == "smtp":
                return await self._send_via_smtp(recipient, subject, body)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return {"success": False, "error": str(e)}

    async def _send_via_sendgrid(self, recipient: str, subject: str, body: str) -> dict:
        """Send via SendGrid API"""
        async with httpx.AsyncClient() as client:
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": recipient}],
                        "subject": subject,
                    }
                ],
                "from": {"email": self.from_address},
                "content": [
                    {
                        "type": "text/html",
                        "value": body,
                    }
                ],
            }

            try:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
                )

                if response.status_code < 400:
                    return {
                        "success": True,
                        "message_id": response.headers.get("X-Message-ID"),
                    }
                else:
                    return {"success": False, "error": response.text}

            except Exception as e:
                return {"success": False, "error": str(e)}

    async def _send_via_smtp(self, recipient: str, subject: str, body: str) -> dict:
        """Send via SMTP (placeholder)"""
        # In real implementation, use aiosmtplib
        logger.info(f"Would send email to {recipient}: {subject}")
        return {"success": True}


class SMSProvider(BaseNotificationProvider):
    """SMS notification provider"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("provider", "twilio")
        self.api_key = config.get("api_key")
        self.account_sid = config.get("account_sid")

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send SMS"""
        try:
            if self.provider == "twilio":
                return await self._send_via_twilio(recipient, body)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to send SMS to {recipient}: {e}")
            return {"success": False, "error": str(e)}

    async def _send_via_twilio(self, phone: str, message: str) -> dict:
        """Send via Twilio API"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json",
                    data={
                        "From": self.config.get("from_number"),
                        "To": phone,
                        "Body": message,
                    },
                    auth=(self.account_sid, self.api_key),
                    timeout=10.0,
                )

                if response.status_code < 400:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("sid"),
                    }
                else:
                    return {"success": False, "error": response.text}

            except Exception as e:
                return {"success": False, "error": str(e)}


class PushNotificationProvider(BaseNotificationProvider):
    """Push notification provider"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("provider", "firebase")
        self.api_key = config.get("api_key")

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send push notification"""
        try:
            if self.provider == "firebase":
                return await self._send_via_firebase(recipient, subject, body)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to send push notification to {recipient}: {e}")
            return {"success": False, "error": str(e)}

    async def _send_via_firebase(self, token: str, title: str, body: str) -> dict:
        """Send via Firebase Cloud Messaging"""
        async with httpx.AsyncClient() as client:
            payload = {
                "message": {
                    "notification": {
                        "title": title,
                        "body": body,
                    },
                    "token": token,
                }
            }

            try:
                response = await client.post(
                    "https://fcm.googleapis.com/v1/projects/[project-id]/messages:send",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0,
                )

                if response.status_code < 400:
                    return {"success": True}
                else:
                    return {"success": False, "error": response.text}

            except Exception as e:
                return {"success": False, "error": str(e)}


class InAppNotificationProvider(BaseNotificationProvider):
    """In-app notification provider (database-based)"""

    def __init__(self, db: Session):
        self.db = db

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Store in-app notification"""
        try:
            # In real implementation, save to database
            logger.info(f"In-app notification for {recipient}: {subject}")
            return {"success": True, "notification_id": str(uuid4())}

        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}")
            return {"success": False, "error": str(e)}


class NotificationService:
    """Main notification service"""

    def __init__(self, db: Session, config: dict):
        self.db = db
        self.config = config
        self.providers = {
            NotificationChannel.EMAIL: EmailProvider(config.get("email", {})),
            NotificationChannel.SMS: SMSProvider(config.get("sms", {})),
            NotificationChannel.PUSH: PushNotificationProvider(config.get("push", {})),
            NotificationChannel.IN_APP: InAppNotificationProvider(db),
        }

    async def send(
        self,
        recipient: str,
        channel: NotificationChannel,
        subject: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send notification via specified channel"""
        try:
            provider = self.providers.get(channel)
            if not provider:
                raise ValueError(f"Unsupported channel: {channel}")

            result = await provider.send(recipient, subject, body, metadata)

            # Log notification
            logger.info(
                f"Notification sent via {channel} to {recipient}: {result.get('success')}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {"success": False, "error": str(e)}

    async def send_to_multiple(
        self,
        recipients: list[str],
        channels: list[NotificationChannel],
        subject: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> dict[str, dict]:
        """Send notification to multiple recipients via multiple channels"""
        tasks = []

        for recipient in recipients:
            for channel in channels:
                task = self.send(
                    recipient=recipient,
                    channel=channel,
                    subject=subject,
                    body=body,
                    priority=priority,
                )
                tasks.append((recipient, channel, task))

        # Execute all tasks concurrently
        results = {}
        for recipient, channel, task in tasks:
            try:
                result = await task
                key = f"{recipient}:{channel.value}"
                results[key] = result
            except Exception as e:
                logger.error(f"Error sending to {recipient} via {channel}: {e}")

        return results

    async def send_template(
        self,
        recipient: str,
        channel: NotificationChannel,
        template_name: str,
        context: dict,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> dict:
        """Send notification using template"""
        try:
            # Load template from database/filesystem
            template = self._load_template(template_name)

            # Render template with context
            subject = template.get("subject", "").format(**context)
            body = template.get("body", "").format(**context)

            return await self.send(
                recipient=recipient,
                channel=channel,
                subject=subject,
                body=body,
                priority=priority,
            )

        except Exception as e:
            logger.error(f"Failed to send template notification: {e}")
            return {"success": False, "error": str(e)}

    def _load_template(self, template_name: str) -> dict:
        """Load notification template"""
        # Placeholder - would load from database or config
        templates = {
            "invoice_created": {
                "subject": "Factura #{invoice_number} creada",
                "body": "Se ha creado la factura #{invoice_number} por ${amount}",
            },
            "payment_received": {
                "subject": "Pago recibido",
                "body": "Se ha recibido pago de ${amount} para factura #{invoice_number}",
            },
            "low_inventory": {
                "subject": "Stock bajo",
                "body": "Producto {product_name} tiene stock bajo: {stock_level}",
            },
        }

        return templates.get(template_name, {})

    def get_notification_preferences(self, user_id: str) -> dict:
        """Get user notification preferences"""
        # Placeholder
        return {
            "email": True,
            "sms": False,
            "push": True,
            "in_app": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        }

    async def respect_preferences(
        self,
        user_id: str,
        channels: list[NotificationChannel],
    ) -> list[NotificationChannel]:
        """Filter channels based on user preferences"""
        prefs = self.get_notification_preferences(user_id)

        filtered = []
        for channel in channels:
            channel_key = channel.value
            if prefs.get(channel_key, True):
                filtered.append(channel)

        return filtered
