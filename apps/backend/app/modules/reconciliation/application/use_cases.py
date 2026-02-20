"""Business logic / use cases for reconciliation module."""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.modules.reconciliation.domain.exceptions import (
    AlreadyReconciled,
    LineNotFound,
    MatchingFailed,
    StatementNotFound,
)
from app.modules.reconciliation.domain.models import (
    ReconciliationBankStatement as BankStatement,
    ReconciliationStatementLine as StatementLine,
)
from app.modules.reconciliation.infrastructure.reconciliation_service import (
    ReconciliationService,
)

logger = logging.getLogger(__name__)


class ImportStatementUseCase:
    """Import a bank statement with its transaction lines."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        bank_name: str,
        account_number: str,
        statement_date,
        transactions: list,
        db_session: Session,
    ) -> BankStatement:
        statement = BankStatement(
            tenant_id=tenant_id,
            bank_name=bank_name,
            account_number=account_number,
            statement_date=statement_date,
            import_format="manual",
            status="imported",
            total_transactions=len(transactions),
            matched_count=0,
            unmatched_count=len(transactions),
        )
        db_session.add(statement)
        db_session.flush()

        for txn in transactions:
            line = StatementLine(
                statement_id=statement.id,
                tenant_id=tenant_id,
                transaction_date=txn.transaction_date,
                description=txn.description,
                reference=txn.reference,
                amount=txn.amount,
                transaction_type=txn.transaction_type,
                match_status="unmatched",
            )
            db_session.add(line)

        db_session.commit()
        db_session.refresh(statement)

        logger.info(
            f"Imported statement {statement.id} with {len(transactions)} transactions"
        )
        return statement


class ListStatementsUseCase:
    """List bank statements for a tenant (paginated)."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
        db_session: Session,
    ) -> Tuple[List[BankStatement], int]:
        query = db_session.query(BankStatement).filter(
            BankStatement.tenant_id == tenant_id
        ).order_by(BankStatement.created_at.desc())

        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total


class GetStatementDetailUseCase:
    """Get a statement with its lines."""

    def execute(
        self,
        *,
        statement_id: UUID,
        tenant_id: UUID,
        db_session: Session,
    ) -> BankStatement:
        statement = db_session.query(BankStatement).filter(
            BankStatement.id == statement_id,
            BankStatement.tenant_id == tenant_id,
        ).first()

        if not statement:
            raise StatementNotFound(f"Statement {statement_id} not found")

        return statement


class AutoMatchUseCase:
    """Auto-match unmatched statement lines against invoices."""

    def execute(
        self,
        *,
        statement_id: UUID,
        tenant_id: UUID,
        db_session: Session,
    ) -> BankStatement:
        statement = db_session.query(BankStatement).filter(
            BankStatement.id == statement_id,
            BankStatement.tenant_id == tenant_id,
        ).first()

        if not statement:
            raise StatementNotFound(f"Statement {statement_id} not found")

        unmatched_lines = db_session.query(StatementLine).filter(
            StatementLine.statement_id == statement_id,
            StatementLine.match_status == "unmatched",
        ).all()

        matched = 0

        for line in unmatched_lines:
            # Try match by reference first
            if line.reference:
                invoice = db_session.execute(
                    text(
                        """
                        SELECT id, total FROM invoices
                        WHERE tenant_id = :tenant_id
                        AND (numero = :reference
                             OR metadata::jsonb->>'reference' = :reference)
                        LIMIT 1
                        """
                    ),
                    {"tenant_id": str(tenant_id), "reference": line.reference},
                ).first()

                if invoice:
                    line.matched_invoice_id = invoice[0]
                    line.match_status = "auto_matched"
                    line.match_confidence = Decimal("95.00")
                    matched += 1
                    continue

            # Try match by amount + date proximity (±3 days)
            invoice = db_session.execute(
                text(
                    """
                    SELECT id, total FROM invoices
                    WHERE tenant_id = :tenant_id
                    AND ABS(total - :amount) < 0.01
                    AND estado NOT IN ('cancelled', 'draft', 'paid')
                    AND ABS(fecha_emision - :txn_date) <= 3
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": str(tenant_id),
                    "amount": float(line.amount),
                    "txn_date": line.transaction_date,
                },
            ).first()

            if invoice:
                line.matched_invoice_id = invoice[0]
                line.match_status = "auto_matched"
                line.match_confidence = Decimal("75.00")
                matched += 1

        statement.matched_count = (
            db_session.query(StatementLine)
            .filter(
                StatementLine.statement_id == statement_id,
                StatementLine.match_status != "unmatched",
            )
            .count()
        )
        statement.unmatched_count = statement.total_transactions - statement.matched_count

        if statement.unmatched_count == 0:
            statement.status = "reconciled"
        elif statement.matched_count > 0:
            statement.status = "partial"
        else:
            statement.status = "imported"

        db_session.commit()
        db_session.refresh(statement)

        logger.info(
            f"Auto-match on statement {statement_id}: {matched} new matches"
        )
        return statement


class ManualMatchUseCase:
    """Manually link a statement line to an invoice."""

    def execute(
        self,
        *,
        line_id: UUID,
        invoice_id: UUID,
        tenant_id: UUID,
        db_session: Session,
    ) -> StatementLine:
        line = db_session.query(StatementLine).filter(
            StatementLine.id == line_id,
            StatementLine.tenant_id == tenant_id,
        ).first()

        if not line:
            raise LineNotFound(f"Statement line {line_id} not found")

        if line.match_status != "unmatched":
            raise AlreadyReconciled(
                f"Line {line_id} is already matched ({line.match_status})"
            )

        # Verify invoice exists for this tenant
        invoice = db_session.execute(
            text(
                """
                SELECT id FROM invoices
                WHERE id = :invoice_id AND tenant_id = :tenant_id
                """
            ),
            {"invoice_id": str(invoice_id), "tenant_id": str(tenant_id)},
        ).first()

        if not invoice:
            raise LineNotFound(f"Invoice {invoice_id} not found")

        line.matched_invoice_id = invoice_id
        line.match_status = "manual_matched"
        line.match_confidence = Decimal("100.00")

        # Update statement counts
        statement = db_session.query(BankStatement).filter(
            BankStatement.id == line.statement_id,
        ).first()

        if statement:
            statement.matched_count = (
                db_session.query(StatementLine)
                .filter(
                    StatementLine.statement_id == statement.id,
                    StatementLine.match_status != "unmatched",
                )
                .count()
            ) + 1  # include current line being matched
            statement.unmatched_count = (
                statement.total_transactions - statement.matched_count
            )

            if statement.unmatched_count == 0:
                statement.status = "reconciled"
            else:
                statement.status = "partial"

        db_session.commit()
        db_session.refresh(line)

        logger.info(f"Manual match: line {line_id} → invoice {invoice_id}")
        return line


class GetReconciliationSummaryUseCase:
    """Get aggregate reconciliation statistics for a tenant."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        db_session: Session,
    ) -> dict:
        total_statements = db_session.query(BankStatement).filter(
            BankStatement.tenant_id == tenant_id,
        ).count()

        total_lines = db_session.query(StatementLine).filter(
            StatementLine.tenant_id == tenant_id,
        ).count()

        matched = db_session.query(StatementLine).filter(
            StatementLine.tenant_id == tenant_id,
            StatementLine.match_status != "unmatched",
        ).count()

        unmatched = total_lines - matched

        auto_matched = db_session.query(StatementLine).filter(
            StatementLine.tenant_id == tenant_id,
            StatementLine.match_status == "auto_matched",
        ).count()

        manual_matched = db_session.query(StatementLine).filter(
            StatementLine.tenant_id == tenant_id,
            StatementLine.match_status == "manual_matched",
        ).count()

        return {
            "total_statements": total_statements,
            "total_lines": total_lines,
            "matched": matched,
            "unmatched": unmatched,
            "auto_matched": auto_matched,
            "manual_matched": manual_matched,
        }


class ReconcilePaymentUseCase:
    """Reconcile a payment against an invoice using ReconciliationService."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        invoice_id: UUID,
        payment_amount: Decimal,
        payment_date,
        payment_reference: str,
        payment_method: str = "bank_transfer",
        notes: str | None = None,
        db_session: Session,
    ) -> dict:
        service = ReconciliationService(db_session)
        return service.reconcile_payment(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            payment_amount=payment_amount,
            payment_date=payment_date,
            payment_reference=payment_reference,
            payment_method=payment_method,
            notes=notes,
        )


class GetPendingReconciliationsUseCase:
    """Get all invoices pending reconciliation using ReconciliationService."""

    def execute(
        self,
        *,
        tenant_id: UUID,
        db_session: Session,
    ) -> dict:
        service = ReconciliationService(db_session)
        return service.get_pending_reconciliations(tenant_id=tenant_id)
