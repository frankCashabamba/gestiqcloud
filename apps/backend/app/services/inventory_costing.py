from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


class CostState(NamedTuple):
    on_hand_qty: Decimal
    avg_cost: Decimal


def _dec(value: float | Decimal | None, q: str) -> Decimal:
    if value is None:
        value = 0
    return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)


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
        self.db.execute(
            text(
                "INSERT INTO inventory_cost_state("
                "tenant_id, warehouse_id, product_id, on_hand_qty, avg_cost"
                ") VALUES (:tid, :wid, :pid, :q, :avg) "
                "ON CONFLICT (tenant_id, warehouse_id, product_id) DO NOTHING"
            ),
            {
                "tid": tenant_id,
                "wid": warehouse_id,
                "pid": product_id,
                "q": float(initial_qty or Decimal("0")),
                "avg": float(initial_avg_cost or Decimal("0")),
            },
        )

        row = self.db.execute(
            text(
                "SELECT on_hand_qty, avg_cost "
                "FROM inventory_cost_state "
                "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid "
                "FOR UPDATE"
            ),
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
                "SET on_hand_qty = :q, avg_cost = :avg, updated_at = now() "
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
                "SET on_hand_qty = :q, updated_at = now() "
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
