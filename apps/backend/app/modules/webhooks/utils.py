"""Webhook utilities for integration"""

import hashlib
import hmac
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class WebhookSignature:
    """Utilities for webhook signature generation and verification"""

    @staticmethod
    def sign(secret: str, payload: dict[str, Any]) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.

        Args:
            secret: Secret key for signing
            payload: Payload dictionary

        Returns:
            Signature in format "sha256=<hex>"
        """
        if not secret:
            raise ValueError("Secret cannot be empty")

        # Serialize payload deterministically
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        # Generate HMAC-SHA256
        signature = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return f"sha256={signature}"

    @staticmethod
    def verify(secret: str, payload: dict[str, Any], signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            secret: Secret key
            payload: Payload dictionary
            signature: Signature to verify (e.g., "sha256=abc123...")

        Returns:
            True if signature is valid, False otherwise
        """
        if not secret or not signature:
            return False

        try:
            # Generate expected signature
            expected_sig = WebhookSignature.sign(secret, payload)

            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_sig, signature)

        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    @staticmethod
    def verify_raw(secret: str, body_raw: bytes, signature: str) -> bool:
        """
        Verify webhook signature using raw request body.

        Use this when you have the raw HTTP body as received.

        Args:
            secret: Secret key
            body_raw: Raw request body as bytes
            signature: Signature to verify (e.g., "sha256=abc123...")

        Returns:
            True if signature is valid, False otherwise
        """
        if not secret or not signature:
            return False

        try:
            # Extract hex from signature string
            if signature.startswith("sha256="):
                expected_hex = signature[7:]
            else:
                expected_hex = signature

            # Generate HMAC-SHA256
            calculated_sig = hmac.new(
                secret.encode("utf-8"),
                body_raw,
                hashlib.sha256,
            ).hexdigest()

            # Use constant-time comparison
            return hmac.compare_digest(calculated_sig, expected_hex)

        except Exception as e:
            logger.error(f"Raw signature verification error: {e}")
            return False


class WebhookValidator:
    """Webhook input validation utilities"""

    @staticmethod
    def validate_url(url: str) -> tuple[bool, str | None]:
        """
        Validate webhook URL.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"

        url = url.strip()

        if len(url) > 2048:
            return False, "URL is too long (max 2048 characters)"

        if not url.startswith("https://"):
            return False, "URL must use HTTPS protocol"

        # Basic URL format check
        if not any(c in url for c in [".", "/"]):
            return False, "URL format is invalid"

        return True, None

    @staticmethod
    def validate_event(event: str) -> tuple[bool, str | None]:
        """
        Validate event name.

        Args:
            event: Event name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not event:
            return False, "Event cannot be empty"

        event = event.strip()

        if len(event) > 100:
            return False, "Event name is too long (max 100 characters)"

        if " " in event:
            return False, "Event name cannot contain spaces"

        # Must be in format: resource.action (e.g., invoice.created)
        if "." not in event:
            return False, "Event must be in format: resource.action (e.g., invoice.created)"

        return True, None

    @staticmethod
    def validate_secret(secret: str | None) -> tuple[bool, str | None]:
        """
        Validate webhook secret.

        Args:
            secret: Secret to validate (optional)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if secret is None:
            return True, None

        secret = secret.strip()

        if len(secret) < 8:
            return False, "Secret must be at least 8 characters"

        if len(secret) > 500:
            return False, "Secret is too long (max 500 characters)"

        return True, None

    @staticmethod
    def validate_payload(payload: Any) -> tuple[bool, str | None]:
        """
        Validate webhook payload.

        Args:
            payload: Payload to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if payload is None:
            return False, "Payload cannot be null"

        if not isinstance(payload, dict):
            return False, "Payload must be a dictionary"

        try:
            json.dumps(payload)
            return True, None
        except (TypeError, ValueError) as e:
            return False, f"Payload is not JSON serializable: {str(e)}"


class WebhookFormatter:
    """Webhook payload formatting utilities"""

    @staticmethod
    def format_event_payload(
        event: str,
        resource_type: str,
        resource_id: str,
        data: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Format a standard webhook payload.

        Args:
            event: Event name (e.g., "invoice.created")
            resource_type: Type of resource (e.g., "invoice")
            resource_id: ID of resource
            data: Event-specific data
            tenant_id: Tenant ID

        Returns:
            Formatted payload dictionary
        """
        from datetime import datetime

        return {
            "event": event,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "metadata": {
                "tenant_id": tenant_id,
                "source": "gestiqcloud",
                "version": "1.0",
            },
        }

    @staticmethod
    def mask_secret(secret: str | None) -> str | None:
        """
        Mask a secret for logging/display.

        Args:
            secret: Secret to mask

        Returns:
            Masked secret or None
        """
        if secret:
            return "***"
        return None


class WebhookRetry:
    """Webhook retry logic utilities"""

    @staticmethod
    def get_retry_delay(attempt: int, base: int = 2) -> int:
        """
        Calculate retry delay using exponential backoff.

        Args:
            attempt: Attempt number (1-indexed)
            base: Base for exponential backoff (default: 2)

        Returns:
            Delay in seconds
        """
        return base ** (attempt - 1)

    @staticmethod
    def should_retry(status_code: int, attempt: int, max_attempts: int = 3) -> bool:
        """
        Determine if a delivery should be retried.

        Args:
            status_code: HTTP status code from delivery attempt
            attempt: Current attempt number (1-indexed)
            max_attempts: Maximum attempts allowed

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= max_attempts:
            return False

        # Retry on 5xx errors and timeout-like conditions
        if status_code >= 500:
            return True

        # Don't retry on 4xx errors (client errors)
        if 400 <= status_code < 500:
            return False

        # Retry on 3xx redirects and unknown statuses
        return True

    @staticmethod
    def get_retry_strategy(max_attempts: int = 3) -> dict[int, int]:
        """
        Get retry strategy with delays.

        Args:
            max_attempts: Maximum attempts

        Returns:
            Dictionary mapping attempt number to delay in seconds
        """
        return {
            attempt: WebhookRetry.get_retry_delay(attempt) for attempt in range(1, max_attempts + 1)
        }


# Example usage and integration points
if __name__ == "__main__":
    # Example: Sign a payload
    payload = {
        "invoice_id": "inv-123",
        "amount": 1500.00,
        "currency": "USD",
    }
    secret = "my-webhook-secret-key"

    signature = WebhookSignature.sign(secret, payload)
    print(f"Signature: {signature}")

    # Example: Verify signature
    is_valid = WebhookSignature.verify(secret, payload, signature)
    print(f"Signature valid: {is_valid}")

    # Example: Validate inputs
    url_valid, url_error = WebhookValidator.validate_url("https://example.com/webhook")
    print(f"URL valid: {url_valid}, Error: {url_error}")

    event_valid, event_error = WebhookValidator.validate_event("invoice.created")
    print(f"Event valid: {event_valid}, Error: {event_error}")

    # Example: Format payload
    formatted = WebhookFormatter.format_event_payload(
        event="invoice.created",
        resource_type="invoice",
        resource_id="inv-123",
        data={"amount": 1500.00},
        tenant_id="tenant-1",
    )
    print(f"Formatted payload: {json.dumps(formatted, indent=2)}")

    # Example: Retry strategy
    retry_strategy = WebhookRetry.get_retry_strategy(max_attempts=4)
    print(f"Retry strategy: {retry_strategy}")
