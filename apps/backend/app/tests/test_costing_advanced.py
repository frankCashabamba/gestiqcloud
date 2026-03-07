"""
Tests para el sistema de costeo avanzado.

Cubre:
- Separación TOUCH vs PROCESO
- Cálculo con CostPeriod
- Validaciones de período
- Impacto en recetas
"""

import os
import uuid as uuid_mod
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.core.global_catalogs import UnitOfMeasure
from app.models.production._cost_drivers import (
    CostDriverUnitType,
    ProductionCostDriver,
    RecipeCostLine,
)
from app.models.production._cost_periods import CostPeriod
from app.models.production._recipe_steps import RecipeStep
from app.models.recipes import Recipe
from app.modules.production.interface.http.tenant import _resolve_cost_driver_unit_code
from app.services.cost_periods_service import CostPeriodsService
from app.services.recipe_calculator import calculate_recipe_full_cost

# These tests require PostgreSQL (gen_random_uuid, Computed columns, UUID type consistency)
_db_url = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    _db_url.startswith("sqlite"),
    reason="Costing tests require PostgreSQL (UUID type mismatch on SQLite)",
)


@pytest.fixture
def test_tenant_id(db: Session):
    """Tenant ID para tests — crea el tenant si no existe."""
    from app.models.tenant import Tenant

    tid = UUID("12345678-1234-1234-1234-123456789012")
    existing = db.get(Tenant, tid)
    if not existing:
        tenant = Tenant(id=tid, name="Test Tenant Costing", slug="test-costing")
        db.add(tenant)
        db.commit()
    return tid


@pytest.fixture
def test_recipe(db: Session, test_tenant_id: UUID):
    """Crea una receta de prueba."""
    from app.models.core.products import Product

    product_id = UUID("87654321-4321-4321-4321-876543210987")
    existing = db.get(Product, product_id)
    if not existing:
        product = Product(
            id=product_id,
            tenant_id=test_tenant_id,
            name="Pan Integral - Producto Test",
            sku="PI-TEST-001",
            active=True,
            stock=0,
            unit="unit",
        )
        db.add(product)
        db.commit()

    recipe = Recipe(
        id=uuid_mod.uuid4(),
        tenant_id=test_tenant_id,
        product_id=product_id,
        name="Pan Integral - Test",
        yield_qty=192,
        # Legacy
        prep_time_minutes=50,
        baking_time_minutes=25,
        rest_time_minutes=45,
        # NUEVO: separación TOUCH vs PROCESO
        touch_minutes_standard=65,  # 10+5+40+5+5
        oven_minutes_standard=25,
        process_minutes=45,
        total_cost=Decimal("14.00"),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@pytest.fixture
def test_cost_period(db: Session, test_tenant_id: UUID):
    """Crea un período de costeo de prueba."""
    period = CostPeriod(
        id=uuid_mod.uuid4(),
        tenant_id=test_tenant_id,
        month="2025-02",
        labor_hour_rate=Decimal("4.00"),
        labor_paid_hours=Decimal("160"),
        touch_hours_total=Decimal("150"),
        electricity_cost=Decimal("100"),
        diesel_cost_month=Decimal("64"),
        oven_hours_total=Decimal("160"),
        notes="Test period",
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


class TestTouchVsProceso:
    """Tests para separación TOUCH vs PROCESO."""

    def test_recipe_touch_minutes(self, test_recipe: Recipe):
        """Receta debe tener touch_minutes_standard."""
        assert test_recipe.touch_minutes_standard == 65
        assert test_recipe.oven_minutes_standard == 25
        assert test_recipe.process_minutes == 45

    def test_recipe_total_minutes(self, test_recipe: Recipe):
        """Total de minutos debe ser suma correcta."""
        total = (
            test_recipe.touch_minutes_standard
            + test_recipe.oven_minutes_standard
            + test_recipe.process_minutes
        )
        assert total == 135


class TestCostPeriodData:
    """Tests para datos de CostPeriod."""

    def test_cost_period_exists(self, test_cost_period: CostPeriod):
        """Período debe existir con datos correctos."""
        assert test_cost_period.month == "2025-02"
        assert float(test_cost_period.labor_hour_rate) == 4.00
        assert float(test_cost_period.labor_paid_hours) == 160
        assert float(test_cost_period.touch_hours_total) == 150

    def test_cost_period_computed_burden_factor(self, test_cost_period: CostPeriod):
        """labor_burden_factor debe calcularse correctamente."""
        # 160 / 150 = 1.0667
        expected = Decimal("160") / Decimal("150")
        assert test_cost_period.labor_burden_factor is not None
        assert abs(float(test_cost_period.labor_burden_factor) - float(expected)) < 0.01

    def test_cost_period_computed_diesel_per_hour(self, test_cost_period: CostPeriod):
        """diesel_per_oven_hour debe calcularse correctamente."""
        # 64 / 160 = 0.40
        expected = Decimal("64") / Decimal("160")
        assert test_cost_period.diesel_per_oven_hour is not None
        assert abs(float(test_cost_period.diesel_per_oven_hour) - float(expected)) < 0.01

    def test_cost_period_computed_electricity_per_hour(self, test_cost_period: CostPeriod):
        """electricity_per_hour debe calcularse correctamente."""
        # 100 / 160 = 0.625
        expected = Decimal("100") / Decimal("160")
        assert test_cost_period.electricity_per_hour is not None
        assert abs(float(test_cost_period.electricity_per_hour) - float(expected)) < 0.01


class TestRecipeSteps:
    """Tests para etapas de receta."""

    def test_create_recipe_steps(self, db: Session, test_recipe: Recipe):
        """Crear etapas de receta."""
        steps = [
            RecipeStep(
                recipe_id=test_recipe.id,
                step_name="Pesar/mise en place",
                duration_minutes=10,
                is_touch=True,
                resource_type="labor",
                step_order=1,
            ),
            RecipeStep(
                recipe_id=test_recipe.id,
                step_name="Fermentación",
                duration_minutes=45,
                is_touch=False,
                resource_type="fermentation",
                step_order=2,
            ),
            RecipeStep(
                recipe_id=test_recipe.id,
                step_name="Horneado",
                duration_minutes=25,
                is_touch=False,
                resource_type="oven",
                step_order=3,
            ),
        ]
        db.add_all(steps)
        db.commit()

        # Verificar que se crearon
        steps_in_db = db.query(RecipeStep).filter(RecipeStep.recipe_id == test_recipe.id).all()
        assert len(steps_in_db) == 3

    def test_touch_vs_notouch_steps(self, db: Session, test_recipe: Recipe):
        """Steps TOUCH vs NO-TOUCH se diferencian correctamente."""
        touch_step = RecipeStep(
            recipe_id=test_recipe.id,
            step_name="Amasado",
            duration_minutes=5,
            is_touch=True,
            resource_type="labor",
            step_order=1,
        )
        notouch_step = RecipeStep(
            recipe_id=test_recipe.id,
            step_name="Reposo",
            duration_minutes=45,
            is_touch=False,
            resource_type="fermentation",
            step_order=2,
        )
        db.add_all([touch_step, notouch_step])
        db.commit()

        # Buscar ambos
        touch = (
            db.query(RecipeStep)
            .filter(RecipeStep.is_touch, RecipeStep.recipe_id == test_recipe.id)
            .all()
        )
        notouch = (
            db.query(RecipeStep)
            .filter(RecipeStep.is_touch.is_(False), RecipeStep.recipe_id == test_recipe.id)
            .all()
        )

        assert len(touch) == 1
        assert len(notouch) == 1


class TestCostCalculation:
    """Tests para cálculo de costos con CostPeriod."""

    def test_calculate_cost_with_period(
        self, db: Session, test_recipe: Recipe, test_cost_period: CostPeriod
    ):
        """Calcular costo usando CostPeriod."""
        # Agregar cost_drivers para la prueba
        labor_driver = ProductionCostDriver(
            tenant_id=test_recipe.tenant_id,
            code="LABOR_STD",
            name="Labor Standard",
            unit="hour",
            default_rate=Decimal("4.00"),
            is_active=True,
        )
        db.add(labor_driver)
        db.commit()

        # Calcular costo con período
        result = calculate_recipe_full_cost(db, test_recipe.id, period_month="2025-02")

        assert result is not None
        assert result["recipe_id"] == str(test_recipe.id)
        assert result["touch_minutes"] == 65
        assert result["oven_minutes"] == 25
        assert "breakdown" in result
        assert result["labor_burden_factor"] > 0

    def test_cost_breakdown_categories(
        self, db: Session, test_recipe: Recipe, test_cost_period: CostPeriod
    ):
        """Desglose debe incluir todas las categorías."""
        result = calculate_recipe_full_cost(db, test_recipe.id, period_month="2025-02")

        breakdown = result["breakdown"]
        required_keys = ["materials", "labor", "diesel", "electricity", "other"]
        for key in required_keys:
            assert key in breakdown
            assert isinstance(breakdown[key], (int, float))

    def test_labor_driver_with_short_hour_unit_autocalculates(
        self, db: Session, test_recipe: Recipe
    ):
        """Unidad 'H' debe tratarse como hora para auto-cálculo de mano de obra."""
        labor_driver = ProductionCostDriver(
            tenant_id=test_recipe.tenant_id,
            code="PANADERO",
            name="Panadero",
            unit="H",
            default_rate=Decimal("4.00"),
            is_active=True,
        )
        db.add(labor_driver)
        db.flush()

        db.add(
            RecipeCostLine(
                recipe_id=test_recipe.id,
                driver_id=labor_driver.id,
                qty_standard=Decimal("1.00"),
                headcount=1,
                line_order=0,
            )
        )
        db.commit()

        result = calculate_recipe_full_cost(db, test_recipe.id, period_month=None)

        assert result["cost_lines"]
        assert result["cost_lines"][0]["driver_unit"] == "H"
        assert result["cost_lines"][0]["cost_category"] == "labor"
        assert result["cost_lines"][0]["qty_standard"] == pytest.approx(65 / 60, rel=0.001)
        assert result["labor_total"] == pytest.approx((65 / 60) * 4, rel=0.001)

    def test_kwh_driver_is_classified_as_electricity_without_code_prefix(
        self, db: Session, test_recipe: Recipe
    ):
        """KWH debe clasificarse como electricidad aunque el código sea genérico."""
        electricity_driver = ProductionCostDriver(
            tenant_id=test_recipe.tenant_id,
            code="ELEC",
            name="Electricidad",
            unit="KWH",
            default_rate=Decimal("0.94"),
            consumption_rate=Decimal("4.00"),
            is_active=True,
        )
        db.add(electricity_driver)
        db.flush()

        db.add(
            RecipeCostLine(
                recipe_id=test_recipe.id,
                driver_id=electricity_driver.id,
                qty_standard=Decimal("1.3333"),
                headcount=1,
                line_order=0,
            )
        )
        db.commit()

        result = calculate_recipe_full_cost(db, test_recipe.id, period_month=None)
        electricity_line = next(
            line for line in result["cost_lines"] if line["driver_code"] == "ELEC"
        )

        assert electricity_line["driver_unit"] == "KWH"
        assert electricity_line["cost_category"] == "electricity"
        assert result["electricity_total"] == pytest.approx(1.3333 * 0.94, rel=0.001)
        assert result["other_indirect_total"] == pytest.approx(0, abs=0.001)

    def test_cost_driver_unit_is_normalized_to_catalog_code(
        self, db: Session, test_tenant_id: UUID
    ):
        """Create/update debe guardar el code canónico del catálogo del tenant."""
        db.add(
            CostDriverUnitType(
                tenant_id=test_tenant_id,
                code="hour",
                name_en="Hour",
                name_es="hora",
                is_active=True,
                sort_order=1,
            )
        )
        db.commit()

        assert _resolve_cost_driver_unit_code(db, test_tenant_id, "hora") == "hour"
        assert _resolve_cost_driver_unit_code(db, test_tenant_id, "hour") == "hour"

    def test_cost_driver_unit_falls_back_to_global_units_catalog(
        self, db: Session, test_tenant_id: UUID
    ):
        """Si el tenant no tiene catálogo propio, usar units_of_measure."""
        db.query(CostDriverUnitType).filter(CostDriverUnitType.tenant_id == test_tenant_id).delete()
        existing = db.query(UnitOfMeasure).filter(UnitOfMeasure.code == "HORA").first()
        if not existing:
            db.add(
                UnitOfMeasure(
                    code="HORA",
                    name="Hora",
                    abbreviation="h",
                    active=True,
                )
            )
        existing_lot = db.query(UnitOfMeasure).filter(UnitOfMeasure.code == "LOTE").first()
        if not existing_lot:
            db.add(
                UnitOfMeasure(
                    code="LOTE",
                    name="Fijo por lote",
                    abbreviation="lote",
                    active=True,
                )
            )
        db.commit()

        assert _resolve_cost_driver_unit_code(db, test_tenant_id, "h") == "HORA"
        assert _resolve_cost_driver_unit_code(db, test_tenant_id, "hora") == "HORA"
        assert _resolve_cost_driver_unit_code(db, test_tenant_id, "lote") == "LOTE"
        with pytest.raises(HTTPException):
            _resolve_cost_driver_unit_code(db, test_tenant_id, "hour")
        with pytest.raises(HTTPException):
            _resolve_cost_driver_unit_code(db, test_tenant_id, "flat")


class TestCostPeriodService:
    """Tests para CostPeriodsService."""

    def test_validate_period_good(
        self, db: Session, test_tenant_id: UUID, test_cost_period: CostPeriod
    ):
        """Validar período correcto."""
        service = CostPeriodsService(db, test_tenant_id)
        result = service.validate_period(test_cost_period.id)

        assert result.is_valid or not result.errors  # Sin errores fatales
        assert result.period_id == test_cost_period.id
        assert result.month == "2025-02"

    def test_validate_period_warning_high_burden(self, db: Session, test_tenant_id: UUID):
        """Validar período con burden_factor muy alto."""
        period = CostPeriod(
            id=uuid_mod.uuid4(),
            tenant_id=test_tenant_id,
            month="2025-03",
            labor_hour_rate=Decimal("4.00"),
            labor_paid_hours=Decimal("160"),
            touch_hours_total=Decimal("50"),  # Muy bajo → burden > 1.6
            electricity_cost=Decimal("100"),
            diesel_cost_month=Decimal("64"),
            oven_hours_total=Decimal("160"),
        )
        db.add(period)
        db.commit()

        service = CostPeriodsService(db, test_tenant_id)
        result = service.validate_period(period.id)

        assert not result.burden_factor_check
        assert any("burden" in w["code"].lower() for w in result.warnings)

    def test_get_current_period(
        self, db: Session, test_tenant_id: UUID, test_cost_period: CostPeriod
    ):
        """Obtener período actual (más reciente)."""
        service = CostPeriodsService(db, test_tenant_id)
        current = service.get_current_period()

        assert current is not None
        assert current.id == test_cost_period.id

    def test_update_period(self, db: Session, test_tenant_id: UUID, test_cost_period: CostPeriod):
        """Actualizar período."""
        service = CostPeriodsService(db, test_tenant_id)

        updated = service.update_period(
            test_cost_period.id, labor_hour_rate=Decimal("5.00"), notes="Updated test"
        )

        assert float(updated.labor_hour_rate) == 5.00
        assert updated.notes == "Updated test"

    def test_close_period(self, db: Session, test_tenant_id: UUID, test_cost_period: CostPeriod):
        """Cerrar período."""
        service = CostPeriodsService(db, test_tenant_id)

        closed = service.close_period(test_cost_period.id)

        assert closed.closed_at is not None


class TestFormulas:
    """Tests para fórmulas de cálculo."""

    def test_labor_burden_formula(self):
        """Validar fórmula de burden factor."""
        labor_paid_hours = Decimal("160")
        touch_hours_total = Decimal("150")

        burden_factor = labor_paid_hours / touch_hours_total

        assert float(burden_factor) == pytest.approx(1.0667, rel=0.01)

    def test_diesel_per_hour_formula(self):
        """Validar fórmula de diésel por hora."""
        diesel_cost = Decimal("64")
        oven_hours = Decimal("160")

        diesel_per_hour = diesel_cost / oven_hours

        assert float(diesel_per_hour) == 0.4

    def test_electricity_per_hour_formula(self):
        """Validar fórmula de electricidad por hora."""
        electricity_cost = Decimal("100")
        labor_paid_hours = Decimal("160")

        electricity_per_hour = electricity_cost / labor_paid_hours

        assert float(electricity_per_hour) == pytest.approx(0.625, rel=0.01)

    def test_unit_cost_calculation(self):
        """Validar cálculo de costo unitario."""
        materials = Decimal("14.00")
        labor = Decimal("4.62")
        diesel = Decimal("0.17")
        electricity = Decimal("0.68")
        other = Decimal("0.00")

        total_cost = materials + labor + diesel + electricity + other
        yield_qty = 192
        unit_cost = total_cost / yield_qty

        assert float(unit_cost) == pytest.approx(0.1015, rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
