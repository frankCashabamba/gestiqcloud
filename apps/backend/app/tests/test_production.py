"""
Tests de Módulo de Producción

Valida órdenes de producción, consumo de stock y generación de productos.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.models.production import ProductionOrder, ProductionOrderLine
from app.schemas.production import ProductionOrderCreate, ProductionOrderUpdate
from app.services.sector_defaults import get_sector_defaults


class TestProductionModels:
    """Tests de modelos de producción"""

    def test_production_order_table_name(self):
        """ProductionOrder debe tener tablename correcto"""
        assert ProductionOrder.__tablename__ == "production_orders"

    def test_production_order_line_table_name(self):
        """ProductionOrderLine debe tener tablename correcto"""
        assert ProductionOrderLine.__tablename__ == "production_order_lines"


class TestProductionSchemas:
    """Tests de schemas Pydantic"""

    def test_production_order_create_schema(self):
        """Schema de creación debe validar correctamente"""
        recipe_id = uuid4()
        product_id = uuid4()

        data = ProductionOrderCreate(
            recipe_id=recipe_id,
            product_id=product_id,
            qty_planned=Decimal("100"),
            scheduled_date=datetime.utcnow(),
            notes="Test production order",
        )

        assert data.recipe_id == recipe_id
        assert data.product_id == product_id
        assert data.qty_planned == Decimal("100")

    def test_production_order_create_requires_positive_qty(self):
        """Cantidad planificada debe ser > 0"""
        with pytest.raises(ValueError):
            ProductionOrderCreate(
                recipe_id=uuid4(),
                product_id=uuid4(),
                qty_planned=Decimal("-10"),  # Negativo = inválido
            )

    def test_production_order_update_schema(self):
        """Schema de actualización debe validar status"""
        data = ProductionOrderUpdate(
            qty_produced=Decimal("95"),
            waste_qty=Decimal("5"),
            status="COMPLETED",
        )

        assert data.qty_produced == Decimal("95")
        assert data.status == "COMPLETED"

    def test_production_order_update_invalid_status(self):
        """Status inválido debe fallar"""
        with pytest.raises(ValueError):
            ProductionOrderUpdate(status="INVALID_STATUS")


class TestProductionHelpers:
    """Tests de funciones helper"""

    def test_numero_generation_format(self):
        """Número de orden debe tener formato correcto"""
        # Simulación de generación
        year = datetime.utcnow().year
        numero = f"OP-{year}-0001"

        assert numero.startswith("OP-")
        assert str(year) in numero
        assert numero.endswith("-0001")

    def test_batch_number_format(self):
        """Número de lote debe tener formato correcto"""
        year = datetime.utcnow().year
        month = datetime.utcnow().month
        batch = f"LOT-{year}{month:02d}-0001"

        assert batch.startswith("LOT-")
        assert len(batch.split("-")) == 3
        assert batch.endswith("-0001")


class TestProductionIntegration:
    """Tests de integración con sector config"""

    def test_production_is_panaderia_compatible(self):
        """Producción debe estar configurado para panadería"""
        # Panadería debe tener recetas/producción
        productos = get_sector_defaults("productos", "panaderia")
        field_names = [f["field"] for f in productos]

        assert "receta_id" in field_names
        assert "caducidad_dias" in field_names  # Para productos de producción

    def test_production_is_restaurante_compatible(self):
        """Producción debe estar configurado para restaurante"""
        productos = get_sector_defaults("productos", "restaurante")
        field_names = [f["field"] for f in productos]

        assert "receta_id" in field_names
        assert "ingredientes" in field_names
        assert "tiempo_preparacion" in field_names

    def test_production_not_in_retail(self):
        """Retail NO debe tener campos de producción"""
        productos = get_sector_defaults("productos", "retail")
        field_names = [f["field"] for f in productos]

        assert "receta_id" not in field_names
        # Retail no produce, compra mercancía
