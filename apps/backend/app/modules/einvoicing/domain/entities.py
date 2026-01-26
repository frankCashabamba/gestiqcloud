"""Domain entities for E-invoicing module"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID


class InvoiceStatus(str, Enum):
    """Invoice status enumeration"""
    DRAFT = "draft"
    EMITTED = "emitted"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    AUTHORIZED = "authorized"


class CertificateStatus(str, Enum):
    """Certificate status"""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


@dataclass
class EInvoiceDocument:
    """Electronic invoice document entity"""
    id: UUID
    invoice_id: UUID
    tenant_id: str
    document_number: str
    issue_date: datetime
    customer_ruc: str
    customer_name: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    status: InvoiceStatus
    authorization_code: Optional[str] = None
    cdr_number: Optional[str] = None
    emission_timestamp: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class DigitalCertificate:
    """Digital certificate for signing"""
    id: UUID
    tenant_id: str
    certificate_path: str
    private_key_path: str
    password: str  # Should be encrypted
    issuer: str
    subject: str
    valid_from: datetime
    valid_to: datetime
    status: CertificateStatus
    serial_number: str
    fingerprint: str
    created_at: datetime = None
    updated_at: datetime = None

    def is_valid(self) -> bool:
        """Check if certificate is valid and not expired"""
        now = datetime.now()
        return (
            self.status == CertificateStatus.VALID and
            self.valid_from <= now <= self.valid_to
        )

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class EInvoiceConfig:
    """E-invoicing configuration per tenant"""
    id: UUID
    tenant_id: str
    country_code: str
    api_type: str  # 'SRI' (Ecuador), 'SUNAT' (Peru), etc.
    base_url: str
    api_key: str  # Encrypted
    secret_key: Optional[str] = None
    environment: str = "production"  # or 'test'
    enabled: bool = True
    auto_send: bool = True
    auto_authorize: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class EInvoiceLineItem:
    """Line item for electronic invoice"""
    id: UUID
    einvoice_id: UUID
    product_id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal = Decimal("0")
    tax_percent: Decimal = Decimal("0")
    subtotal: Decimal = None
    tax_amount: Decimal = None
    total: Decimal = None

    def __post_init__(self):
        if self.subtotal is None:
            self.subtotal = self.quantity * self.unit_price * (1 - self.discount_percent / 100)
        if self.tax_amount is None:
            self.tax_amount = self.subtotal * (self.tax_percent / 100)
        if self.total is None:
            self.total = self.subtotal + self.tax_amount


@dataclass
class EInvoiceXML:
    """XML representation of e-invoice"""
    content: str
    signature: Optional[str] = None
    is_signed: bool = False
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
