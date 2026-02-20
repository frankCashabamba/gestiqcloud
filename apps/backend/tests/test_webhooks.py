"""Webhook module tests"""

import json
from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.webhooks.domain.entities import (
    DeliveryStatus,
    WebhookEndpoint,
    WebhookEvent,
    WebhookEventType,
    WebhookPayload,
    WebhookStatus,
)
from app.modules.webhooks.infrastructure.webhook_dispatcher import WebhookDispatcher


class TestWebhookEndpoint:
    """Test webhook endpoint entity"""

    def test_create_webhook_endpoint(self):
        """Test creating webhook endpoint"""
        endpoint = WebhookEndpoint(
            id=uuid4(),
            tenant_id="tenant-1",
            url="https://example.com/webhook",
            events=[WebhookEventType.INVOICE_CREATED, WebhookEventType.INVOICE_SENT],
            secret="webhook-secret-key",
            status=WebhookStatus.ACTIVE,
            max_retries=5,
            timeout_seconds=30,
        )

        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.status == WebhookStatus.ACTIVE
        assert len(endpoint.events) == 2
        assert WebhookEventType.INVOICE_CREATED in endpoint.events

    def test_webhook_custom_headers(self):
        """Test webhook with custom headers"""
        endpoint = WebhookEndpoint(
            id=uuid4(),
            tenant_id="tenant-1",
            url="https://example.com/webhook",
            events=[WebhookEventType.INVOICE_CREATED],
            secret="webhook-secret-key",
            headers={"X-Custom-Header": "custom-value", "X-API-Key": "api-key"},
        )

        assert endpoint.headers["X-Custom-Header"] == "custom-value"
        assert endpoint.headers["X-API-Key"] == "api-key"


class TestWebhookEvent:
    """Test webhook event entity"""

    def test_create_webhook_event(self):
        """Test creating webhook event"""
        event = WebhookEvent(
            id=uuid4(),
            webhook_id=uuid4(),
            tenant_id="tenant-1",
            event_type=WebhookEventType.INVOICE_CREATED,
            resource_type="invoice",
            resource_id="inv-123",
            payload={
                "invoice_number": "001-001-000000001",
                "amount": "100.00",
                "customer": "Test Company",
            },
            timestamp=datetime.now(),
        )

        assert event.event_type == WebhookEventType.INVOICE_CREATED
        assert event.resource_type == "invoice"
        assert event.payload["invoice_number"] == "001-001-000000001"

    def test_webhook_event_payload(self):
        """Test webhook event payload structure"""
        event = WebhookEvent(
            id=uuid4(),
            webhook_id=uuid4(),
            tenant_id="tenant-1",
            event_type=WebhookEventType.PAYMENT_RECEIVED,
            resource_type="payment",
            resource_id="pay-456",
            payload={
                "invoice_id": "inv-123",
                "amount": "100.00",
                "method": "bank_transfer",
            },
            timestamp=datetime.now(),
        )

        assert event.payload["method"] == "bank_transfer"


class TestWebhookPayload:
    """Test webhook payload"""

    def test_payload_serialization(self):
        """Test payload to_dict serialization"""
        payload = WebhookPayload(
            id="evt-123",
            timestamp=datetime(2024, 2, 14, 10, 30, 0),
            event=WebhookEventType.INVOICE_CREATED,
            data={"amount": "100.00"},
            tenant_id="tenant-1",
            resource_type="invoice",
            resource_id="inv-123",
        )

        payload_dict = payload.to_dict()
        assert payload_dict["id"] == "evt-123"
        assert payload_dict["event"] == "invoice.created"
        assert payload_dict["data"]["amount"] == "100.00"
        assert isinstance(payload_dict["timestamp"], str)

    def test_payload_json_serialization(self):
        """Test payload can be JSON serialized"""
        payload = WebhookPayload(
            id="evt-456",
            timestamp=datetime.now(),
            event=WebhookEventType.PAYMENT_RECEIVED,
            data={"amount": 500.50, "currency": "USD"},
            tenant_id="tenant-2",
            resource_type="payment",
            resource_id="pay-789",
        )

        payload_dict = payload.to_dict()
        json_str = json.dumps(payload_dict)
        assert isinstance(json_str, str)

        # Verify round-trip
        restored = json.loads(json_str)
        assert restored["event"] == "payment.received"


class TestWebhookDispatcher:
    """Test webhook dispatcher"""

    def test_signature_generation(self):
        """Test HMAC signature generation"""
        dispatcher = WebhookDispatcher(None)
        secret = "test-secret"
        payload = {"key": "value", "amount": 100}

        signature = dispatcher._generate_signature(secret, payload)
        assert isinstance(signature, str)
        assert len(signature) > 0
        assert signature.startswith("sha256=")

    def test_signature_verification(self):
        """Test signature verification"""
        secret = "test-secret"
        payload = {"key": "value", "amount": 100}

        signature = WebhookDispatcher(None)._generate_signature(secret, payload)
        is_valid = WebhookDispatcher.verify_signature(secret, payload, signature)

        assert is_valid is True

    def test_invalid_signature(self):
        """Test invalid signature detection"""
        secret = "test-secret"
        payload = {"key": "value", "amount": 100}

        # Generate signature with different secret
        wrong_signature = WebhookDispatcher(None)._generate_signature("wrong-secret", payload)
        is_valid = WebhookDispatcher.verify_signature(secret, payload, wrong_signature)

        assert is_valid is False

    def test_signature_verification_tampered_payload(self):
        """Test tampered payload detection"""
        secret = "test-secret"
        payload = {"key": "value", "amount": 100}

        signature = WebhookDispatcher(None)._generate_signature(secret, payload)

        # Tamper with payload
        tampered_payload = {"key": "value", "amount": 200}
        is_valid = WebhookDispatcher.verify_signature(secret, tampered_payload, signature)

        assert is_valid is False

    def test_signature_payload_ordering(self):
        """Test that signature is consistent regardless of key order"""
        secret = "test-secret"
        payload1 = {"a": 1, "b": 2, "c": 3}
        payload2 = {"c": 3, "a": 1, "b": 2}

        sig1 = WebhookDispatcher(None)._generate_signature(secret, payload1)
        sig2 = WebhookDispatcher(None)._generate_signature(secret, payload2)

        # Should be identical despite different order
        assert sig1 == sig2


class TestWebhookValidation:
    """Test webhook input validation"""

    def test_subscription_create_request_validation(self):
        """Test subscription create request validation"""
        from app.modules.webhooks.interface.http.tenant import WebhookSubscriptionCreate

        # Valid request
        valid = WebhookSubscriptionCreate(
            event="invoice.created",
            url="https://example.com/webhook",
            secret="my-secret-key-12345",
        )
        assert valid.event == "invoice.created"
        assert valid.url == "https://example.com/webhook"

        # Invalid URL (not HTTPS)
        with pytest.raises(ValueError):
            WebhookSubscriptionCreate(
                event="invoice.created",
                url="http://example.com/webhook",
            )

        # Invalid secret (too short)
        with pytest.raises(ValueError):
            WebhookSubscriptionCreate(
                event="invoice.created",
                url="https://example.com/webhook",
                secret="short",
            )

        # Empty event
        with pytest.raises(ValueError):
            WebhookSubscriptionCreate(
                event="",
                url="https://example.com/webhook",
            )

    def test_delivery_enqueue_request_validation(self):
        """Test delivery enqueue request validation"""
        from app.modules.webhooks.interface.http.tenant import WebhookDeliveryEnqueue

        # Valid request
        valid = WebhookDeliveryEnqueue(
            event="invoice.created",
            payload={"invoice_id": "inv-123", "amount": 100.50},
        )
        assert valid.event == "invoice.created"
        assert valid.payload["amount"] == 100.50

        # Invalid payload (not JSON serializable - will fail at Pydantic level)
        # This is handled by Pydantic validation

    def test_event_name_normalization(self):
        """Test event name is normalized to lowercase"""
        from app.modules.webhooks.interface.http.tenant import WebhookSubscriptionCreate

        request = WebhookSubscriptionCreate(
            event="Invoice.Created",
            url="https://example.com/webhook",
            secret="my-secret-key-12345",
        )
        assert request.event == "invoice.created"


class TestWebhookIntegration:
    """Integration tests for webhooks"""

    @pytest.mark.asyncio
    async def test_dispatch_single_endpoint(self):
        """Test dispatching to single endpoint"""
        # Would require mocking httpx
        pass

    @pytest.mark.asyncio
    async def test_dispatch_multiple_endpoints(self):
        """Test dispatching to multiple endpoints"""
        # Would require mocking httpx
        pass

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test exponential backoff retry logic"""
        # Would require mocking httpx with failure responses
        pass

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling"""
        # Would require mocking httpx with timeout
        pass


class TestWebhookDeliveryStatus:
    """Test delivery status management"""

    def test_delivery_status_enum(self):
        """Test delivery status enum values"""
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.DELIVERED.value == "delivered"
        assert DeliveryStatus.FAILED.value == "failed"
        assert DeliveryStatus.RETRYING.value == "retrying"
        assert DeliveryStatus.ABANDONED.value == "abandoned"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
