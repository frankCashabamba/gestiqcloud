"""
INVENTORY MODULE: Use Cases para gestión de stock.

Implementa:
- Almacenes (warehouses)
- Movimientos de stock (entrada/salida)
- Valorización de inventario (FIFO/LIFO)
- Alertas de stock bajo
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.services.inventory_costing import InventoryCostingService

logger = logging.getLogger(__name__)


class StockMoveType(str, Enum):
    """Tipos de movimiento de stock."""

    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    RETURN = "return"


class Costing(str, Enum):
    """Métodos de valuación."""

    FIFO = "fifo"
    LIFO = "lifo"
    AVG = "avg"


class CreateWarehouseUseCase:
    """Crea almacén."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        *,
        name: str,
        code: str,
        tenant_id: UUID,
        location: str | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        existing = self.db.execute(
            text("SELECT id FROM warehouses WHERE code = :code AND tenant_id = :tid").bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True))
            ),
            {"code": code, "tid": tenant_id},
        ).first()
        if existing:
            raise ValueError("warehouse_code_already_exists")

        row = self.db.execute(
            text(
                "INSERT INTO warehouses(tenant_id, name, code, location, is_default, active) "
                "VALUES (:tid, :name, :code, :location, :is_default, true) RETURNING id, created_at"
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {
                "tid": tenant_id,
                "name": name,
                "code": code,
                "location": location,
                "is_default": is_default,
            },
        ).first()

        return {
            "warehouse_id": row[0],
            "name": name,
            "code": code,
            "location": location,
            "is_default": is_default,
            "is_active": True,
            "created_at": row[1] if row[1] else datetime.now(UTC),
        }


class ReceiveStockUseCase:
    """Recibe stock de compra (entrada a almacén)."""

    def __init__(self, db: Session, costing: InventoryCostingService):
        self.db = db
        self.costing = costing

    def execute(
        self,
        *,
        warehouse_id: UUID,
        tenant_id: UUID,
        purchase_order_id: UUID | None = None,
        lines: list[dict[str, Any]],
        costing_method: str = "avg",
    ) -> dict[str, Any]:
        total_cost = Decimal("0")
        received = 0

        for line in lines:
            product_id = str(line["product_id"])
            qty = Decimal(str(line.get("qty", 0)))
            unit_cost = Decimal(str(line.get("unit_cost", 0)))

            if qty <= 0:
                continue

            if costing_method == "fifo":
                self.costing.apply_inbound_fifo(
                    str(tenant_id),
                    str(warehouse_id),
                    product_id,
                    qty=qty,
                    unit_cost=unit_cost,
                    lot=line.get("lot"),
                    expires_at=line.get("expires_at"),
                )
            elif costing_method == "lifo":
                self.costing.apply_inbound_lifo(
                    str(tenant_id),
                    str(warehouse_id),
                    product_id,
                    qty=qty,
                    unit_cost=unit_cost,
                    lot=line.get("lot"),
                    expires_at=line.get("expires_at"),
                )
            else:
                self.costing.apply_inbound(
                    str(tenant_id),
                    str(warehouse_id),
                    product_id,
                    qty=qty,
                    unit_cost=unit_cost,
                )

            # Update stock_items
            existing_si = self.db.execute(
                text(
                    "SELECT id, qty FROM stock_items "
                    "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {"tid": tenant_id, "wid": warehouse_id, "pid": line["product_id"]},
            ).first()

            if existing_si:
                new_qty = float(existing_si[1] or 0) + float(qty)
                self.db.execute(
                    text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                        bindparam("id", type_=PGUUID(as_uuid=True))
                    ),
                    {"q": new_qty, "id": existing_si[0]},
                )
            else:
                self.db.execute(
                    text(
                        "INSERT INTO stock_items(tenant_id, warehouse_id, product_id, qty) "
                        "VALUES (:tid, :wid, :pid, :q)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("wid", type_=PGUUID(as_uuid=True)),
                        bindparam("pid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "wid": warehouse_id,
                        "pid": line["product_id"],
                        "q": float(qty),
                    },
                )

            # Create stock_move
            self.db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, "
                    "tentative, posted, unit_cost, total_cost, occurred_at"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, 'purchase', 'purchase_order', :ref_id, "
                    "FALSE, TRUE, :uc, :tc, :occurred_at"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("ref_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "pid": line["product_id"],
                    "wid": warehouse_id,
                    "q": float(qty),
                    "ref_id": purchase_order_id,
                    "uc": float(unit_cost),
                    "tc": float(qty * unit_cost),
                    "occurred_at": datetime.now(UTC),
                },
            )

            total_cost += qty * unit_cost
            received += 1

        return {
            "warehouse_id": warehouse_id,
            "purchase_order_id": purchase_order_id,
            "lines_received": received,
            "total_cost": total_cost,
            "created_at": datetime.now(UTC),
        }


class AdjustStockUseCase:
    """Ajuste manual de stock (pérdida, daño, robo)."""

    def __init__(self, db: Session, costing: InventoryCostingService):
        self.db = db
        self.costing = costing

    def execute(
        self,
        *,
        warehouse_id: UUID,
        product_id: UUID,
        tenant_id: UUID,
        qty_adjustment: Decimal,
        reason: str,
    ) -> dict[str, Any]:
        if qty_adjustment > 0:
            self.costing.apply_inbound(
                str(tenant_id),
                str(warehouse_id),
                str(product_id),
                qty=qty_adjustment,
                unit_cost=Decimal("0"),
            )
        elif qty_adjustment < 0:
            self.costing.apply_outbound(
                str(tenant_id),
                str(warehouse_id),
                str(product_id),
                qty=abs(qty_adjustment),
                allow_negative=True,
            )

        # Update stock_items
        existing = self.db.execute(
            text(
                "SELECT id, qty FROM stock_items "
                "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("wid", type_=PGUUID(as_uuid=True)),
                bindparam("pid", type_=PGUUID(as_uuid=True)),
            ),
            {"tid": tenant_id, "wid": warehouse_id, "pid": product_id},
        ).first()

        new_qty = Decimal("0")
        if existing:
            new_qty = Decimal(str(existing[1] or 0)) + qty_adjustment
            self.db.execute(
                text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True))
                ),
                {"q": float(new_qty), "id": existing[0]},
            )

        # Create stock_move
        kind = "adjustment"
        self.db.execute(
            text(
                "INSERT INTO stock_moves("
                "tenant_id, product_id, warehouse_id, qty, kind, ref_type, "
                "tentative, posted, occurred_at"
                ") VALUES ("
                ":tid, :pid, :wid, :q, :kind, 'adjustment', FALSE, TRUE, :occurred_at"
                ")"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("pid", type_=PGUUID(as_uuid=True)),
                bindparam("wid", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "pid": product_id,
                "wid": warehouse_id,
                "q": float(abs(qty_adjustment)),
                "kind": kind,
                "occurred_at": datetime.now(UTC),
            },
        )

        return {
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "qty_adjustment": qty_adjustment,
            "new_qty": new_qty,
            "reason": reason,
            "created_at": datetime.now(UTC),
        }


class TransferStockUseCase:
    """Transfiere stock entre almacenes."""

    def __init__(self, db: Session, costing: InventoryCostingService):
        self.db = db
        self.costing = costing

    def execute(
        self,
        *,
        from_warehouse_id: UUID,
        to_warehouse_id: UUID,
        product_id: UUID,
        tenant_id: UUID,
        qty: Decimal,
    ) -> dict[str, Any]:
        if qty <= 0:
            raise ValueError("qty_must_be_positive")

        state = self.costing.apply_outbound(
            str(tenant_id),
            str(from_warehouse_id),
            str(product_id),
            qty=qty,
            allow_negative=False,
        )
        unit_cost = state.avg_cost

        self.costing.apply_inbound(
            str(tenant_id),
            str(to_warehouse_id),
            str(product_id),
            qty=qty,
            unit_cost=unit_cost,
        )

        # Update stock_items source
        src_si = self.db.execute(
            text(
                "SELECT id, qty FROM stock_items "
                "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("wid", type_=PGUUID(as_uuid=True)),
                bindparam("pid", type_=PGUUID(as_uuid=True)),
            ),
            {"tid": tenant_id, "wid": from_warehouse_id, "pid": product_id},
        ).first()
        if src_si:
            self.db.execute(
                text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True))
                ),
                {"q": float(Decimal(str(src_si[1] or 0)) - qty), "id": src_si[0]},
            )

        # Update stock_items destination
        dst_si = self.db.execute(
            text(
                "SELECT id, qty FROM stock_items "
                "WHERE tenant_id = :tid AND warehouse_id = :wid AND product_id = :pid"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("wid", type_=PGUUID(as_uuid=True)),
                bindparam("pid", type_=PGUUID(as_uuid=True)),
            ),
            {"tid": tenant_id, "wid": to_warehouse_id, "pid": product_id},
        ).first()
        if dst_si:
            self.db.execute(
                text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True))
                ),
                {"q": float(Decimal(str(dst_si[1] or 0)) + qty), "id": dst_si[0]},
            )
        else:
            self.db.execute(
                text(
                    "INSERT INTO stock_items(tenant_id, warehouse_id, product_id, qty) "
                    "VALUES (:tid, :wid, :pid, :q)"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {"tid": tenant_id, "wid": to_warehouse_id, "pid": product_id, "q": float(qty)},
            )

        now = datetime.now(UTC)
        for wid, kind in [(from_warehouse_id, "issue"), (to_warehouse_id, "receipt")]:
            self.db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, "
                    "tentative, posted, unit_cost, total_cost, occurred_at"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, :kind, 'transfer', FALSE, TRUE, :uc, :tc, :occurred_at"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "pid": product_id,
                    "wid": wid,
                    "q": float(qty),
                    "kind": kind,
                    "uc": float(unit_cost),
                    "tc": float(qty * unit_cost),
                    "occurred_at": now,
                },
            )

        return {
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "product_id": product_id,
            "qty": qty,
            "status": "completed",
            "created_at": now,
        }


class CalculateInventoryValueUseCase:
    """Calcula valor del inventario usando FIFO/LIFO/AVG."""

    def __init__(self, db: Session, costing: InventoryCostingService):
        self.db = db
        self.costing = costing

    def execute(
        self,
        *,
        tenant_id: UUID,
        warehouse_id: UUID | None = None,
        costing_method: Costing = Costing.AVG,
    ) -> dict[str, Any]:
        total_value = self.costing.get_inventory_value(
            str(tenant_id),
            warehouse_id=str(warehouse_id) if warehouse_id else None,
            costing_method=costing_method.value,
        )

        items_count = self.db.execute(
            text(
                "SELECT count(*) FROM stock_items WHERE tenant_id = :tid AND qty > 0"
                + (" AND warehouse_id = :wid" if warehouse_id else "")
            ),
            {"tid": str(tenant_id), **({"wid": str(warehouse_id)} if warehouse_id else {})},
        ).scalar()

        return {
            "warehouse_id": warehouse_id,
            "costing_method": costing_method.value,
            "total_value": total_value,
            "items_count": int(items_count or 0),
            "calculated_at": datetime.now(UTC),
        }


class GetLowStockAlertsUseCase:
    """Obtiene alertas de stock bajo."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        *,
        tenant_id: UUID,
        warehouse_id: UUID | None = None,
        threshold: Decimal = Decimal("5"),
    ) -> dict[str, Any]:
        wh_filter = ""
        params: dict[str, Any] = {"tid": tenant_id, "th": float(threshold)}
        if warehouse_id:
            wh_filter = "AND si.warehouse_id = :wid"
            params["wid"] = warehouse_id

        alerts = self.db.execute(
            text(
                f"SELECT si.product_id, p.name, si.qty, w.code AS warehouse "
                f"FROM stock_items si "
                f"JOIN products p ON p.id = si.product_id "
                f"JOIN warehouses w ON w.id = si.warehouse_id "
                f"WHERE si.tenant_id = :tid AND si.qty < :th AND si.qty >= 0 "
                f"{wh_filter} "
                f"ORDER BY si.qty ASC LIMIT 50"
            ),
            params,
        ).fetchall()

        alert_list = [
            {
                "product_id": str(a[0]),
                "product_name": a[1],
                "current_qty": float(a[2] or 0),
                "warehouse": a[3],
            }
            for a in alerts
        ]

        return {
            "alerts": alert_list,
            "total_alerts": len(alert_list),
        }
