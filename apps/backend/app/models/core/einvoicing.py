"""
E-invoicing models for SRI (Ecuador) and SII (Spain)
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, ForeignKey, Text, TIMESTAMP, Enum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class EinvoicingCredentials(Base):
    """E-invoicing credentials per tenant and country"""
    __tablename__ = "einvoicing_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False)  # 'EC' or 'ES'

    # EC (SRI) fields
    sri_cert_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sri_key_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sri_env: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'staging' or 'production'

    # ES (SII) fields
    sii_agency: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # e.g., 'AEAT'
    sii_cert_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sii_key_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")


# Enum types (matching database enums)
sri_status_enum = Enum('PENDING', 'SENT', 'RECEIVED', 'AUTHORIZED', 'REJECTED', 'ERROR', name='sri_status')
sii_batch_status_enum = Enum('PENDING', 'SENT', 'ACCEPTED', 'PARTIAL', 'REJECTED', 'ERROR', name='sii_batch_status')
sii_item_status_enum = Enum('PENDING', 'SENT', 'ACCEPTED', 'REJECTED', 'ERROR', name='sii_item_status')


class SRISubmission(Base):
    """SRI submission records for Ecuador e-invoicing"""
    __tablename__ = "sri_submissions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(sri_status_enum, nullable=False, default='PENDING')

    error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    receipt_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authorization_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # XML payload
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # XML response

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")


class SIIBatch(Base):
    """SII batch records for Spain e-invoicing"""
    __tablename__ = "sii_batches"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYYQn or YYYYMM
    status: Mapped[str] = mapped_column(sii_batch_status_enum, nullable=False, default='PENDING')

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")

    # Relationship to items
    items: Mapped[list["SIIBatchItem"]] = relationship(back_populates="batch")


class SIIBatchItem(Base):
    """Individual items within SII batches"""
    __tablename__ = "sii_batch_items"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sii_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(sii_item_status_enum, nullable=False, default='PENDING')

    error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default="now()")

    # Relationship to batch
    batch: Mapped["SIIBatch"] = relationship(back_populates="items")
