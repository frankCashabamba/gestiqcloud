"""Custom exceptions for reconciliation module."""


class ReconciliationException(Exception):
    pass


class StatementNotFound(ReconciliationException):
    pass


class LineNotFound(ReconciliationException):
    pass


class AlreadyReconciled(ReconciliationException):
    pass


class ImportError(ReconciliationException):
    pass


class MatchingFailed(ReconciliationException):
    pass
