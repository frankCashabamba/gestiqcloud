"""Webhook delivery tasks for Celery"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import requests
from celery import shared_task
from sqlalchemy import text

from app.config.database import SessionLocal
from app.modules.webhooks.application.metrics import (
    record_delivery_attempt,
    record_delivery_duration,
    record_retry,
)

logger = logging.getLogger(__name__)

# Configuration
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_MAX_RETRIES = 3
WEBHOOK_USER_AGENT = "GestiqCloud-Webhooks/1.0"


def _sign(secret: str, payload: dict[str, Any]) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        secret: Secret key for signing
        payload: Payload dictionary

    Returns:
        Hex-encoded signature
    """
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@shared_task(
    name="apps.backend.app.modules.webhooks.tasks.deliver",
    bind=True,
    max_retries=WEBHOOK_MAX_RETRIES,
    default_retry_delay=60,  # Retry after 60 seconds
)
def deliver(self, delivery_id: str) -> dict:
    """
    Deliver a webhook to its target URL.

    Args:
        delivery_id: UUID of the webhook delivery record

    Returns:
        Dictionary with delivery result
    """
    start_time = time.time()
    with SessionLocal() as db:
        # Fetch delivery record
        delivery_row = db.execute(
            text("""
                SELECT
                    id::text, event, payload, target_url, secret, status, attempts, tenant_id::text
                FROM webhook_deliveries
                WHERE id = CAST(:id AS uuid)
                LIMIT 1
                """),
            {"id": delivery_id},
        ).first()

        if not delivery_row:
            logger.error(f"Delivery not found: {delivery_id}")
            return {"ok": False, "error": "delivery_not_found"}

        did, event, payload, url, secret, status, attempts, tenant_id = delivery_row

        # Don't retry if already delivered
        if status == "DELIVERED":
            logger.info(f"Delivery already completed: {did}")
            return {"ok": True, "already_delivered": True}

        # Parse payload if it's a string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse payload JSON: {e}")
                _update_delivery_status(db, did, "FAILED", str(e), attempts + 1)
                record_delivery_attempt(event, tenant_id, "failed")
                return {"ok": False, "error": "invalid_payload_json"}

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Event": str(event),
            "User-Agent": WEBHOOK_USER_AGENT,
        }

        # Add signature if secret is present
        if secret:
            headers["X-Signature"] = _sign(secret, payload)

        logger.info(
            f"Attempting webhook delivery {attempts + 1}/{WEBHOOK_MAX_RETRIES + 1}: "
            f"{event} to {url}"
        )

        try:
            # Update status to SENDING
            _update_delivery_status(db, did, "SENDING", None, attempts)

            # Send request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT_SECONDS,
            )

            # Record duration
            duration = time.time() - start_time
            record_delivery_duration(event, tenant_id, duration)

            # Handle response
            if 200 <= response.status_code < 300:
                # Success
                logger.info(
                    f"Webhook delivered successfully: {did} " f"(HTTP {response.status_code})"
                )
                _update_delivery_status(db, did, "DELIVERED", None, attempts + 1)
                record_delivery_attempt(event, tenant_id, "delivered", response.status_code)
                return {"ok": True, "status_code": response.status_code}
            else:
                # HTTP error
                error_msg = f"HTTP {response.status_code}"
                logger.warning(f"Webhook delivery failed: {did} - {error_msg}")

                # Record HTTP status
                record_delivery_attempt(event, tenant_id, "failed", response.status_code)

                # Don't retry on 4xx errors (client errors)
                if 400 <= response.status_code < 500:
                    _update_delivery_status(db, did, "FAILED", error_msg, attempts + 1)
                    return {"ok": False, "status_code": response.status_code}

                # Retry on 5xx errors (server errors)
                _update_delivery_status(db, did, "PENDING", error_msg, attempts + 1)
                record_retry(event, tenant_id, "server_error")

                # Schedule retry
                raise self.retry(exc=Exception(error_msg))

        except requests.exceptions.Timeout:
            error_msg = f"Request timeout ({WEBHOOK_TIMEOUT_SECONDS}s)"
            logger.warning(f"Webhook delivery timeout: {did}")
            _update_delivery_status(db, did, "PENDING", error_msg, attempts + 1)
            record_retry(event, tenant_id, "timeout")
            raise self.retry(exc=Exception(error_msg))

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.warning(f"Webhook delivery connection error: {did} - {error_msg}")
            _update_delivery_status(db, did, "PENDING", error_msg, attempts + 1)
            record_retry(event, tenant_id, "connection_error")
            raise self.retry(exc=e)

        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"Webhook delivery request error: {did} - {error_msg}")
            _update_delivery_status(db, did, "FAILED", error_msg, attempts + 1)
            record_delivery_attempt(event, tenant_id, "failed")
            return {"ok": False, "error": error_msg}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error during webhook delivery: {did} - {error_msg}")
            _update_delivery_status(db, did, "FAILED", error_msg, attempts + 1)
            record_delivery_attempt(event, tenant_id, "failed")
            return {"ok": False, "error": error_msg}

    return {"ok": False, "error": "unknown_error"}


def _update_delivery_status(
    db, delivery_id: str, status: str, error: str | None, attempts: int
) -> None:
    """
    Update webhook delivery status in database.

    Args:
        db: Database session
        delivery_id: Delivery ID
        status: New status (SENDING, DELIVERED, FAILED, PENDING)
        error: Error message if any
        attempts: Number of attempts
    """
    try:
        update_query = """
            UPDATE webhook_deliveries
            SET status = :status, attempts = :attempts, updated_at = NOW()
        """
        params = {"delivery_id": delivery_id, "status": status, "attempts": attempts}

        if error:
            update_query += ", last_error = :error"
            params["error"] = error[:500]  # Limit error message length

        update_query += " WHERE id = CAST(:delivery_id AS uuid)"

        db.execute(text(update_query), params)
        db.commit()

    except Exception as e:
        logger.error(f"Failed to update delivery status: {e}")
        db.rollback()
