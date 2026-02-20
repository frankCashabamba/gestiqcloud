"""Webhook delivery handler with retry logic."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta

import httpx

from app.modules.webhooks.domain.models import WebhookDelivery

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    """Handle webhook HTTP delivery with retry logic."""

    BASE_DELAY_SECONDS = 1
    BACKOFF_MULTIPLIER = 2
    MAX_ATTEMPTS = 5

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _sign_payload(payload: dict, secret: str) -> str:
        """Create HMAC-SHA256 signature for webhook payload."""
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(secret.encode(), payload_json.encode(), hashlib.sha256).hexdigest()
        return signature

    async def deliver(
        self,
        delivery: WebhookDelivery,
        target_url: str,
        secret: str,
    ) -> bool:
        """Attempt to deliver a webhook."""
        payload = delivery.payload
        signature = self._sign_payload(payload, secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-ID": str(delivery.id),
            "X-Event-Type": delivery.event_type,
            "User-Agent": "GestiqCloud-Webhooks/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    target_url,
                    json=payload,
                    headers=headers,
                )

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:4096]

            if 200 <= response.status_code < 300:
                delivery.completed_at = datetime.utcnow()
                logger.info(f"Webhook delivered successfully: {delivery.id} → {target_url}")
                return True
            else:
                logger.warning(
                    f"Webhook delivery failed: {delivery.id} → {target_url} (status: {response.status_code})"
                )
                return False

        except TimeoutError:
            delivery.error_message = "Timeout"
            logger.warning(f"Webhook timeout: {delivery.id} → {target_url}")
            return False

        except httpx.ConnectError as e:
            delivery.error_message = f"Connection error: {str(e)}"
            logger.warning(f"Webhook connection error: {delivery.id} → {target_url}")
            return False

        except Exception as e:
            delivery.error_message = str(e)[:1024]
            logger.exception(f"Webhook delivery error: {delivery.id} → {target_url}")
            return False

    def calculate_next_retry(self, attempt_number: int) -> datetime | None:
        """Calculate when to retry based on exponential backoff."""
        if attempt_number >= self.MAX_ATTEMPTS:
            return None

        delay_seconds = self.BASE_DELAY_SECONDS * (self.BACKOFF_MULTIPLIER ** (attempt_number - 1))
        return datetime.utcnow() + timedelta(seconds=delay_seconds)
