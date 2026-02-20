"""Custom exceptions for webhooks module."""


class WebhookException(Exception):
    """Base exception for webhook errors."""

    pass


class WebhookNotFound(WebhookException):
    """Webhook subscription not found."""

    pass


class InvalidWebhookURL(WebhookException):
    """Invalid webhook URL provided."""

    pass


class DeliveryFailed(WebhookException):
    """Webhook delivery failed."""

    pass


class WebhookDisabled(WebhookException):
    """Webhook is disabled."""

    pass
