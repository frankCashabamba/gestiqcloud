"""Finance service - cash position management."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.finance.cash import CashPosition, CashProjection
from app.models.finance.payment import Payment


class CashPositionService:
    """Daily cash position management."""

    @staticmethod
    def calculate_position(
        db: Session,
        tenant_id: UUID,
        bank_account_id: UUID,
        position_date: date,
    ) -> CashPosition:
        """
        Calculate the cash position for a given date and account.

        Formula:
            closing_balance = opening_balance + inflows - outflows
        """
        # 1. Get opening balance (previous day's closing balance).
        previous = db.execute(
            select(CashPosition)
            .where(
                CashPosition.tenant_id == tenant_id,
                CashPosition.bank_account_id == bank_account_id,
                CashPosition.position_date < position_date,
            )
            .order_by(CashPosition.position_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        opening_balance = previous.closing_balance if previous else Decimal("0")

        # 2. Calculate the day's inflows and outflows from the Payment table.
        stmt = select(
            func.coalesce(
                func.sum(case((Payment.amount > 0, Payment.amount), else_=0)),
                Decimal("0"),
            ).label("inflows"),
            func.coalesce(
                func.sum(case((Payment.amount < 0, func.abs(Payment.amount)), else_=0)),
                Decimal("0"),
            ).label("outflows"),
        ).where(
            Payment.tenant_id == tenant_id,
            Payment.bank_account_id == bank_account_id,
            func.date(Payment.payment_date) == position_date,
            Payment.status == "CONFIRMED",
        )

        result = db.execute(stmt).one()
        inflows = result.inflows or Decimal("0")
        outflows = result.outflows or Decimal("0")

        # 3. Calculate closing balance.
        closing_balance = opening_balance + inflows - outflows

        # 4. Find or create the record.
        position = db.execute(
            select(CashPosition).where(
                CashPosition.tenant_id == tenant_id,
                CashPosition.bank_account_id == bank_account_id,
                CashPosition.position_date == position_date,
            )
        ).scalar_one_or_none()

        if not position:
            position = CashPosition(
                tenant_id=tenant_id,
                bank_account_id=bank_account_id,
                position_date=position_date,
            )
            db.add(position)

        position.opening_balance = opening_balance
        position.inflows = inflows
        position.outflows = outflows
        position.closing_balance = closing_balance

        db.flush()
        return position

    @staticmethod
    def create_projection(
        db: Session,
        tenant_id: UUID,
        bank_account_id: UUID,
        projection_days: int = 30,
    ) -> CashProjection:
        """
        Create a cash flow projection for the next N days.

        Base: current balance + confirmed payments in the next N days.
        """
        today = date.today()
        projection_date = today
        projection_end_date = date(
            today.year + (today.month + projection_days - 1) // 12,
            ((today.month + projection_days - 1) % 12) + 1,
            1,
        )

        # Get current balance.
        current_position = CashPositionService.calculate_position(
            db, tenant_id, bank_account_id, today
        )
        opening_balance = current_position.closing_balance

        # Project inflows and outflows.
        stmt = select(
            func.coalesce(
                func.sum(case((Payment.amount > 0, Payment.amount), else_=0)),
                Decimal("0"),
            ).label("proj_inflows"),
            func.coalesce(
                func.sum(case((Payment.amount < 0, func.abs(Payment.amount)), else_=0)),
                Decimal("0"),
            ).label("proj_outflows"),
        ).where(
            Payment.tenant_id == tenant_id,
            Payment.bank_account_id == bank_account_id,
            func.date(Payment.scheduled_date).between(today, projection_end_date),
            Payment.status.in_(["PENDING", "IN_PROGRESS"]),
        )

        result = db.execute(stmt).one()
        projected_inflows = result.proj_inflows or Decimal("0")
        projected_outflows = result.proj_outflows or Decimal("0")
        projected_balance = opening_balance + projected_inflows - projected_outflows

        # Create the projection record.
        projection = CashProjection(
            tenant_id=tenant_id,
            bank_account_id=bank_account_id,
            projection_date=projection_date,
            projection_end_date=projection_end_date,
            period_days=projection_days,
            opening_balance=opening_balance,
            projected_inflows=projected_inflows,
            projected_outflows=projected_outflows,
            projected_balance=projected_balance,
            scenario="BASE",
        )

        db.add(projection)
        db.flush()
        return projection

    @staticmethod
    def get_multi_day_positions(
        db: Session,
        tenant_id: UUID,
        bank_account_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[CashPosition]:
        """Get cash positions for a date range."""
        positions = (
            db.execute(
                select(CashPosition)
                .where(
                    CashPosition.tenant_id == tenant_id,
                    CashPosition.bank_account_id == bank_account_id,
                    CashPosition.position_date.between(start_date, end_date),
                )
                .order_by(CashPosition.position_date)
            )
            .scalars()
            .all()
        )

        return positions
