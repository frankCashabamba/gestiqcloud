"""Finance Service - Cash Position Management"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.finance.cash import CashPosition, CashProjection
from app.models.finance.payment import Payment


class CashPositionService:
    """Gestión de posiciones de caja diarias."""

    @staticmethod
    def calculate_position(
        db: Session,
        tenant_id: UUID,
        bank_account_id: UUID,
        position_date: date,
    ) -> CashPosition:
        """
        Calcula la posición de caja para una fecha y cuenta.

        Fórmula:
            closing_balance = opening_balance + inflows - outflows
        """
        # 1. Obtener saldo de apertura (saldo cierre del día anterior)
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

        # 2. Calcula inflows y outflows del día desde Payment table
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

        # 3. Calcula saldo de cierre
        closing_balance = opening_balance + inflows - outflows

        # 4. Busca o crea registro
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
        Crea proyección de flujo de caja para los próximos N días.

        Base: saldo actual + pagos confirmados próximos N días
        """
        today = date.today()
        projection_date = today
        projection_end_date = date(
            today.year + (today.month + projection_days - 1) // 12,
            ((today.month + projection_days - 1) % 12) + 1,
            1,
        )

        # Obtener saldo actual
        current_position = CashPositionService.calculate_position(
            db, tenant_id, bank_account_id, today
        )
        opening_balance = current_position.closing_balance

        # Proyectar inflows y outflows
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

        # Crear proyección
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
        """Obtiene posiciones de caja para un rango de fechas."""
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
