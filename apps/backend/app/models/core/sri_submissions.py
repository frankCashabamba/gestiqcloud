"""
Compatibility shim for tests expecting SRISubmission at
app.models.core.sri_submissions.

This defines a lightweight class that matches what tests instantiate
and what the use_case reads (duck-typed attributes). It avoids coupling
unit tests to SQLAlchemy constructors while remaining compatible with
the application code that only reads attributes.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime


class SRISubmission:  # noqa: D401 - simple data holder
    """Lightweight submission record used in tests."""

    def __init__(
        self,
        *,
        invoice_id: UUID,
        tenant_id: UUID,
        status: str,
        clave_acceso: Optional[str] = None,
        error_message: Optional[str] = None,
        submitted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.invoice_id = invoice_id
        self.tenant_id = tenant_id
        self.status = status
        self.error_message = error_message
        # Tests may pass submitted_at/created_at; we keep both
        self.created_at = created_at or submitted_at or datetime.utcnow()
        self.submitted_at = submitted_at or self.created_at
        # Map both alias names so use_case can read receipt_number
        self.clave_acceso = clave_acceso
        self.receipt_number = clave_acceso

