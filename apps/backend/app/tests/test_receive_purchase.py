"""
C-T2: Tests del flujo receive_purchase con costeo de inventario.

Cubre:
- InventoryCostingService.apply_inbound: cálculo de costo promedio ponderado
- InventoryCostingService.apply_inbound_fifo / apply_inbound_lifo: registro de capas
- InventoryCostingService.apply_outbound: decremento de stock y detección de faltante
- InventoryCostingService.apply_outbound_fifo / apply_outbound_lifo: consumo FIFO/LIFO + COGS
- InventoryCostingService.get_inventory_value: valoración por método
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.services.inventory_costing import InventoryCostingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT = str(uuid.uuid4())
WH = str(uuid.uuid4())
PROD = str(uuid.uuid4())


def _make_db(dialect_name: str = "postgresql"):
    """Crea un mock de Session con dialecto configurable."""
    db = MagicMock()
    bind = MagicMock()
    bind.dialect.name = dialect_name
    db.get_bind.return_value = bind
    return db


def _setup_ensure_state(db, on_hand_qty: float, avg_cost: float):
    """
    Configura db.execute para que _ensure_state_row retorne el estado dado.
    - Primera llamada: INSERT ON CONFLICT (no retorno relevante)
    - Segunda llamada: SELECT FOR UPDATE → retorna (on_hand_qty, avg_cost)
    """
    call_count = {"n": 0}

    def side_effect(stmt, params=None):
        result = MagicMock()
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            # INSERT — no importa el retorno
            result.first.return_value = None
        else:
            # SELECT
            result.first.return_value = (on_hand_qty, avg_cost)
        return result

    db.execute.side_effect = side_effect


# ============================================================================
# apply_inbound — costo promedio ponderado
# ============================================================================


class TestApplyInbound:

    def test_initial_inbound_sets_avg_cost(self):
        """Stock vacío → avg_cost = unit_cost del inbound."""
        db = _make_db()
        call_count = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                # INSERT
                pass
            elif n == 1:
                # SELECT
                result.first.return_value = (0.0, 0.0)
            # n==2 es el UPDATE — no retorno relevante
            return result

        db.execute.side_effect = side

        svc = InventoryCostingService(db)
        state = svc.apply_inbound(TENANT, WH, PROD, qty=Decimal("10"), unit_cost=Decimal("5"))

        assert state.on_hand_qty == Decimal("10")
        assert state.avg_cost == Decimal("5")

    def test_weighted_average_on_second_inbound(self):
        """
        Stock previo: 10 unidades @ $5.
        Ingreso: 5 unidades @ $8.
        Nuevo avg = (10*5 + 5*8) / 15 = 90/15 = $6.
        """
        db = _make_db()
        call_count = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                pass  # INSERT
            elif n == 1:
                result.first.return_value = (10.0, 5.0)  # estado previo
            return result

        db.execute.side_effect = side

        svc = InventoryCostingService(db)
        state = svc.apply_inbound(TENANT, WH, PROD, qty=Decimal("5"), unit_cost=Decimal("8"))

        assert state.on_hand_qty == Decimal("15")
        assert state.avg_cost == pytest.approx(Decimal("6"), abs=Decimal("0.01"))

    def test_avg_cost_unchanged_when_same_price(self):
        """Ingreso al mismo precio → avg no cambia."""
        db = _make_db()
        call_count = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 1:
                result.first.return_value = (20.0, 10.0)
            return result

        db.execute.side_effect = side

        svc = InventoryCostingService(db)
        state = svc.apply_inbound(TENANT, WH, PROD, qty=Decimal("10"), unit_cost=Decimal("10"))

        assert state.on_hand_qty == Decimal("30")
        assert state.avg_cost == pytest.approx(Decimal("10"), abs=Decimal("0.001"))

    def test_db_execute_called_with_update(self):
        """Verifica que se llame a UPDATE inventory_cost_state."""
        db = _make_db()
        call_count = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 1:
                result.first.return_value = (0.0, 0.0)
            return result

        db.execute.side_effect = side

        svc = InventoryCostingService(db)
        svc.apply_inbound(TENANT, WH, PROD, qty=Decimal("5"), unit_cost=Decimal("3"))

        # Debe haber habido al menos 3 calls: INSERT, SELECT, UPDATE
        assert db.execute.call_count >= 3


# ============================================================================
# apply_outbound — decremento y control de faltante
# ============================================================================


class TestApplyOutbound:

    def _setup(self, db, on_hand: float, avg_cost: float = 10.0):
        call_count = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 1:
                result.first.return_value = (on_hand, avg_cost)
            return result

        db.execute.side_effect = side

    def test_decrements_qty_correctly(self):
        db = _make_db()
        self._setup(db, on_hand=20.0, avg_cost=10.0)

        svc = InventoryCostingService(db)
        state = svc.apply_outbound(TENANT, WH, PROD, qty=Decimal("5"), allow_negative=False)

        assert state.on_hand_qty == Decimal("15")

    def test_avg_cost_preserved_on_outbound(self):
        """El costo promedio no cambia al consumir stock (AVG)."""
        db = _make_db()
        self._setup(db, on_hand=10.0, avg_cost=7.5)

        svc = InventoryCostingService(db)
        state = svc.apply_outbound(TENANT, WH, PROD, qty=Decimal("3"), allow_negative=False)

        assert state.avg_cost == pytest.approx(Decimal("7.5"), abs=Decimal("0.001"))

    def test_raises_http_exception_on_insufficient_stock(self):
        """allow_negative=False con stock insuficiente → HTTPException 400."""
        from fastapi import HTTPException as FastHTTPException

        db = _make_db()
        self._setup(db, on_hand=2.0, avg_cost=10.0)

        svc = InventoryCostingService(db)
        with pytest.raises(FastHTTPException) as exc_info:
            svc.apply_outbound(TENANT, WH, PROD, qty=Decimal("5"), allow_negative=False)

        assert exc_info.value.status_code == 400
        assert "insufficient_stock" in exc_info.value.detail

    def test_allows_negative_stock_when_flag_set(self):
        """allow_negative=True → permite stock negativo sin excepción."""
        db = _make_db()
        self._setup(db, on_hand=2.0, avg_cost=10.0)

        svc = InventoryCostingService(db)
        state = svc.apply_outbound(TENANT, WH, PROD, qty=Decimal("5"), allow_negative=True)

        assert state.on_hand_qty == Decimal("-3")


# ============================================================================
# apply_inbound_fifo / apply_inbound_lifo — registro de capas
# ============================================================================


class TestApplyInboundLayered:

    def _make_layered_db(self, on_hand: float = 0.0, avg_cost: float = 0.0):
        """
        Configura db para apply_inbound_fifo/lifo:
        - _ensure_layers_table: ALTER TABLE calls (no importan)
        - INSERT into inventory_cost_layers
        - _ensure_state_row: INSERT + SELECT
        - UPDATE inventory_cost_state
        """
        db = _make_db()
        call_seq = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            sql_str = str(stmt) if not isinstance(stmt, str) else stmt
            call_seq["n"] += 1
            # Cuando busca el estado actual (SELECT on_hand_qty, avg_cost)
            if "on_hand_qty" in sql_str and "SELECT" in sql_str.upper():
                result.first.return_value = (on_hand, avg_cost)
            return result

        db.execute.side_effect = side
        return db

    def test_fifo_calls_execute_for_layer_insert(self):
        db = self._make_layered_db()
        svc = InventoryCostingService(db)

        svc.apply_inbound_fifo(TENANT, WH, PROD, qty=Decimal("10"), unit_cost=Decimal("5"))

        # Verificar que se ejecutaron al menos las llamadas a DB
        assert db.execute.call_count >= 2

    def test_lifo_returns_updated_state(self):
        db = self._make_layered_db(on_hand=10.0, avg_cost=5.0)
        svc = InventoryCostingService(db)

        state = svc.apply_inbound_lifo(TENANT, WH, PROD, qty=Decimal("5"), unit_cost=Decimal("8"))

        # qty debe incluir el nuevo ingreso
        assert state.on_hand_qty == Decimal("15")

    def test_fifo_returns_updated_state(self):
        db = self._make_layered_db(on_hand=0.0, avg_cost=0.0)
        svc = InventoryCostingService(db)

        state = svc.apply_inbound_fifo(TENANT, WH, PROD, qty=Decimal("20"), unit_cost=Decimal("3"))

        assert state.on_hand_qty == Decimal("20")

    def test_inbound_with_lot_and_expiry(self):
        """apply_inbound_fifo acepta lot y expires_at sin error."""
        from datetime import date

        db = self._make_layered_db()
        svc = InventoryCostingService(db)

        # No debe lanzar excepción
        state = svc.apply_inbound_fifo(
            TENANT,
            WH,
            PROD,
            qty=Decimal("5"),
            unit_cost=Decimal("10"),
            lot="LOT-001",
            expires_at=date(2027, 12, 31),
        )

        assert state.on_hand_qty == Decimal("5")


# ============================================================================
# apply_outbound_fifo / apply_outbound_lifo — consumo de capas + COGS
# ============================================================================


class TestApplyOutboundLayered:

    def _make_outbound_db(self, layers: list[tuple], on_hand: float = 10.0, avg_cost: float = 5.0):
        """
        layers: list of (id, remaining_qty, unit_cost) tuples.
        Simula _consume_layers + apply_outbound.
        """
        db = _make_db()
        call_seq = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            sql_str = str(stmt) if not isinstance(stmt, str) else stmt
            call_seq["n"] += 1

            if "remaining_qty, unit_cost" in sql_str:
                # SELECT FROM inventory_cost_layers → retorna capas
                result.fetchall.return_value = layers
            elif "on_hand_qty" in sql_str and "SELECT" in sql_str.upper():
                result.first.return_value = (on_hand, avg_cost)
            return result

        db.execute.side_effect = side
        return db

    def test_fifo_calculates_cogs_single_layer(self):
        """
        1 capa: 10 unidades @ $5.
        Consumo: 6 unidades → COGS = 6 * 5 = $30.
        """
        layers = [(1, 10.0, 5.0)]
        db = self._make_outbound_db(layers, on_hand=10.0, avg_cost=5.0)
        svc = InventoryCostingService(db)

        state, cogs = svc.apply_outbound_fifo(TENANT, WH, PROD, qty=Decimal("6"))

        assert cogs == pytest.approx(Decimal("30"), abs=Decimal("0.01"))

    def test_fifo_calculates_cogs_multiple_layers(self):
        """
        FIFO con 2 capas:
        - Capa 1 (más antigua): 5 unidades @ $4
        - Capa 2: 10 unidades @ $6
        Consumo: 8 unidades → COGS = 5*4 + 3*6 = 20 + 18 = $38.
        """
        layers = [(1, 5.0, 4.0), (2, 10.0, 6.0)]
        db = self._make_outbound_db(layers, on_hand=15.0, avg_cost=5.33)
        svc = InventoryCostingService(db)

        state, cogs = svc.apply_outbound_fifo(TENANT, WH, PROD, qty=Decimal("8"))

        assert cogs == pytest.approx(Decimal("38"), abs=Decimal("0.01"))

    def test_lifo_calculates_cogs_multiple_layers(self):
        """
        LIFO con 2 capas:
        - Capa 1 (más antigua): 5 unidades @ $4
        - Capa 2 (más reciente): 10 unidades @ $6
        LIFO consume capa 2 primero.
        Consumo: 8 unidades → COGS = 8*6 = $48.
        """
        # LIFO invierte el orden: capa 2 primero
        layers = [(2, 10.0, 6.0), (1, 5.0, 4.0)]
        db = self._make_outbound_db(layers, on_hand=15.0, avg_cost=5.33)
        svc = InventoryCostingService(db)

        state, cogs = svc.apply_outbound_lifo(TENANT, WH, PROD, qty=Decimal("8"))

        assert cogs == pytest.approx(Decimal("48"), abs=Decimal("0.01"))

    def test_fifo_raises_when_insufficient_layers(self):
        """Sin capas suficientes y allow_negative=False → HTTPException."""
        from fastapi import HTTPException as FastHTTPException

        layers = [(1, 3.0, 5.0)]  # solo 3 unidades disponibles
        db = self._make_outbound_db(layers, on_hand=3.0)
        svc = InventoryCostingService(db)

        with pytest.raises(FastHTTPException) as exc_info:
            svc.apply_outbound_fifo(TENANT, WH, PROD, qty=Decimal("10"), allow_negative=False)

        assert exc_info.value.status_code == 400

    def test_zero_cogs_when_no_layers(self):
        """Sin capas disponibles pero allow_negative=True → COGS = 0."""
        layers = []
        db = self._make_outbound_db(layers, on_hand=10.0)
        svc = InventoryCostingService(db)

        state, cogs = svc.apply_outbound_fifo(TENANT, WH, PROD, qty=Decimal("5"), allow_negative=True)

        assert cogs == Decimal("0")


# ============================================================================
# get_inventory_value — valoración del inventario
# ============================================================================


class TestGetInventoryValue:

    def test_avg_method_returns_sum(self):
        """AVG: SUM(on_hand_qty * avg_cost)."""
        db = _make_db()
        db.execute.return_value.scalar.return_value = 500.0

        svc = InventoryCostingService(db)
        value = svc.get_inventory_value(TENANT, costing_method="avg")

        assert value == Decimal("500")

    def test_avg_method_returns_zero_when_no_stock(self):
        db = _make_db()
        db.execute.return_value.scalar.return_value = None

        svc = InventoryCostingService(db)
        value = svc.get_inventory_value(TENANT, costing_method="avg")

        assert value == Decimal("0")

    def test_unsupported_method_raises_value_error(self):
        db = _make_db()
        svc = InventoryCostingService(db)

        with pytest.raises(ValueError, match="Unsupported"):
            svc.get_inventory_value(TENANT, costing_method="xyz")  # type: ignore

    def test_fifo_method_calls_layer_inventory_value(self):
        """Para FIFO/LIFO se consultan las capas de costo."""
        db = _make_db()
        db.execute.return_value.fetchall.return_value = [
            (10.0, 5.0),
            (5.0, 8.0),
        ]

        svc = InventoryCostingService(db)
        value = svc.get_inventory_value(TENANT, costing_method="fifo")

        # 10*5 + 5*8 = 50 + 40 = 90
        assert value == pytest.approx(Decimal("90"), abs=Decimal("0.01"))

    def test_lifo_method_same_value_calculation(self):
        """LIFO computa el mismo SUM pero con orden invertido."""
        db = _make_db()
        db.execute.return_value.fetchall.return_value = [
            (5.0, 8.0),   # más reciente primero
            (10.0, 5.0),
        ]

        svc = InventoryCostingService(db)
        value = svc.get_inventory_value(TENANT, costing_method="lifo")

        # Mismo total: 5*8 + 10*5 = 40 + 50 = 90
        assert value == pytest.approx(Decimal("90"), abs=Decimal("0.01"))


# ============================================================================
# Pipeline completo: receive_purchase → costeo actualizado
# ============================================================================


class TestReceivePurchasePipeline:
    """
    Simula el pipeline lógico del endpoint receive_purchase:
    1. Inbound de múltiples productos en una recepción
    2. Verifica que el costo promedio se actualice correctamente para cada uno
    """

    def test_multi_product_receive_updates_each_product_independently(self):
        """
        Recepción de 2 productos distintos:
        - Producto A: 10 unidades @ $5 (estado inicial vacío)
        - Producto B: 20 unidades @ $3 (estado inicial 5 unidades @ $4)

        El costo de B = (5*4 + 20*3) / 25 = (20+60)/25 = $3.20
        """
        prod_a = str(uuid.uuid4())
        prod_b = str(uuid.uuid4())

        # DB para producto A (estado inicial vacío)
        db_a = _make_db()
        seq_a = {"n": 0}

        def side_a(stmt, params=None):
            result = MagicMock()
            n = seq_a["n"]
            seq_a["n"] += 1
            if n == 1:
                result.first.return_value = (0.0, 0.0)
            return result

        db_a.execute.side_effect = side_a

        # DB para producto B (estado inicial 5 @ $4)
        db_b = _make_db()
        seq_b = {"n": 0}

        def side_b(stmt, params=None):
            result = MagicMock()
            n = seq_b["n"]
            seq_b["n"] += 1
            if n == 1:
                result.first.return_value = (5.0, 4.0)
            return result

        db_b.execute.side_effect = side_b

        svc_a = InventoryCostingService(db_a)
        svc_b = InventoryCostingService(db_b)

        state_a = svc_a.apply_inbound(TENANT, WH, prod_a, qty=Decimal("10"), unit_cost=Decimal("5"))
        state_b = svc_b.apply_inbound(TENANT, WH, prod_b, qty=Decimal("20"), unit_cost=Decimal("3"))

        assert state_a.on_hand_qty == Decimal("10")
        assert state_a.avg_cost == Decimal("5")

        assert state_b.on_hand_qty == Decimal("25")
        assert state_b.avg_cost == pytest.approx(Decimal("3.2"), abs=Decimal("0.001"))

    def test_receive_then_sell_fifo_correct_cogs(self):
        """
        Flujo compra → venta con FIFO:
        - Recibe 10 unidades @ $5 (capa 1)
        - Recibe 5 unidades @ $8 (capa 2)
        - Vende 8 unidades → COGS FIFO = 8*5 = $40 (consume toda capa 1 - 2)
        """
        db = _make_db()
        call_seq = {"n": 0}

        def side(stmt, params=None):
            result = MagicMock()
            sql_str = str(stmt) if not isinstance(stmt, str) else stmt
            call_seq["n"] += 1

            if "remaining_qty, unit_cost" in sql_str:
                # Retorna capas FIFO: capa 1 más antigua primero
                result.fetchall.return_value = [(1, 10.0, 5.0), (2, 5.0, 8.0)]
            elif "on_hand_qty" in sql_str and "SELECT" in sql_str.upper():
                result.first.return_value = (15.0, 6.0)
            return result

        db.execute.side_effect = side

        svc = InventoryCostingService(db)
        state, cogs = svc.apply_outbound_fifo(TENANT, WH, PROD, qty=Decimal("8"))

        assert cogs == pytest.approx(Decimal("40"), abs=Decimal("0.01"))
        assert state.on_hand_qty == Decimal("7")
