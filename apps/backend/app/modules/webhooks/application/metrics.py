"""
Prometheus metrics for webhook module

Tracks webhook delivery performance, retry counts, and failure rates.
"""

import logging

try:
    from prometheus_client import Counter, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Dummy implementations if prometheus_client not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self


logger = logging.getLogger(__name__)


class WebhookMetrics:
    """Webhook delivery metrics collection"""

    def __init__(self):
        """Initialize metrics"""
        self._initialized = False
        self.webhook_deliveries_total = None
        self.webhook_delivery_duration_seconds = None
        self.webhook_retries_total = None
        self.webhook_delivery_http_status = None
        self._ensure_metrics()

    def _ensure_metrics(self):
        """Ensure metrics are initialized"""
        if self._initialized or not PROMETHEUS_AVAILABLE:
            return

        try:
            # Total webhook deliveries counter
            self.webhook_deliveries_total = Counter(
                "webhook_deliveries_total",
                "Total webhook deliveries by event and status",
                ["event", "tenant_id", "status"],
            )

            # Webhook delivery duration histogram
            self.webhook_delivery_duration_seconds = Histogram(
                "webhook_delivery_duration_seconds",
                "Webhook delivery duration in seconds",
                ["event", "tenant_id"],
                buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            )

            # Webhook retries counter
            self.webhook_retries_total = Counter(
                "webhook_retries_total",
                "Total webhook retry attempts",
                ["event", "tenant_id", "reason"],
            )

            # HTTP status codes counter
            self.webhook_delivery_http_status = Counter(
                "webhook_delivery_http_status",
                "HTTP status codes from webhook deliveries",
                ["event", "status_code"],
            )

            self._initialized = True
            logger.info("Webhook metrics initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing webhook metrics: {e}")

    def record_delivery_attempt(
        self,
        event: str,
        tenant_id: str,
        status: str,
        http_status: int | None = None,
    ):
        """
        Record a webhook delivery attempt

        Args:
            event: Event name (e.g., "invoice.created")
            tenant_id: Tenant ID
            status: Delivery status (delivered, failed, retrying, abandoned)
            http_status: HTTP status code if available
        """
        if not PROMETHEUS_AVAILABLE or not self._initialized:
            return

        try:
            # Record delivery status
            if self.webhook_deliveries_total:
                self.webhook_deliveries_total.labels(
                    event=event,
                    tenant_id=tenant_id,
                    status=status,
                ).inc()

            # Record HTTP status if available
            if http_status and self.webhook_delivery_http_status:
                self.webhook_delivery_http_status.labels(
                    event=event,
                    status_code=str(http_status),
                ).inc()

        except Exception as e:
            logger.error(f"Error recording delivery attempt metric: {e}")

    def record_delivery_duration(
        self,
        event: str,
        tenant_id: str,
        duration_seconds: float,
    ):
        """
        Record webhook delivery duration

        Args:
            event: Event name
            tenant_id: Tenant ID
            duration_seconds: Duration in seconds
        """
        if not PROMETHEUS_AVAILABLE or not self._initialized:
            return

        try:
            if self.webhook_delivery_duration_seconds:
                self.webhook_delivery_duration_seconds.labels(
                    event=event,
                    tenant_id=tenant_id,
                ).observe(duration_seconds)

        except Exception as e:
            logger.error(f"Error recording delivery duration metric: {e}")

    def record_retry(
        self,
        event: str,
        tenant_id: str,
        reason: str,
    ):
        """
        Record a webhook retry attempt

        Args:
            event: Event name
            tenant_id: Tenant ID
            reason: Retry reason (timeout, 5xx, connection_error, etc.)
        """
        if not PROMETHEUS_AVAILABLE or not self._initialized:
            return

        try:
            if self.webhook_retries_total:
                self.webhook_retries_total.labels(
                    event=event,
                    tenant_id=tenant_id,
                    reason=reason,
                ).inc()

        except Exception as e:
            logger.error(f"Error recording retry metric: {e}")


# Global metrics instance
_webhook_metrics: WebhookMetrics | None = None


def get_webhook_metrics() -> WebhookMetrics:
    """Get or initialize global webhook metrics instance"""
    global _webhook_metrics
    if _webhook_metrics is None:
        _webhook_metrics = WebhookMetrics()
    return _webhook_metrics


def record_delivery_attempt(
    event: str,
    tenant_id: str,
    status: str,
    http_status: int | None = None,
):
    """Convenience function to record delivery attempt"""
    get_webhook_metrics().record_delivery_attempt(
        event=event,
        tenant_id=tenant_id,
        status=status,
        http_status=http_status,
    )


def record_delivery_duration(
    event: str,
    tenant_id: str,
    duration_seconds: float,
):
    """Convenience function to record delivery duration"""
    get_webhook_metrics().record_delivery_duration(
        event=event,
        tenant_id=tenant_id,
        duration_seconds=duration_seconds,
    )


def record_retry(
    event: str,
    tenant_id: str,
    reason: str,
):
    """Convenience function to record retry attempt"""
    get_webhook_metrics().record_retry(
        event=event,
        tenant_id=tenant_id,
        reason=reason,
    )
