"""Custom exceptions for notifications module."""


class NotificationException(Exception):
    pass


class NotificationNotFound(NotificationException):
    pass


class InvalidChannel(NotificationException):
    pass


class TemplateNotFound(NotificationException):
    pass


class DeliveryFailed(NotificationException):
    pass
