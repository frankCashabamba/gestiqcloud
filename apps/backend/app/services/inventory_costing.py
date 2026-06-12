from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, NamedTuple
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.shared.utils import normalize_lot as _normalize_lot
from app.shared.utils import to_decimal as _dec


class CostState(NamedTuple):
    on_hand_qty: Decimal
    avg_cost: Decimal


class InventoryCostingService:
    def __init__(self, db: Session):
        self.db = db

    def _ensure_state_row(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        initial_qty: Decimal | None = None,
        initial_avg_cost: Decimal | None = None,
    ) -> CostState:
        params = {
            "tid": tenant_id,
            "wid": warehouse_id,
            "pid": product_id,
            "q": float(initial_qty or Decimal("0")),
            "avg": float(initial_avg_cost or Decimal("0")),
        }

        if getattr(self.db.get_bind().dialect, "name", "") == "sqlite":
            existing = self.db.execute(
                text(
                    "SELECT 1 FROM inventory_cost_state "
                    "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid "
                    "LIMIT 1"
                ),
                params,
            ).first()
            if not existing:
                self.db.execute(
                    text(
                        "INSERT INTO inventory_cost_state("
                        "id, tenant_id, warehouse_id, product_id, on_hand_qty, avg_cost, updated_at"
                        ") VALUES (:id, :tid, :wid, :pid, :q, :avg, :updated_at)"
                    ),
                    {
                        **params,
                        "id": str(uuid4()),
                        "updated_at": datetime.now(UTC),
                    },
                )
        else:
            self.db.execute(
                text(
                    "INSERT INTO inventory_cost_state("
                    "tenant_id, warehouse_id, product_id, on_hand_qty, avg_cost"
                    ") VALUES (:tid, :wid, :pid, :q, :avg) "
                    "ON CONFLICT (tenant_id, warehouse_id, product_id) DO NOTHING"
                ),
                params,
            )

        select_sql = (
            "SELECT on_hand_qty, avg_cost "
            "FROM inventory_cost_state "
            "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
        )
        if getattr(self.db.get_bind().dialect, "name", "") != "sqlite":
            select_sql += " FOR UPDATE"

        row = self.db.execute(
            text(select_sql),
            {"tid": tenant_id, "wid": warehouse_id, "pid": product_id},
        ).first()

        if not row:
            # Should not happen due to insert above; keep safe defaults.
            return CostState(_dec(0, "0.000001"), _dec(0, "0.000001"))

        return CostState(_dec(row[0], "0.000001"), _dec(row[1], "0.000001"))

    def apply_inbound(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        unit_cost: Decimal,
        initial_qty: Decimal | None = None,
        initial_avg_cost: Decimal | None = None,
    ) -> CostState:
        state = self._ensure_state_row(
            tenant_id,
            warehouse_id,
            product_id,
            initial_qty=initial_qty,
            initial_avg_cost=initial_avg_cost,
        )

        new_qty = state.on_hand_qty + qty
        if new_qty > 0:
            new_avg = (state.on_hand_qty * state.avg_cost + qty * unit_cost) / new_qty
        else:
            new_avg = _dec(0, "0.000001")

        self.db.execute(
            text(
                "UPDATE inventory_cost_state "
                "SET on_hand_qty = :q, avg_cost = :avg, updated_at = CURRENT_TIMESTAMP "
                "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
            ),
            {
                "tid": tenant_id,
                "wid": warehouse_id,
                "pid": product_id,
                "q": float(new_qty),
                "avg": float(_dec(new_avg, "0.000001")),
            },
        )

        return CostState(_dec(new_qty, "0.000001"), _dec(new_avg, "0.000001"))

    def apply_outbound(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        allow_negative: bool,
        initial_qty: Decimal | None = None,
        initial_avg_cost: Decimal | None = None,
    ) -> CostState:
        state = self._ensure_state_row(
            tenant_id,
            warehouse_id,
            product_id,
            initial_qty=initial_qty,
            initial_avg_cost=initial_avg_cost,
        )

        if not allow_negative and state.on_hand_qty < qty:
            raise HTTPException(status_code=400, detail="insufficient_stock")

        new_qty = state.on_hand_qty - qty
        self.db.execute(
            text(
                "UPDATE inventory_cost_state "
                "SET on_hand_qty = :q, updated_at = CURRENT_TIMESTAMP "
                "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
            ),
            {
                "tid": tenant_id,
                "wid": warehouse_id,
                "pid": product_id,
                "q": float(new_qty),
            },
        )

        return CostState(_dec(new_qty, "0.000001"), state.avg_cost)

    def _ensure_layers_table(self) -> None:
        """Create cost layers table if it doesn't exist (idempotent)."""
        # Rol de app NO-superuser: sin CREATE/ALTER en el esquema. Si la tabla ya
        # existe (dev/prod vía migración) no tocamos DDL. Crear/alterar tablas es
        # responsabilidad de las migraciones, no del runtime.
        from app.config.database import table_exists

        if table_exists(self.db, "inventory_cost_layers"):
            return
        self.db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS inventory_cost_layers ("
                "id SERIAL PRIMARY KEY, "
                "tenant_id TEXT NOT NULL, "
                "warehouse_id TEXT NOT NULL, "
                "product_id TEXT NOT NULL, "
                "lot TEXT NULL, "
                "expires_at DATE NULL, "
                "remaining_qty NUMERIC(14,6) NOT NULL, "
                "unit_cost NUMERIC(14,6) NOT NULL, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        for ddl in (
            "ALTER TABLE inventory_cost_layers ADD COLUMN IF NOT EXISTS lot TEXT NULL",
            "ALTER TABLE inventory_cost_layers ADD COLUMN IF NOT EXISTS expires_at DATE NULL",
        ):
            try:
                self.db.execute(text(ddl))
            except Exception:
                pass

    def _record_layer(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        unit_cost: Decimal,
        lot: str | None = None,
        expires_at: date | None = None,
    ) -> None:
        self._ensure_layers_table()
        self.db.execute(
            text(
                "INSERT INTO inventory_cost_layers "
                "(tenant_id, warehouse_id, product_id, lot, expires_at, remaining_qty, unit_cost, created_at) "
                "VALUES (:tid, :wid, :pid, :lot, :exp, :qty, :cost, :created_at)"
            ),
            {
                "tid": tenant_id,
                "wid": warehouse_id,
                "pid": product_id,
                "lot": _normalize_lot(lot),
                "exp": expires_at,
                "qty": float(qty),
                "cost": float(unit_cost),
                "created_at": datetime.now(UTC),
            },
        )

    def _consume_layers(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        order: Literal["fifo", "lifo"],
        allow_negative: bool = False,
        lot: str | None = None,
        expires_at: date | None = None,
    ) -> Decimal:
        self._ensure_layers_table()
        remaining = qty
        total_cogs = Decimal("0")
        order_sql = "ASC" if order == "fifo" else "DESC"
        clauses = [
            "tenant_id = :tid",
            "warehouse_id = :wid",
            "product_id = :pid",
            "remaining_qty > 0",
        ]
        params: dict[str, object] = {"tid": tenant_id, "wid": warehouse_id, "pid": product_id}
        if lot is not None:
            clauses.append("lot = :lot")
            params["lot"] = _normalize_lot(lot)
        if expires_at is not None:
            clauses.append("expires_at = :exp")
            params["exp"] = expires_at

        layers = self.db.execute(
            text(
                "SELECT id, remaining_qty, unit_cost "
                "FROM inventory_cost_layers "
                f"WHERE {' AND '.join(clauses)} "
                f"ORDER BY created_at {order_sql}, id {order_sql}"
            ),
            params,
        ).fetchall()

        for layer_id, layer_qty, layer_cost in layers:
            if remaining <= 0:
                break
            consume = min(remaining, Decimal(str(layer_qty)))
            total_cogs += consume * Decimal(str(layer_cost))
            remaining -= consume
            new_layer_qty = Decimal(str(layer_qty)) - consume
            self.db.execute(
                text("UPDATE inventory_cost_layers SET remaining_qty = :q WHERE id = :id"),
                {"q": float(new_layer_qty), "id": layer_id},
            )

        if remaining > 0 and not allow_negative:
            raise HTTPException(
                status_code=400,
                detail="insufficient_stock_fifo" if order == "fifo" else "insufficient_stock_lifo",
            )

        return _dec(total_cogs, "0.000001")

    def _layer_inventory_value(
        self,
        tenant_id: str,
        *,
        warehouse_id: str | None = None,
        order: Literal["fifo", "lifo"] = "fifo",
    ) -> Decimal:
        self._ensure_layers_table()
        order_sql = "ASC" if order == "fifo" else "DESC"
        clauses = [
            "tenant_id = :tid",
            "remaining_qty > 0",
        ]
        params: dict[str, object] = {"tid": tenant_id}
        if warehouse_id is not None:
            clauses.append("warehouse_id = :wid")
            params["wid"] = warehouse_id

        rows = self.db.execute(
            text(
                "SELECT remaining_qty, unit_cost "
                "FROM inventory_cost_layers "
                f"WHERE {' AND '.join(clauses)} "
                f"ORDER BY warehouse_id ASC, product_id ASC, created_at {order_sql}, id {order_sql}"
            ),
            params,
        ).fetchall()

        total = Decimal("0")
        for remaining_qty, unit_cost in rows:
            total += Decimal(str(remaining_qty or 0)) * Decimal(str(unit_cost or 0))
        return _dec(total, "0.000001")

    def apply_inbound_lifo(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        unit_cost: Decimal,
        lot: str | None = None,
        expires_at: date | None = None,
    ) -> CostState:
        """Record an inbound layer for LIFO costing."""
        self._record_layer(
            tenant_id,
            warehouse_id,
            product_id,
            qty=qty,
            unit_cost=unit_cost,
            lot=lot,
            expires_at=expires_at,
        )
        # Also update the summary state
        return self.apply_inbound(tenant_id, warehouse_id, product_id, qty=qty, unit_cost=unit_cost)

    def apply_inbound_fifo(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        unit_cost: Decimal,
        lot: str | None = None,
        expires_at: date | None = None,
    ) -> CostState:
        """Record an inbound layer for FIFO costing."""
        self._record_layer(
            tenant_id,
            warehouse_id,
            product_id,
            qty=qty,
            unit_cost=unit_cost,
            lot=lot,
            expires_at=expires_at,
        )
        return self.apply_inbound(tenant_id, warehouse_id, product_id, qty=qty, unit_cost=unit_cost)

    def apply_outbound_lifo(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        allow_negative: bool = False,
        lot: str | None = None,
        expires_at: date | None = None,
    ) -> tuple[CostState, Decimal]:
        """
        Consume stock using LIFO (last layer first).
        Returns (new_state, total_cogs).
        """
        total_cogs = self._consume_layers(
            tenant_id,
            warehouse_id,
            product_id,
            qty=qty,
            order="lifo",
            allow_negative=allow_negative,
            lot=lot,
            expires_at=expires_at,
        )

        # Update summary state
        state = self.apply_outbound(
            tenant_id, warehouse_id, product_id, qty=qty, allow_negative=allow_negative
        )
        return state, total_cogs

    def apply_outbound_fifo(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        *,
        qty: Decimal,
        allow_negative: bool = False,
        lot: str | None = None,
        expires_at: date | None = None,
    ) -> tuple[CostState, Decimal]:
        """
        Consume stock using FIFO (oldest layer first).
        Returns (new_state, total_cogs).
        """
        total_cogs = self._consume_layers(
            tenant_id,
            warehouse_id,
            product_id,
            qty=qty,
            order="fifo",
            allow_negative=allow_negative,
            lot=lot,
            expires_at=expires_at,
        )
        state = self.apply_outbound(
            tenant_id, warehouse_id, product_id, qty=qty, allow_negative=allow_negative
        )
        return state, total_cogs

    def get_inventory_value(
        self,
        tenant_id: str,
        *,
        warehouse_id: str | None = None,
        costing_method: Literal["avg", "fifo", "lifo"] = "avg",
    ) -> Decimal:
        """Calculate inventory value for a tenant using the requested costing method."""
        method = (costing_method or "avg").lower()
        if method == "avg":
            clauses = ["tenant_id = :tid"]
            params: dict[str, object] = {"tid": tenant_id}
            if warehouse_id is not None:
                clauses.append("warehouse_id = :wid")
                params["wid"] = warehouse_id
            row = self.db.execute(
                text(
                    "SELECT COALESCE(SUM(on_hand_qty * avg_cost), 0) "
                    "FROM inventory_cost_state "
                    f"WHERE {' AND '.join(clauses)}"
                ),
                params,
            ).scalar()
            return _dec(row, "0.000001")
        if method == "fifo":
            return self._layer_inventory_value(tenant_id, warehouse_id=warehouse_id, order="fifo")
        if method == "lifo":
            return self._layer_inventory_value(tenant_id, warehouse_id=warehouse_id, order="lifo")
        raise ValueError(f"Unsupported costing method: {costing_method}")
