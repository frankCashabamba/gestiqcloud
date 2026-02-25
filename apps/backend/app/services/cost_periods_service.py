"""
Service para gestionar Cost Periods (costeo mensual).

Encargado de:
1. Crear/actualizar períodos de costeo
2. Validar datos del período
3. Calcular factores derivados (burden, rates, etc)
4. Cierre de período y recálculos
5. Análisis de impacto en recetas
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.production._cost_periods import CostPeriod
from app.models.recipes import Recipe
from app.schemas.cost_periods import CostPeriodValidationResult


class CostPeriodsService:
    """Servicio de gestión de períodos de costeo."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create_period(
        self,
        month: str,
        labor_hour_rate: float,
        labor_paid_hours: float = 160,
        touch_hours_total: float | None = None,
        electricity_cost: float = 0,
        diesel_cost_month: float = 0,
        oven_hours_total: float = 160,
        production_share_pct: float | None = None,
        notes: str | None = None,
    ) -> CostPeriod:
        """
        Crea un nuevo período de costeo.

        Los campos computed (burden_factor, rates) se calculan automáticamente en DB.
        """
        period = CostPeriod(
            tenant_id=self.tenant_id,
            month=month,
            labor_hour_rate=Decimal(str(labor_hour_rate)),
            labor_paid_hours=Decimal(str(labor_paid_hours)),
            touch_hours_total=Decimal(str(touch_hours_total)) if touch_hours_total else None,
            electricity_cost=Decimal(str(electricity_cost)),
            diesel_cost_month=Decimal(str(diesel_cost_month)),
            oven_hours_total=Decimal(str(oven_hours_total)),
            production_share_pct=(
                Decimal(str(production_share_pct)) if production_share_pct else None
            ),
            notes=notes,
            is_active=True,
        )
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def update_period(
        self,
        period_id: UUID,
        **kwargs,
    ) -> CostPeriod:
        """Actualiza un período de costeo."""
        period = self.db.query(CostPeriod).filter(CostPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Period not found: {period_id}")

        # Validar que sea del mismo tenant
        if period.tenant_id != self.tenant_id:
            raise PermissionError(f"Access denied to period {period_id}")

        # Mapear valores Decimal
        for key, value in kwargs.items():
            if value is not None and key in [
                "labor_hour_rate",
                "labor_paid_hours",
                "touch_hours_total",
                "electricity_cost",
                "diesel_cost_month",
                "oven_hours_total",
                "production_share_pct",
            ]:
                value = Decimal(str(value))
            setattr(period, key, value)

        self.db.commit()
        self.db.refresh(period)
        return period

    def get_current_period(self) -> CostPeriod | None:
        """Obtiene el período actual (más reciente activo)."""
        return (
            self.db.query(CostPeriod)
            .filter(
                CostPeriod.tenant_id == self.tenant_id,
                CostPeriod.is_active,
            )
            .order_by(desc(CostPeriod.month))
            .first()
        )

    def get_period(self, month: str) -> CostPeriod | None:
        """Obtiene un período por mes (YYYY-MM)."""
        return (
            self.db.query(CostPeriod)
            .filter(
                CostPeriod.tenant_id == self.tenant_id,
                CostPeriod.month == month,
            )
            .first()
        )

    def validate_period(self, period_id: UUID) -> CostPeriodValidationResult:
        """
        Valida un período y retorna warnings/errors.

        Checks:
        - labor_burden_factor está entre 0.8 y 1.6 (eficiencia razonable)
        - oven_hours_total > 10 (no subutilizado)
        - touch_hours_total ≈ labor_paid_hours (no mucho tiempo muerto)
        """
        period = self.db.query(CostPeriod).filter(CostPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Period not found: {period_id}")

        warnings = []
        errors = []

        # Check 1: Burden factor
        burden_ok = True
        if period.labor_burden_factor:
            bf = float(period.labor_burden_factor)
            if bf > 1.6:
                burden_ok = False
                warnings.append(
                    {
                        "code": "burden_too_high",
                        "message": f"Burden factor muy alto: {bf:.2f}. Indica mucho tiempo muerto.",
                        "suggestion": "Revisar si hay ineficiencias no capturadas o tareas adicionales",
                    }
                )
            elif bf < 0.8:
                burden_ok = False
                warnings.append(
                    {
                        "code": "burden_too_low",
                        "message": f"Burden factor bajo: {bf:.2f}. Posible medición incompleta.",
                        "suggestion": "Verificar que se registren todos los touch_hours",
                    }
                )

        # Check 2: Oven utilization
        oven_ok = True
        if period.oven_hours_total:
            oh = float(period.oven_hours_total)
            if oh < 10:
                oven_ok = False
                warnings.append(
                    {
                        "code": "oven_underutilized",
                        "message": f"Horno muy poco utilizado: {oh:.1f}h. Datos incompletos?",
                        "suggestion": "Verificar que se registren todas las horas de horno",
                    }
                )

        # Check 3: Touch hours vs paid hours (eficiencia general)
        touch_ok = True
        if period.touch_hours_total and period.labor_paid_hours:
            touch = float(period.touch_hours_total)
            paid = float(period.labor_paid_hours)
            ratio = touch / paid if paid > 0 else 0
            if ratio < 0.5:
                touch_ok = False
                warnings.append(
                    {
                        "code": "low_touch_ratio",
                        "message": f"Ratio touch/paid muy bajo: {ratio:.1%}. Muchos tiempos muertos.",
                        "suggestion": "Normal si hay descansos, mantenimiento, etc. O falta registrar horas.",
                    }
                )

        return CostPeriodValidationResult(
            period_id=period_id,
            month=period.month,
            is_valid=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            burden_factor_check=burden_ok,
            oven_utilization_check=oven_ok,
            touch_hours_check=touch_ok,
        )

    def close_period(self, period_id: UUID) -> CostPeriod:
        """
        Cierra formalmente un período.

        Esto marca que no se pueden hacer más cambios al período
        y se pueden hacer recálculos históricos si necesario.
        """
        period = self.db.query(CostPeriod).filter(CostPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Period not found: {period_id}")

        period.closed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(period)
        return period

    def get_period_impact_on_recipes(self, period_id: UUID) -> dict:
        """
        Calcula el impacto de aplicar un período a todas las recetas del tenant.

        Retorna:
        - Recipes afectadas
        - Cost changes
        - Estadísticas aggregadas
        """
        period = self.db.query(CostPeriod).filter(CostPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Period not found: {period_id}")

        recipes = (
            self.db.query(Recipe).filter(Recipe.tenant_id == self.tenant_id, Recipe.is_active).all()
        )

        # Usar calculate_recipe_full_cost con el period_month
        from app.services.recipe_calculator import calculate_recipe_full_cost

        impacted_recipes = []
        total_cost_change = Decimal("0")
        total_recipes = len(recipes)

        for recipe in recipes:
            try:
                # Cost con período
                cost_with = calculate_recipe_full_cost(
                    self.db, recipe.id, period_month=period.month
                )
                # Cost sin período (default)
                cost_without = calculate_recipe_full_cost(self.db, recipe.id, period_month=None)

                cost_before = Decimal(str(cost_without["full_cost_total"]))
                cost_after = Decimal(str(cost_with["full_cost_total"]))
                change = cost_after - cost_before
                change_pct = (change / cost_before * 100) if cost_before > 0 else Decimal("0")

                total_cost_change += change

                impacted_recipes.append(
                    {
                        "recipe_id": str(recipe.id),
                        "recipe_name": recipe.name,
                        "cost_before": float(cost_before),
                        "cost_after": float(cost_after),
                        "cost_change": float(change),
                        "cost_change_pct": float(change_pct),
                    }
                )

            except Exception:
                # Skip si falla el cálculo
                pass

        avg_change_pct = (
            float(
                total_cost_change
                / sum(Decimal(str(r["cost_before"])) for r in impacted_recipes)
                * 100
            )
            if impacted_recipes and any(r["cost_before"] > 0 for r in impacted_recipes)
            else 0
        )

        return {
            "period": {
                "id": str(period.id),
                "month": period.month,
                "labor_burden_factor": float(period.labor_burden_factor),
                "diesel_per_oven_hour": float(period.diesel_per_oven_hour or 0),
                "electricity_per_hour": float(period.electricity_per_hour or 0),
            },
            "recipes_impacted": len(impacted_recipes),
            "total_recipes": total_recipes,
            "total_cost_change": float(total_cost_change),
            "average_change_pct": avg_change_pct,
            "recipes": sorted(impacted_recipes, key=lambda x: x["cost_change_pct"], reverse=True),
        }
