"""Payment reconciliation service"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Payment reconciliation and matching"""

    def __init__(self, db: Session):
        self.db = db

    def reconcile_payment(
        self,
        tenant_id: str | UUID,
        invoice_id: UUID,
        payment_amount: Decimal,
        payment_date: datetime,
        payment_reference: str,
        payment_method: str = "bank_transfer",
        notes: Optional[str] = None,
    ) -> dict:
        """
        Reconcile a payment against an invoice

        Args:
            tenant_id: Tenant ID
            invoice_id: Invoice ID
            payment_amount: Amount paid
            payment_date: Date of payment
            payment_reference: Payment reference/check number
            payment_method: Method of payment
            notes: Additional notes

        Returns:
            Reconciliation result with status
        """
        try:
            # Get invoice
            invoice = self.db.execute(
                text(
                    """
                    SELECT id, numero, total, estado, metadata
                    FROM invoices
                    WHERE id = :invoice_id AND tenant_id = :tenant_id
                """
                ),
                {"invoice_id": str(invoice_id), "tenant_id": str(tenant_id)},
            ).first()

            if not invoice:
                return {
                    "success": False,
                    "error": f"Invoice {invoice_id} not found for tenant {tenant_id}",
                }

            invoice_id_db, invoice_number, invoice_total, invoice_status, metadata = invoice

            # Check if already paid
            existing_payment = self.db.execute(
                text(
                    """
                    SELECT id, amount FROM payments
                    WHERE invoice_id = :invoice_id AND status = 'confirmed'
                    ORDER BY created_at DESC LIMIT 1
                """
                ),
                {"invoice_id": str(invoice_id)},
            ).first()

            if existing_payment:
                paid_amount = existing_payment[1]
                if Decimal(str(paid_amount)) >= Decimal(str(invoice_total)):
                    return {
                        "success": False,
                        "error": f"Invoice {invoice_number} is already fully paid",
                    }

            # Record payment
            payment_id = self.db.execute(
                text(
                    """
                    INSERT INTO payments (
                        id, invoice_id, tenant_id, amount, payment_date,
                        payment_reference, payment_method, status, created_at
                    ) VALUES (
                        :id, :invoice_id, :tenant_id, :amount, :payment_date,
                        :payment_reference, :payment_method, 'pending', NOW()
                    )
                    RETURNING id
                """
                ),
                {
                    "id": str(UUID()),
                    "invoice_id": str(invoice_id),
                    "tenant_id": str(tenant_id),
                    "amount": float(payment_amount),
                    "payment_date": payment_date,
                    "payment_reference": payment_reference,
                    "payment_method": payment_method,
                },
            ).scalar()

            # Calculate remaining balance
            total_paid = Decimal(str(existing_payment[1])) if existing_payment else Decimal("0")
            total_paid += payment_amount
            remaining_balance = Decimal(str(invoice_total)) - total_paid

            # Determine payment status
            if remaining_balance <= 0:
                payment_status = "completed"
                invoice_payment_status = "paid"
            else:
                payment_status = "partial"
                invoice_payment_status = "partial_paid"

            # Update payment status
            self.db.execute(
                text(
                    """
                    UPDATE payments
                    SET status = :status, confirmed_at = NOW()
                    WHERE id = :payment_id
                """
                ),
                {"status": payment_status, "payment_id": str(payment_id)},
            )

            # Update invoice status
            self.db.execute(
                text(
                    """
                    UPDATE invoices
                    SET estado = :status, updated_at = NOW()
                    WHERE id = :invoice_id
                """
                ),
                {"status": invoice_payment_status, "invoice_id": str(invoice_id)},
            )

            self.db.commit()

            logger.info(
                f"Payment reconciled: Invoice {invoice_number}, "
                f"Amount: ${payment_amount}, Remaining: ${remaining_balance}"
            )

            return {
                "success": True,
                "payment_id": str(payment_id),
                "invoice_number": invoice_number,
                "amount_paid": float(payment_amount),
                "remaining_balance": float(remaining_balance),
                "payment_status": payment_status,
                "invoice_status": invoice_payment_status,
            }

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def get_reconciliation_status(
        self, tenant_id: str | UUID, invoice_id: UUID
    ) -> dict:
        """Get current reconciliation status for an invoice"""
        try:
            result = self.db.execute(
                text(
                    """
                    SELECT
                        inv.numero,
                        inv.total,
                        inv.estado,
                        COALESCE(SUM(p.amount), 0) as total_paid,
                        COUNT(p.id) as payment_count
                    FROM invoices inv
                    LEFT JOIN payments p ON inv.id = p.invoice_id
                    WHERE inv.id = :invoice_id AND inv.tenant_id = :tenant_id
                    GROUP BY inv.id, inv.numero, inv.total, inv.estado
                """
                ),
                {"invoice_id": str(invoice_id), "tenant_id": str(tenant_id)},
            ).first()

            if not result:
                return {
                    "success": False,
                    "error": f"Invoice {invoice_id} not found",
                }

            invoice_number, total, status, total_paid, payment_count = result

            remaining = Decimal(str(total)) - Decimal(str(total_paid))

            return {
                "success": True,
                "invoice_number": invoice_number,
                "total_amount": float(total),
                "total_paid": float(total_paid),
                "remaining_balance": float(remaining),
                "payment_count": payment_count,
                "reconciliation_status": "paid"
                if remaining <= 0
                else "partial" if total_paid > 0 else "pending",
                "invoice_status": status,
            }

        except Exception as e:
            logger.error(f"Failed to get reconciliation status: {e}")
            return {"success": False, "error": str(e)}

    def match_payments(
        self,
        tenant_id: str | UUID,
        bank_statement: list[dict],
    ) -> dict:
        """
        Match bank statement payments to invoices

        Args:
            tenant_id: Tenant ID
            bank_statement: List of bank transactions

        Returns:
            Matching results
        """
        try:
            results = {
                "total_transactions": len(bank_statement),
                "matched": 0,
                "unmatched": 0,
                "matches": [],
                "unmatched_transactions": [],
            }

            for transaction in bank_statement:
                amount = Decimal(str(transaction.get("amount", 0)))
                reference = transaction.get("reference", "")
                date = transaction.get("date")

                # Try to match by reference first
                matched = self.db.execute(
                    text(
                        """
                        SELECT id, numero, total FROM invoices
                        WHERE tenant_id = :tenant_id
                        AND (numero = :reference OR metadata::jsonb->>'reference' = :reference)
                        LIMIT 1
                    """
                    ),
                    {"tenant_id": str(tenant_id), "reference": reference},
                ).first()

                if matched:
                    invoice_id, invoice_number, invoice_total = matched
                    results["matched"] += 1
                    results["matches"].append(
                        {
                            "invoice_id": str(invoice_id),
                            "invoice_number": invoice_number,
                            "transaction_amount": float(amount),
                            "invoice_amount": float(invoice_total),
                            "reference": reference,
                        }
                    )
                else:
                    results["unmatched"] += 1
                    results["unmatched_transactions"].append(transaction)

            return {"success": True, "results": results}

        except Exception as e:
            logger.error(f"Failed to match payments: {e}")
            return {"success": False, "error": str(e)}

    def get_pending_reconciliations(self, tenant_id: str | UUID) -> dict:
        """Get all invoices pending reconciliation"""
        try:
            pending = self.db.execute(
                text(
                    """
                    SELECT
                        inv.id,
                        inv.numero,
                        inv.total,
                        inv.estado,
                        inv.fecha_emision,
                        COALESCE(SUM(p.amount), 0) as paid_amount
                    FROM invoices inv
                    LEFT JOIN payments p ON inv.id = p.invoice_id
                    WHERE inv.tenant_id = :tenant_id
                    AND inv.estado NOT IN ('cancelled', 'draft')
                    GROUP BY inv.id
                    HAVING COALESCE(SUM(p.amount), 0) < inv.total
                    ORDER BY inv.fecha_emision ASC
                """
                ),
                {"tenant_id": str(tenant_id)},
            ).fetchall()

            items = []
            for row in pending:
                inv_id, number, total, status, date, paid = row
                items.append(
                    {
                        "invoice_id": str(inv_id),
                        "invoice_number": number,
                        "total": float(total),
                        "paid": float(paid),
                        "pending": float(Decimal(str(total)) - Decimal(str(paid))),
                        "status": status,
                        "issued_date": str(date),
                    }
                )

            return {
                "success": True,
                "count": len(items),
                "pending_invoices": items,
            }

        except Exception as e:
            logger.error(f"Failed to get pending reconciliations: {e}")
            return {"success": False, "error": str(e)}
