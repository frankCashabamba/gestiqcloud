from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class EinvoicingSendRequest(BaseModel):
    invoice_id: UUID = Field(..., description="ID of the invoice to send for e-invoicing.")
    country: str = Field(..., min_length=2, max_length=2, description="Country code (e.g., 'ES' for Spain, 'EC' for Ecuador).")

class EinvoicingStatusResponse(BaseModel):
    invoice_id: UUID
    status: str = Field(..., description="Current status of the e-invoice submission (e.g., 'pending', 'authorized', 'rejected').")
    clave_acceso: Optional[str] = Field(None, description="Access key for the e-invoice (e.g., SRI clave de acceso).")
    error_message: Optional[str] = Field(None, description="Error message if the submission failed.")
    submitted_at: Optional[datetime] = Field(None, description="Timestamp when the e-invoice was submitted.")
    created_at: datetime = Field(..., description="Timestamp when the e-invoice record was created.")
