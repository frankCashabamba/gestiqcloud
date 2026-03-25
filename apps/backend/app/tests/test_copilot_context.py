"""
C-T5: Tests del CopilotContextBuilder.

Cubre:
- Dispatch al loader correcto según módulo
- Alias de módulos resueltos a IDs canónicos
- Fallback a _general cuando módulo desconocido
- PII masking aplicado al contexto
- Manejo de errores en loaders (fallback a error JSON)
- Cada loader retorna la clave 'modulo' correcta
- Output es JSON válido
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from app.modules.copilot.context_builder import CopilotContextBuilder

TENANT = str(uuid.uuid4())


def _make_db_with_results(results: list):
    """DB mock que retorna resultados en secuencia para cada llamada a execute()."""
    db = MagicMock()
    call_idx = {"n": 0}

    def side(stmt, params=None):
        result = MagicMock()
        n = call_idx["n"]
        call_idx["n"] += 1
        if n < len(results):
            val = results[n]
            if isinstance(val, list):
                result.fetchall.return_value = val
                result.fetchone.return_value = val[0] if val else None
            else:
                result.fetchone.return_value = val
                result.fetchall.return_value = [val] if val else []
            result.scalar.return_value = (
                val[0]
                if (isinstance(val, tuple) and val)
                else (val if not isinstance(val, list) else None)
            )
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = []
            result.scalar.return_value = None
        return result

    db.execute.side_effect = side
    return db


def _row(**kwargs):
    row = MagicMock()
    row._mapping = kwargs
    return row


class TestModuleDispatch:

    def test_unknown_module_uses_general(self):
        db = _make_db_with_results([(42,), (3,)])
        result_json = CopilotContextBuilder.build(db, TENANT, "modulo_inexistente")
        data = json.loads(result_json)
        assert data["modulo"] == "General"

    def test_none_module_uses_general(self):
        db = _make_db_with_results([(10,), (2,)])
        result_json = CopilotContextBuilder.build(db, TENANT, None)
        data = json.loads(result_json)
        assert data["modulo"] == "General"

    def test_pos_module_dispatches_correctly(self):
        shift_row = _row(
            id=str(uuid.uuid4()), status="open", opened_at="2026-03-17T08:00", opening_float=100.0
        )
        sales_row = _row(recibos=5, total=350.0)
        db = _make_db_with_results([shift_row, sales_row, []])
        result_json = CopilotContextBuilder.build(db, TENANT, "pos")
        data = json.loads(result_json)
        assert data["modulo"] == "POS"
        assert "ventas_hoy" in data
        assert "turno_activo" in data

    def test_inventory_spanish_alias(self):
        low_stock_row = _row(name="Producto A", qty=2, almacen="A01")
        total_row = _row(valor=5000.0)
        db = _make_db_with_results([[low_stock_row], total_row, []])
        result_json = CopilotContextBuilder.build(db, TENANT, "inventario")
        data = json.loads(result_json)
        assert data["modulo"] == "Inventario"

    def test_purchases_spanish_alias(self):
        pending_row = _row(total=3, monto=1500.0)
        db = _make_db_with_results([pending_row, []])
        result_json = CopilotContextBuilder.build(db, TENANT, "compras")
        data = json.loads(result_json)
        assert data["modulo"] == "Compras"

    def test_sales_english_key(self):
        db = _make_db_with_results([[], []])
        result_json = CopilotContextBuilder.build(db, TENANT, "sales")
        data = json.loads(result_json)
        assert data["modulo"] == "Ventas"

    def test_finance_spanish_alias(self):
        db = _make_db_with_results([[]])
        result_json = CopilotContextBuilder.build(db, TENANT, "finanzas")
        data = json.loads(result_json)
        assert data["modulo"] == "Finanzas"

    def test_manufacturing_spanish_alias(self):
        db = _make_db_with_results([(5,)])
        result_json = CopilotContextBuilder.build(db, TENANT, "produccion")
        data = json.loads(result_json)
        assert data["modulo"] == "Producción"

    def test_expenses_spanish_alias(self):
        db = _make_db_with_results([[]])
        result_json = CopilotContextBuilder.build(db, TENANT, "gastos")
        data = json.loads(result_json)
        assert data["modulo"] == "Gastos"

    def test_hr_spanish_alias(self):
        db = _make_db_with_results([(12,)])
        result_json = CopilotContextBuilder.build(db, TENANT, "rrhh")
        data = json.loads(result_json)
        assert data["modulo"] == "RRHH"

    def test_products_spanish_alias(self):
        stats_row = _row(total=50, activos=45)
        db = _make_db_with_results([stats_row])
        result_json = CopilotContextBuilder.build(db, TENANT, "productos")
        data = json.loads(result_json)
        assert data["modulo"] == "Productos"

    def test_crm_module_dispatches_correctly(self):
        lead_row = _row(estado="new", total=4)
        opp_row = _row(etapa="qualification", total=2, valor=900.0)
        db = _make_db_with_results([[lead_row], [opp_row]])
        result_json = CopilotContextBuilder.build(db, TENANT, "crm")
        data = json.loads(result_json)
        assert data["modulo"] == "CRM"
        assert len(data["leads_por_estado"]) == 1

    def test_users_module_dispatches_correctly(self):
        recent_row = _row(
            first_name="Ana",
            last_name="Admin",
            email="ana@example.com",
            is_active=True,
            is_company_admin=True,
            created_at="2026-03-20T10:00:00",
        )
        db = _make_db_with_results([(10, 8, 2), [recent_row], (4,)])
        result_json = CopilotContextBuilder.build(db, TENANT, "users")
        data = json.loads(result_json)
        assert data["modulo"] == "Usuarios"
        assert data["usuarios"]["total"] == 10
        assert data["roles"] == 4


class TestOutputFormat:

    def test_always_returns_valid_json(self):
        db = _make_db_with_results([(0,), (0,)])
        result = CopilotContextBuilder.build(db, TENANT, None)
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_pos_no_active_shift(self):
        sales_row = _row(recibos=0, total=0.0)
        db = _make_db_with_results([None, sales_row, []])
        result_json = CopilotContextBuilder.build(db, TENANT, "pos")
        data = json.loads(result_json)
        assert data["turno_activo"] is None

    def test_inventory_returns_list_fields(self):
        low1 = _row(name="P1", qty=1, almacen="W1")
        low2 = _row(name="P2", qty=2, almacen="W1")
        total_row = _row(valor=9999.0)
        db = _make_db_with_results([[low1, low2], total_row, []])
        result_json = CopilotContextBuilder.build(db, TENANT, "inventory")
        data = json.loads(result_json)
        assert isinstance(data["stock_bajo"], list)
        assert len(data["stock_bajo"]) == 2

    def test_general_returns_counts(self):
        db = _make_db_with_results([(20,), (4,)])
        result_json = CopilotContextBuilder.build(db, TENANT, None)
        data = json.loads(result_json)
        assert data["total_productos"] == 20
        assert data["productos_stock_bajo"] == 4


class TestPIIMasking:

    def test_pii_masking_called_on_list_context(self):
        with patch("app.modules.copilot.context_builder.pii_mask_row") as mock_mask:
            mock_mask.side_effect = lambda r: {
                k: "***" if k in ("name", "email") else v for k, v in r.items()
            }

            sales_row = _row(mes="2026-03-01", pedidos=5, total=2000.0)
            client_row = _row(name="Juan Pérez", pedidos=3, total=1500.0)
            db = _make_db_with_results([[sales_row], [client_row]])

            result_json = CopilotContextBuilder.build(db, TENANT, "sales")
            json.loads(result_json)

            assert mock_mask.called


class TestErrorHandling:

    def test_loader_exception_returns_error_json(self):
        db = MagicMock()
        db.execute.side_effect = Exception("DB connection lost")

        result_json = CopilotContextBuilder.build(db, TENANT, "pos")
        data = json.loads(result_json)

        assert "error" in data
        assert "context_unavailable" in data["error"]

    def test_error_json_is_still_valid_json(self):
        db = MagicMock()
        db.execute.side_effect = RuntimeError("timeout")

        result_json = CopilotContextBuilder.build(db, TENANT, "inventory")
        data = json.loads(result_json)
        assert isinstance(data, dict)

    def test_db_rollback_called_on_error(self):
        db = MagicMock()
        db.execute.side_effect = Exception("error")

        CopilotContextBuilder.build(db, TENANT, "pos")

        db.rollback.assert_called()


class TestLoaderRegistry:

    def test_all_loaders_map_to_existing_methods(self):
        for key, method_name in CopilotContextBuilder.LOADERS.items():
            assert hasattr(
                CopilotContextBuilder, method_name
            ), f"Loader '{method_name}' para módulo '{key}' no existe en CopilotContextBuilder"

    def test_all_loaders_callable(self):
        for method_name in set(CopilotContextBuilder.LOADERS.values()):
            method = getattr(CopilotContextBuilder, method_name)
            assert callable(method)

    def test_loader_registry_uses_canonical_module_ids(self):
        assert "inventory" in CopilotContextBuilder.LOADERS
        assert "finance" in CopilotContextBuilder.LOADERS
        assert "manufacturing" in CopilotContextBuilder.LOADERS
        assert "crm" in CopilotContextBuilder.LOADERS
        assert "users" in CopilotContextBuilder.LOADERS
        assert "inventario" not in CopilotContextBuilder.LOADERS
        assert "finanzas" not in CopilotContextBuilder.LOADERS
        assert "produccion" not in CopilotContextBuilder.LOADERS
