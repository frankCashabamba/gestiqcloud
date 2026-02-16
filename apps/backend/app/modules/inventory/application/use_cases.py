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
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class StockMoveType(str, Enum):
    """Tipos de movimiento de stock."""

    PURCHASE = "purchase"  # Entrada por compra
    SALE = "sale"  # Salida por venta
    ADJUSTMENT = "adjustment"  # Ajuste manual
    TRANSFER = "transfer"  # Transferencia entre almacenes
    RETURN = "return"  # Devolución


class Costing(str, Enum):
    """Métodos de valuación."""

    FIFO = "fifo"  # First in, first out
    LIFO = "lifo"  # Last in, first out
    AVG = "avg"  # Promedio ponderado


class CreateWarehouseUseCase:
    """Crea almacén."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        name: str,
        code: str,
        location: str | None = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        """
        Crea almacén.

        Args:
            name: Warehouse name
            code: Warehouse code (unique)
            location: Physical location
            is_default: Mark as default warehouse

        Returns:
            {
                "warehouse_id": UUID,
                "name": str,
                "code": str,
                "is_active": bool,
                "created_at": datetime
            }
        """
        return {
            "warehouse_id": UUID(int=0),  # Set by repo
            "name": name,
            "code": code,
            "location": location,
            "is_default": is_default,
            "is_active": True,
            "created_at": datetime.utcnow(),
        }


class ReceiveStockUseCase:
    """Recibe stock de compra (entrada a almacén)."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        warehouse_id: UUID,
        purchase_order_id: UUID | None = None,
        lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Recibe stock desde compra.

        Por cada línea:
        1. Buscar/crear stock_item
        2. Actualizar qty + cost
        3. Crear stock_move (PURCHASE)
        4. Registrar FIFO/LIFO layers

        Args:
            warehouse_id: Warehouse ID
            purchase_order_id: PO ID (optional)
            lines: List of {product_id, qty, unit_cost}

        Returns:
            {
                "receipt_id": UUID,
                "warehouse_id": UUID,
                "lines_received": int,
                "total_cost": Decimal,
                "created_at": datetime
            }
        """
        total_cost = Decimal("0")
        for line in lines:
            qty = Decimal(str(line.get("qty", 0)))
            cost = Decimal(str(line.get("unit_cost", 0)))
            total_cost += qty * cost

        return {
            "receipt_id": UUID(int=0),  # Set by repo
            "warehouse_id": warehouse_id,
            "purchase_order_id": purchase_order_id,
            "lines_received": len(lines),
            "total_cost": total_cost,
            "created_at": datetime.utcnow(),
        }


class AdjustStockUseCase:
    """Ajuste manual de stock (pérdida, daño, robo)."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        warehouse_id: UUID,
        product_id: UUID,
        qty_adjustment: Decimal,
        reason: str,
    ) -> dict[str, Any]:
        """
        Realiza ajuste manual de stock.

        Casos:
        - qty_adjustment > 0: entrada
        - qty_adjustment < 0: salida

        Args:
            warehouse_id: Warehouse ID
            product_id: Product ID
            qty_adjustment: Cantidad a ajustar (puede ser negativa)
            reason: Motivo del ajuste (damage, loss, theft, etc)

        Returns:
            {
                "move_id": UUID,
                "warehouse_id": UUID,
                "product_id": UUID,
                "qty_adjustment": Decimal,
                "new_qty": Decimal,
                "reason": str,
                "created_at": datetime
            }
        """
        return {
            "move_id": UUID(int=0),  # Set by repo
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "qty_adjustment": qty_adjustment,
            "reason": reason,
            "created_at": datetime.utcnow(),
        }


class TransferStockUseCase:
    """Transfiere stock entre almacenes."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        from_warehouse_id: UUID,
        to_warehouse_id: UUID,
        product_id: UUID,
        qty: Decimal,
    ) -> dict[str, Any]:
        """
        Transfiere stock entre almacenes.

        Operación atómica:
        1. Validar qty disponible en origen
        2. Restar de origen
        3. Sumar a destino
        4. Crear moves TRANSFER en ambos

        Args:
            from_warehouse_id: Source warehouse
            to_warehouse_id: Destination warehouse
            product_id: Product ID
            qty: Quantity to transfer

        Returns:
            {
                "transfer_id": UUID,
                "from_warehouse_id": UUID,
                "to_warehouse_id": UUID,
                "product_id": UUID,
                "qty": Decimal,
                "status": "completed",
                "created_at": datetime
            }
        """
        return {
            "transfer_id": UUID(int=0),  # Set by repo
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "product_id": product_id,
            "qty": qty,
            "status": "completed",
            "created_at": datetime.utcnow(),
        }


class CalculateInventoryValueUseCase:
    """Calcula valor del inventario usando FIFO/LIFO."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        warehouse_id: UUID | None = None,
        costing_method: Costing = Costing.FIFO,
    ) -> dict[str, Any]:
        """
        Calcula valor total del inventario.

        Por cada stock_item:
        1. Aplicar método de valuación (FIFO/LIFO/AVG)
        2. Calcular costo unitario
        3. Multiplicar por qty
        4. Sumar todo

        Args:
            warehouse_id: Warehouse ID (None = all)
            costing_method: FIFO, LIFO, or AVG

        Returns:
            {
                "warehouse_id": UUID | None,
                "costing_method": str,
                "total_value": Decimal,
                "items_count": int,
                "calculated_at": datetime
            }
        """
        return {
            "warehouse_id": warehouse_id,
            "costing_method": costing_method.value,
            "total_value": Decimal("0"),
            "items_count": 0,
            "calculated_at": datetime.utcnow(),
        }


class GetLowStockAlertsUseCase:
    """Obtiene alertas de stock bajo."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        warehouse_id: UUID | None = None,
        threshold_pct: int = 20,
    ) -> dict[str, Any]:
        """
        Obtiene productos con stock bajo.

        Productos donde qty < (min_qty * threshold_pct / 100)

        Args:
            warehouse_id: Warehouse ID (None = all)
            threshold_pct: Alert threshold percentage (default 20%)

        Returns:
            {
                "alerts": [
                    {
                        "product_id": UUID,
                        "product_name": str,
                        "current_qty": Decimal,
                        "min_qty": Decimal,
                        "warehouse": str
                    }
                ],
                "total_alerts": int
            }
        """
        return {
            "alerts": [],
            "total_alerts": 0,
        }
