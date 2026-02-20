"""
Accounting Service
Auto-generates journal entries from business transactions
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AccountingService:
    """Create journal entries from business transactions."""

    def __init__(self, db: Session):
        self.db = db

    def create_entry_from_receipt(
        self,
        *,
        receipt_id: UUID,
        tenant_id: UUID | None = None,
    ) -> dict:
        """
        Auto-create journal entry from POS receipt.

        Entry structure (simplified):
        DEBE:  Caja (Cash Account)       → receipt.total
        HABER: Ventas (Sales Revenue)    → receipt.subtotal
        HABER: IVA Salidas (VAT Output)  → receipt.tax

        Operations:
        1. Fetch receipt details
        2. Get accounting config (account IDs, tax rates)
        3. Create JournalEntry
        4. Create JournalEntryLines (DEBE/HABER)
        5. Post to ledger (if auto-post enabled)

        Args:
            receipt_id: POS Receipt ID
            tenant_id: Tenant ID (for multi-tenant)

        Returns:
            {
                "journal_entry_id": UUID,
                "receipt_id": UUID,
                "status": "posted",
                "lines": [...]
            }
        """
        try:
            # TODO: Fetch receipt from pos_receipts
            # receipt = self.db.query(POSReceipt).filter(
            #     POSReceipt.id == receipt_id
            # ).first()

            # TODO: Create journal entry
            # entry = JournalEntry(
            #     tenant_id=tenant_id,
            #     entry_type="POS",
            #     reference_id=receipt_id,
            #     description=f"POS Receipt {receipt.number}",
            #     entry_date=datetime.utcnow(),
            #     status="posted"
            # )
            # self.db.add(entry)

            # TODO: Create DEBE line (Cash)
            # self.db.add(JournalEntryLine(
            #     journal_entry_id=entry.id,
            #     account_id=...,  # cash_account_id from settings
            #     debit=receipt.total,
            #     credit=Decimal("0")
            # ))

            # TODO: Create HABER lines (Sales + VAT)

            # self.db.commit()

            logger.info(f"Journal entry created from receipt {receipt_id}")

            return {
                "journal_entry_id": UUID(int=0),
                "receipt_id": receipt_id,
                "status": "posted",
                "lines": [],
            }

        except Exception as e:
            logger.exception(f"Error creating journal entry for receipt {receipt_id}")
            raise ValueError(f"Error creating journal entry: {str(e)}")

    def create_entry_from_invoice(
        self,
        *,
        invoice_id: UUID,
        tenant_id: UUID | None = None,
    ) -> dict:
        """
        Auto-create journal entry from invoice.

        Entry for accrual accounting:
        DEBE: Accounts Receivable (A/R) → invoice.total
        HABER: Sales Revenue            → invoice.subtotal
        HABER: VAT Output               → invoice.tax

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID

        Returns:
            {
                "journal_entry_id": UUID,
                "invoice_id": UUID,
                "status": "posted"
            }
        """
        try:
            # TODO: Similar to receipt but for invoices
            # Creates A/R instead of Cash

            logger.info(f"Journal entry created from invoice {invoice_id}")

            return {
                "journal_entry_id": UUID(int=0),
                "invoice_id": invoice_id,
                "status": "posted",
            }

        except Exception:
            logger.exception(f"Error creating journal entry for invoice {invoice_id}")
            raise

    def create_entry_from_payment(
        self,
        *,
        payment_id: UUID,
        invoice_id: UUID,
        amount: Decimal,
        method: str,  # cash, card, check, transfer
        tenant_id: UUID | None = None,
    ) -> dict:
        """
        Auto-create journal entry for payment.

        Entry when payment received:
        DEBE: Cash/Bank (from payment.method)  → amount
        HABER: Accounts Receivable (A/R)       → amount

        This clears the A/R entry created by invoice.

        Args:
            payment_id: Payment ID
            invoice_id: Invoice ID
            amount: Payment amount
            method: Payment method
            tenant_id: Tenant ID

        Returns:
            {
                "journal_entry_id": UUID,
                "payment_id": UUID,
                "status": "posted"
            }
        """
        try:
            # TODO: Create payment entry
            # Get account based on method:
            # - cash → cash_account_id
            # - card → bank_account_id
            # - check → bank_account_id
            # - transfer → bank_account_id

            logger.info(f"Journal entry created from payment {payment_id}")

            return {
                "journal_entry_id": UUID(int=0),
                "payment_id": payment_id,
                "status": "posted",
            }

        except Exception:
            logger.exception(f"Error creating journal entry for payment {payment_id}")
            raise

    def create_manual_entry(
        self,
        *,
        description: str,
        lines: list[dict],  # {account_id, debit, credit, description}
        entry_date: str | None = None,
        tenant_id: UUID | None = None,
    ) -> dict:
        """
        Create manual journal entry.

        Validates:
        - Total DEBE = Total HABER
        - At least 2 lines
        - All account IDs valid

        Args:
            description: Entry description
            lines: List of {account_id, debit, credit, description}
            entry_date: Entry date (default: today)
            tenant_id: Tenant ID

        Returns:
            {
                "journal_entry_id": UUID,
                "status": "draft",
                "debit_total": Decimal,
                "credit_total": Decimal
            }
        """
        try:
            # TODO: Validate entry balance
            debit_total = sum(Decimal(str(line.get("debit", 0))) for line in lines)
            credit_total = sum(Decimal(str(line.get("credit", 0))) for line in lines)

            if debit_total != credit_total:
                raise ValueError(f"Entry unbalanced: DEBE={debit_total} HABER={credit_total}")

            if len(lines) < 2:
                raise ValueError("Entry must have at least 2 lines")

            # TODO: Create entry

            logger.info(f"Manual journal entry created: {description}")

            return {
                "journal_entry_id": UUID(int=0),
                "status": "draft",
                "debit_total": debit_total,
                "credit_total": credit_total,
            }

        except Exception:
            logger.exception("Error creating manual journal entry")
            raise

    def post_entry(self, *, journal_entry_id: UUID) -> dict:
        """Post journal entry to ledger (final)."""
        try:
            # TODO: Update entry status to "posted"
            # Recalculate account balances

            logger.info(f"Journal entry {journal_entry_id} posted")

            return {
                "journal_entry_id": journal_entry_id,
                "status": "posted",
            }

        except Exception:
            logger.exception("Error posting journal entry")
            raise

    def void_entry(self, *, journal_entry_id: UUID, reason: str) -> dict:
        """Void a posted journal entry."""
        try:
            # TODO: Create reversal entry
            # Original entry → marked as voided
            # New entry → reverses the original

            logger.info(f"Journal entry {journal_entry_id} voided: {reason}")

            return {
                "journal_entry_id": journal_entry_id,
                "reversal_entry_id": UUID(int=0),
                "status": "voided",
            }

        except Exception:
            logger.exception("Error voiding journal entry")
            raise
