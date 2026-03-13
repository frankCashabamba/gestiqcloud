from __future__ import annotations

from enum import Enum


class PendingStatus(str, Enum):
    PENDING = "pending"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"


class ExpenseStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentLinkStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
