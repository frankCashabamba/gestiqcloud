from __future__ import annotations

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from psycopg2.extras import Json
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.modules.settings.infrastructure.repositories import SettingsRepo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# UTILIDADES
# ============================================================================


def _get_tenant_id(request: Request) -> UUID:
    """Obtiene tenant_id como UUID (evita casts en SQL)."""
    claims = getattr(request.state, "access_claims", {}) or {}
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="Claims invÃ¡lidos")

    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID no encontrado")

    try:
        return UUID(str(tenant_id))
    except Exception:
        raise HTTPException(status_code=401, detail="Tenant ID invÃ¡lido")


def _get_user_id(request: Request) -> UUID:
    """Obtiene user_id como UUID desde los claims (sin casts en SQL)."""
    claims = getattr(request.state, "access_claims", {}) or {}
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="Claims invÃ¡lidos")

    user_id = claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    try:
        return UUID(str(user_id))
    except Exception:
        raise HTTPException(status_code=401, detail="User ID invÃ¡lido")


def _validate_uuid(value: str, field_name: str = "ID") -> UUID:
    """Valida y convierte un string a UUID"""
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=400, detail=f"{field_name} invÃ¡lido: debe ser un UUID vÃ¡lido"
        )


def _to_decimal(value: float) -> Decimal:
    """Convierte float a Decimal con 2 decimales"""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = None
    default_warehouse_id: str | None = None
    metadata: dict | None = None

    @field_validator("default_warehouse_id")
    @classmethod
    def validate_warehouse_id(cls, v):
        if v is not None:
            _validate_uuid(v, "Warehouse ID")
        return v


class OpenShiftIn(BaseModel):
    register_id: str
    opening_float: float = Field(ge=0, description="Monto inicial debe ser >= 0")

    @field_validator("register_id")
    @classmethod
    def validate_register_id(cls, v):
        _validate_uuid(v, "Register ID")
        return v


class ReceiptLineIn(BaseModel):
    product_id: str
    qty: float = Field(gt=0, description="Cantidad debe ser > 0")
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0, le=1, default=0)
    discount_pct: float = Field(ge=0, le=100, default=0)
    uom: str = Field(default="unit", max_length=20)

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v):
        _validate_uuid(v, "Product ID")
        return v

    @property
    def line_total(self) -> float:
        """Calcula el total de la lÃ­nea"""
        subtotal = self.qty * self.unit_price
        discount = subtotal * (self.discount_pct / 100)
        return subtotal - discount


class PaymentIn(BaseModel):
    method: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0, description="Monto debe ser > 0")
    ref: str | None = Field(default=None, max_length=200)


class ReceiptCreateIn(BaseModel):
    shift_id: str
    register_id: str
    lines: list[ReceiptLineIn] = Field(default_factory=list)
    payments: list[PaymentIn] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("shift_id", "register_id")
    @classmethod
    def validate_ids(cls, v):
        _validate_uuid(v, "ID")
        return v


def _resolve_default_tax_rate(db: Session) -> float | None:
    """Obtiene la tasa por defecto desde settings, si existe.

    Busca claves conocidas: 'pos.tax.default_rate' o 'fiscal.tax.default_rate'.
    Devuelve None si no hay configuración; en ese caso no se fuerza nada.
    """
    try:
        repo = SettingsRepo(db)
        pos_cfg = repo.get("pos") or {}
        fiscal_cfg = repo.get("fiscal") or {}
        dr = ((pos_cfg.get("tax") or {}).get("default_rate")) if isinstance(pos_cfg, dict) else None
        if dr is None:
            dr = (
                ((fiscal_cfg.get("tax") or {}).get("default_rate"))
                if isinstance(fiscal_cfg, dict)
                else None
            )
        try:
            if dr is None:
                return None
            drf = float(dr)
            if drf < 0:
                drf = 0.0
            if drf > 1:
                drf = drf / 100.0
            return drf
        except Exception:
            return None
    except Exception:
        return None


def _is_tax_enabled(db: Session) -> bool:
    """Lee un flag de settings para habilitar/deshabilitar impuestos.

    Prioriza `pos.tax.enabled`; si no existe, intenta `fiscal.tax.enabled`.
    Si no hay configuración, asume True (habilitado) para no sorprender.
    """
    try:
        repo = SettingsRepo(db)
        pos_cfg = repo.get("pos") or {}
        fiscal_cfg = repo.get("fiscal") or {}

        def to_bool(val) -> bool | None:
            try:
                if isinstance(val, bool):
                    return val
                if isinstance(val, int | float):
                    return bool(int(val))
                if isinstance(val, str):
                    v = val.strip().lower()
                    if v in ("true", "1", "yes", "on"):
                        return True
                    if v in ("false", "0", "no", "off"):
                        return False
                return None
            except Exception:
                return None

        v = (
            to_bool((pos_cfg.get("tax") or {}).get("enabled"))
            if isinstance(pos_cfg, dict)
            else None
        )
        if v is None:
            v = (
                to_bool((fiscal_cfg.get("tax") or {}).get("enabled"))
                if isinstance(fiscal_cfg, dict)
                else None
            )
        return True if v is None else bool(v)
    except Exception:
        return True


class CheckoutIn(BaseModel):
    payments: list[PaymentIn] = Field(min_length=1)
    warehouse_id: str | None = None

    @field_validator("warehouse_id")
    @classmethod
    def validate_warehouse_id(cls, v):
        if v is not None:
            _validate_uuid(v, "Warehouse ID")
        return v


class CloseShiftIn(BaseModel):
    closing_cash: float = Field(ge=0)
    loss_amount: float | None = 0.0
    loss_note: str | None = None


class CalculateTotalsLineIn(BaseModel):
    """Línea para cálculo de totales (sin persistir)"""

    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0, le=1, default=0)
    discount_pct: float = Field(ge=0, le=100, default=0)


class CalculateTotalsIn(BaseModel):
    """Request para cálculo de totales de recibo"""

    lines: list[CalculateTotalsLineIn]
    global_discount_pct: float = Field(ge=0, le=100, default=0)


class CalculateTotalsOut(BaseModel):
    """Response con totales calculados"""

    subtotal: float
    line_discounts: float
    global_discount: float
    base_after_discounts: float
    tax: float
    total: float


class ItemIn(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax: float | None = Field(default=None, ge=0)


class RemoveItemIn(BaseModel):
    item_id: int


class PaymentsIn(BaseModel):
    payments: list[PaymentIn]


class PostReceiptIn(BaseModel):
    warehouse_id: str | None = None

    @field_validator("warehouse_id")
    @classmethod
    def validate_warehouse_id(cls, v):
        if v is not None:
            _validate_uuid(v, "Warehouse ID")
        return v


# ============================================================================
# ENDPOINTS - REGISTERS
# ============================================================================


@router.get("/registers", response_model=list[dict])
def list_registers(request: Request, db: Session = Depends(get_db)):
    """Lista todos los registros POS del tenant actual"""
    ensure_guc_from_request(request, db, persist=True)

    try:
        rows = db.execute(
            text(
                "SELECT id, name, store_id, active, created_at "
                "FROM pos_registers "
                "ORDER BY created_at DESC"
            )
        ).fetchall()

        return [
            {
                "id": str(r[0]),
                "name": r[1],
                "store_id": str(r[2]) if r[2] else None,
                "active": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar registros: {str(e)}")


@router.post("/registers", response_model=dict, status_code=201)
def create_register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    """Crea un nuevo registro POS (baseline moderno)."""
    ensure_guc_from_request(request, db, persist=True)
    tid = _get_tenant_id(request)

    try:
        row = db.execute(
            text(
                "INSERT INTO pos_registers(tenant_id, name, active) "
                "VALUES (:tid, :name, TRUE) RETURNING id"
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": tid, "name": payload.name},
        ).first()

        db.commit()
        return {"id": str(row[0])}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear registro: {str(e)}")


# ============================================================================
# ENDPOINTS - SHIFTS
# ============================================================================


@router.post("/shifts", response_model=dict)
@router.post("/open_shift", response_model=dict, deprecated=True)
def open_shift(payload: OpenShiftIn, request: Request, db: Session = Depends(get_db)):
    """Abre un nuevo turno en un registro POS"""
    ensure_guc_from_request(request, db, persist=True)

    user_id = _get_user_id(request)
    register_uuid = _validate_uuid(payload.register_id, "Register ID")

    try:
        # Verificar que el registro existe y estÃ¡ activo
        register = db.execute(
            text("SELECT active FROM pos_registers WHERE id = :rid").bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True))
            ),
            {"rid": register_uuid},
        ).first()

        if not register:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        if not register[0]:
            raise HTTPException(status_code=400, detail="El registro estÃ¡ inactivo")

        # Verificar que no hay un turno abierto
        existing = db.execute(
            text(
                "SELECT id FROM pos_shifts WHERE register_id = :rid AND status = 'open' FOR UPDATE"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": register_uuid},
        ).first()

        if existing:
            raise HTTPException(
                status_code=400, detail="Ya existe un turno abierto para este registro"
            )

        # Insertar turno
        row = db.execute(
            text(
                "INSERT INTO pos_shifts(register_id, opened_by, opening_float, status) "
                "VALUES (:rid, :opened_by, :opening_float, 'open') "
                "RETURNING id"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("opened_by", type_=PGUUID(as_uuid=True)),
            ),
            {
                "rid": register_uuid,
                "opened_by": user_id,
                "opening_float": payload.opening_float,
            },
        ).first()

        db.commit()
        return {"id": str(row[0]), "status": "open"}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al abrir turno: {str(e)}")


@router.get("/shifts/{shift_id}/summary", response_model=dict)
def get_shift_summary(
    shift_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Obtiene resumen del turno: ventas, productos vendidos y stock restante"""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = _validate_uuid(shift_id, "Shift ID")

    try:
        # Verificar recibos pendientes (draft o unpaid)
        pending_receipts = db.execute(
            text(
                "SELECT COUNT(*) FROM pos_receipts "
                "WHERE shift_id = :sid AND status IN ('draft', 'unpaid')"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).scalar()

        # Productos vendidos
        items_sold = db.execute(
            text(
                "SELECT rl.product_id, p.name, p.code, "
                "SUM(rl.qty) as qty_sold, "
                "SUM(rl.qty * rl.unit_price * (1 - rl.discount_pct/100)) as subtotal "
                "FROM pos_receipt_lines rl "
                "JOIN pos_receipts r ON r.id = rl.receipt_id "
                "LEFT JOIN products p ON p.id = rl.product_id "
                "WHERE r.shift_id = :sid AND r.status = 'paid' "
                "GROUP BY rl.product_id, p.name, p.code "
                "ORDER BY p.name"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).fetchall()

        # Obtener IDs de productos vendidos
        product_ids = [row[0] for row in items_sold if row[0]]

        # Stock restante
        stock_items = {}
        if product_ids:
            stock_rows = db.execute(
                text(
                    "SELECT si.product_id, si.warehouse_id, w.name as warehouse_name, si.qty "
                    "FROM stock_items si "
                    "LEFT JOIN warehouses w ON w.id = si.warehouse_id "
                    "WHERE si.product_id = ANY(:product_ids)"
                ),
                {"product_ids": product_ids},
            ).fetchall()

            for row in stock_rows:
                pid = str(row[0])
                if pid not in stock_items:
                    stock_items[pid] = []
                stock_items[pid].append(
                    {
                        "warehouse_id": str(row[1]),
                        "warehouse_name": row[2],
                        "qty": float(row[3] or 0),
                    }
                )

        # Formatear productos vendidos con stock
        items = []
        for row in items_sold:
            pid = str(row[0]) if row[0] else None
            items.append(
                {
                    "product_id": pid,
                    "name": row[1],
                    "code": row[2],
                    "qty_sold": float(row[3] or 0),
                    "subtotal": float(row[4] or 0),
                    "stock": stock_items.get(pid, []) if pid else [],
                }
            )

        # Totales de ventas
        sales_total = db.execute(
            text(
                "SELECT COALESCE(SUM(gross_total), 0) "
                "FROM pos_receipts WHERE shift_id = :sid AND status = 'paid'"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).scalar()

        return {
            "pending_receipts": pending_receipts or 0,
            "items_sold": items,
            "sales_total": float(sales_total or 0),
            "receipts_count": len(items_sold),
        }

    except Exception as e:
        logger.error(f"Error getting shift summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


@router.post("/shifts/{shift_id}/close", response_model=dict)
def close_shift(
    shift_id: str,
    payload: CloseShiftIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cierra un turno POS"""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = _validate_uuid(shift_id, "Shift ID")

    try:
        # Verificar que el turno existe y estÃ¡ abierto
        shift = db.execute(
            text("SELECT status FROM pos_shifts WHERE id = :sid FOR UPDATE").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True))
            ),
            {"sid": shift_uuid},
        ).first()

        if not shift:
            raise HTTPException(status_code=404, detail="Turno no encontrado")

        if shift[0] != "open":
            raise HTTPException(status_code=400, detail="El turno ya estÃ¡ cerrado")

        # Verificar recibos pendientes
        pending = db.execute(
            text(
                "SELECT COUNT(*) FROM pos_receipts "
                "WHERE shift_id = :sid AND status IN ('draft', 'unpaid')"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).scalar()

        if pending and pending > 0:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cerrar el turno. Hay {pending} recibo(s) sin cobrar/terminar.",
            )

        # Obtener datos del turno para el reporte diario
        shift_data = db.execute(
            text(
                "SELECT ps.register_id, ps.opened_at, ps.opening_float, pr.tenant_id "
                "FROM pos_shifts ps "
                "JOIN pos_registers pr ON pr.id = ps.register_id "
                "WHERE ps.id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).first()

        if not shift_data:
            raise HTTPException(status_code=404, detail="Datos del turno no encontrados")

        register_id = shift_data[0]
        opened_at = shift_data[1]
        opening_float = float(shift_data[2] or 0)
        tenant_id = shift_data[3]

        # Calcular totales de ventas por método de pago
        sales_by_method = db.execute(
            text(
                "SELECT pp.method, COALESCE(SUM(pp.amount), 0) as total "
                "FROM pos_payments pp "
                "JOIN pos_receipts pr ON pr.id = pp.receipt_id "
                "WHERE pr.shift_id = :sid AND pr.status = 'paid' "
                "GROUP BY pp.method"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).fetchall()

        cash_sales = 0
        card_sales = 0
        other_sales = 0
        total_sales = 0

        for method, amount in sales_by_method:
            total_sales += float(amount)
            if method.lower() == "cash":
                cash_sales = float(amount)
            elif method.lower() in ("card", "credit", "debit"):
                card_sales = float(amount)
            else:
                other_sales += float(amount)

        expected_cash = opening_float + cash_sales

        # Cerrar turno
        db.execute(
            text(
                "UPDATE pos_shifts "
                "SET status = 'closed', closed_at = NOW(), closing_total = :ct "
                "WHERE id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid, "ct": payload.closing_cash},
        )

        # Guardar reporte diario
        count_date = opened_at.date() if opened_at else datetime.utcnow().date()

        db.execute(
            text(
                "INSERT INTO pos_daily_counts "
                "(tenant_id, register_id, shift_id, count_date, opening_float, "
                "cash_sales, card_sales, other_sales, total_sales, expected_cash, "
                "counted_cash, discrepancy, loss_amount, loss_note) "
                "VALUES (:tid, :rid, :sid, :cd, :of, :cs, :cars, :os, :ts, :ec, :cc, :disc, :la, :ln)"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("sid", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "rid": register_id,
                "sid": shift_uuid,
                "cd": count_date,
                "of": opening_float,
                "cs": cash_sales,
                "cars": card_sales,
                "os": other_sales,
                "ts": total_sales,
                "ec": expected_cash,
                "cc": payload.closing_cash,
                "disc": payload.closing_cash - expected_cash,
                "la": payload.loss_amount or 0,
                "ln": payload.loss_note,
            },
        )

        db.commit()

        diff = payload.closing_cash - expected_cash

        return {
            "status": "closed",
            "expected_cash": expected_cash,
            "counted_cash": payload.closing_cash,
            "difference": diff,
            "total_sales": total_sales,
            "cash_sales": cash_sales,
            "card_sales": card_sales,
            "loss_amount": payload.loss_amount or 0,
            "loss_note": payload.loss_note,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al cerrar turno: {str(e)}")


@router.get("/shifts", response_model=list[dict])
def list_shifts(
    request: Request,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    """Lista turnos POS con filtros opcionales"""
    ensure_guc_from_request(request, db, persist=True)

    sql_parts = [
        "SELECT id, register_id, opened_at, closed_at, opening_float, closing_cash, status, opened_by "
        "FROM pos_shifts WHERE 1=1"
    ]
    params = {}

    if status:
        sql_parts.append("AND status = :st")
        params["st"] = status

    if since:
        sql_parts.append("AND opened_at >= :since")
        params["since"] = since

    if until:
        sql_parts.append("AND opened_at <= :until")
        params["until"] = until

    sql_parts.append(f"ORDER BY opened_at DESC LIMIT {min(limit, 1000)}")

    try:
        rows = db.execute(text(" ".join(sql_parts)), params).fetchall()

        return [
            {
                "id": str(r[0]),
                "register_id": str(r[1]),
                "opened_at": r[2].isoformat() if r[2] else None,
                "closed_at": r[3].isoformat() if r[3] else None,
                "opening_float": float(r[4]) if r[4] else 0,
                "closing_cash": float(r[5]) if r[5] else None,
                "status": r[6],
                "opened_by": str(r[7]),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar turnos: {str(e)}")


@router.get("/shifts/{shift_id}/summary", response_model=dict)
def shift_summary(shift_id: str, request: Request, db: Session = Depends(get_db)):
    """Resumen de un turno POS"""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = _validate_uuid(shift_id, "Shift ID")

    try:
        # Totales por mÃ©todo de pago
        payments = db.execute(
            text(
                "SELECT pp.method, COALESCE(SUM(pp.amount), 0) AS amount "
                "FROM pos_payments pp "
                "JOIN pos_receipts pr ON pr.id = pp.receipt_id "
                "WHERE pr.shift_id = :sid "
                "GROUP BY pp.method "
                "ORDER BY amount DESC"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).fetchall()

        # Conteo de recibos
        receipts = db.execute(
            text(
                "SELECT "
                "COUNT(*) FILTER (WHERE status = 'paid') AS paid, "
                "COUNT(*) FILTER (WHERE status = 'draft') AS draft "
                "FROM pos_receipts WHERE shift_id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).first()

        # Totales
        totals = db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(gross_total), 0) AS gross, "
                "COALESCE(SUM(tax_total), 0) AS tax "
                "FROM pos_receipts "
                "WHERE shift_id = :sid AND status = 'paid'"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).first()

        return {
            "shift_id": shift_id,
            "receipts": {"paid": int(receipts[0] or 0), "draft": int(receipts[1] or 0)},
            "payments": [{"method": p[0], "amount": float(p[1])} for p in payments],
            "totals": {
                "gross": float(totals[0] or 0),
                "tax": float(totals[1] or 0),
                "total": float((totals[0] or 0) + (totals[1] or 0)),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


# ============================================================================
# ENDPOINTS - RECEIPTS
# ============================================================================


@router.post("/receipts/calculate_totals", response_model=CalculateTotalsOut)
def calculate_receipt_totals(payload: CalculateTotalsIn):
    """
    Calcula los totales de un recibo sin persistirlo.

    Este endpoint permite al frontend obtener cálculos precisos antes de crear el recibo,
    garantizando consistencia entre la UI y el backend.

    **Algoritmo:**
    1. Calcula subtotal por línea: qty * unit_price
    2. Aplica descuento por línea: subtotal * (discount_pct / 100)
    3. Suma descuentos de todas las líneas
    4. Aplica descuento global sobre el subtotal después de descuentos de línea
    5. Calcula impuestos sobre base neta (después de todos los descuentos)
    6. Total = base + impuestos

    Usa Decimal para evitar errores de redondeo.
    """
    if not payload.lines:
        return CalculateTotalsOut(
            subtotal=0.0,
            line_discounts=0.0,
            global_discount=0.0,
            base_after_discounts=0.0,
            tax=0.0,
            total=0.0,
        )

    # Convertir todo a Decimal para precisión
    subtotal = Decimal("0")
    line_discounts = Decimal("0")
    tax_total = Decimal("0")

    for line in payload.lines:
        # Subtotal de línea
        line_subtotal = _to_decimal(line.qty) * _to_decimal(line.unit_price)
        subtotal += line_subtotal

        # Descuento de línea
        line_discount = line_subtotal * (_to_decimal(line.discount_pct) / Decimal("100"))
        line_discounts += line_discount

        # Base neta de línea (después de descuento)
        line_net = line_subtotal - line_discount

        # Impuesto sobre base neta de línea
        line_tax = line_net * _to_decimal(line.tax_rate)
        tax_total += line_tax

    # Base después de descuentos de línea
    base_after_line_discounts = subtotal - line_discounts

    # Descuento global sobre base
    global_discount = base_after_line_discounts * (
        _to_decimal(payload.global_discount_pct) / Decimal("100")
    )

    # Base final después de todos los descuentos
    base_after_all_discounts = base_after_line_discounts - global_discount

    # Total final
    total = base_after_all_discounts + tax_total

    return CalculateTotalsOut(
        subtotal=float(subtotal),
        line_discounts=float(line_discounts),
        global_discount=float(global_discount),
        base_after_discounts=float(base_after_all_discounts),
        tax=float(tax_total),
        total=float(total),
    )


@router.post("/receipts", response_model=dict, status_code=201)
def create_receipt(payload: ReceiptCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea un nuevo recibo POS"""
    ensure_guc_from_request(request, db, persist=True)

    tenant_id = _get_tenant_id(request)
    shift_uuid = _validate_uuid(payload.shift_id, "Shift ID")
    register_uuid = _validate_uuid(payload.register_id, "Register ID")

    try:
        # Verificar que el turno existe y estÃ¡ abierto
        shift = db.execute(
            text("SELECT status FROM pos_shifts WHERE id = :sid AND register_id = :rid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "rid": register_uuid},
        ).first()

        if not shift:
            raise HTTPException(status_code=404, detail="Turno no encontrado")

        if shift[0] != "open":
            raise HTTPException(status_code=400, detail="El turno no estÃ¡ abierto")

        # Generar nÃºmero de ticket usando secuencia atÃ³mica
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"{tenant_id}-{register_uuid}-POS_R"},
        )

        ticket_number = db.execute(
            text(
                "SELECT COALESCE(MAX("
                "CASE WHEN SPLIT_PART(number, '-', 2) ~ '^[0-9]+$' "
                "THEN (SPLIT_PART(number, '-', 2))::int ELSE 0 END"
                "), 0) + 1 "
                "FROM pos_receipts "
                "WHERE tenant_id = :tid AND register_id = :rid"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
            ),
            {"tid": tenant_id, "rid": register_uuid},
        ).scalar()

        ticket_number = f"R-{ticket_number:04d}"

        # Crear el recibo
        row = db.execute(
            text(
                "INSERT INTO pos_receipts("
                "tenant_id, register_id, shift_id, number, status, "
                "gross_total, tax_total, currency"
                ") VALUES ("
                ":tid, :rid, :sid, :number, 'draft', "
                "0, 0, 'EUR'"
                ") RETURNING id"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("sid", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "rid": register_uuid,
                "sid": shift_uuid,
                "number": ticket_number,
            },
        ).first()

        receipt_id = row[0]

        # Commit the receipt insertion to make it visible for RLS policies
        db.commit()

        # Insertar lÃ­neas
        # Resolver configuración fiscal del tenant
        tax_enabled = _is_tax_enabled(db)
        default_tax = _resolve_default_tax_rate(db)

        for line in payload.lines:
            product_uuid = _validate_uuid(line.product_id, "Product ID")

            # Resolver tasa efectiva considerando configuración
            tax_rate = line.tax_rate

            # Deshabilitado globalmente → siempre 0
            if not tax_enabled:
                tax_rate = 0.0
            else:
                # Si hay default, respétalo
                if default_tax is not None:
                    if default_tax <= 0:
                        tax_rate = 0.0
                    else:
                        tax_rate = default_tax
                # Normalizar si viniera en porcentaje entero
                if tax_rate is not None and tax_rate > 1:
                    tax_rate = tax_rate / 100.0

            db.execute(
                text(
                    "INSERT INTO pos_receipt_lines("
                    "receipt_id, product_id, qty, unit_price, tax_rate, "
                    "discount_pct, line_total, uom"
                    ") VALUES ("
                    ":receipt_id, :product_id, :qty, :unit_price, :tax_rate, "
                    ":discount_pct, :line_total, :uom"
                    ")"
                ).bindparams(
                    bindparam("receipt_id", type_=PGUUID(as_uuid=True)),
                    bindparam("product_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "receipt_id": receipt_id,
                    "product_id": product_uuid,
                    "qty": line.qty,
                    "unit_price": line.unit_price,
                    "tax_rate": tax_rate,
                    "discount_pct": line.discount_pct,
                    "line_total": line.line_total,
                    "uom": line.uom,
                },
            )

        db.commit()
        return {"id": str(receipt_id), "number": ticket_number}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error al crear recibo")
        raise HTTPException(status_code=500, detail=f"Error al crear recibo: {str(e)}")


@router.post("/receipts/{receipt_id}/checkout", response_model=dict)
def checkout(
    receipt_id: str,
    payload: CheckoutIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Registra pagos y descuenta stock en una transacciÃ³n atÃ³mica"""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        # 1. Validar estado del recibo
        receipt = db.execute(
            text("SELECT shift_id, status FROM pos_receipts WHERE id = :id FOR UPDATE").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": receipt_uuid},
        ).first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")

        if receipt[1] != "draft":
            raise HTTPException(
                status_code=400,
                detail=f"Recibo en estado '{receipt[1]}', debe estar en 'draft'",
            )

        # 2. Insertar pagos
        for payment in payload.payments:
            db.execute(
                text(
                    "INSERT INTO pos_payments(receipt_id, method, amount, ref) "
                    "VALUES (:rid, :m, :a, :ref)"
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {
                    "rid": receipt_uuid,
                    "m": payment.method,
                    "a": payment.amount,
                    "ref": payment.ref,
                },
            )

        # 3. Calcular totales
        totals = db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(rl.qty * rl.unit_price * (1 - rl.discount_pct/100)), 0) AS subtotal, "
                "COALESCE(SUM(rl.qty * rl.unit_price * (1 - rl.discount_pct/100) * rl.tax_rate), 0) AS tax "
                "FROM pos_receipt_lines rl "
                "WHERE rl.receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()

        payments_total = db.execute(
            text(
                "SELECT COALESCE(SUM(amount), 0) FROM pos_payments WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()

        # Convertir a Decimal para precisiÃ³n
        subtotal = _to_decimal(float(totals[0] or 0))
        tax = _to_decimal(float(totals[1] or 0))

        # Aplicar configuración fiscal del tenant (override)
        tax_enabled = _is_tax_enabled(db)
        default_tax = _resolve_default_tax_rate(db)
        if not tax_enabled or (default_tax is not None and default_tax <= 0):
            tax = _to_decimal(0.0)

        total = subtotal + tax
        paid = _to_decimal(float(payments_total[0] or 0))

        # Validar pago suficiente (comparar en centavos)
        if int(paid * 100) < int(total * 100):
            raise HTTPException(
                status_code=400,
                detail=f"Pago insuficiente. Recibido: ${paid:.2f}, Requerido: ${total:.2f}",
            )

        # 4. Determinar almacÃ©n
        warehouse_id = payload.warehouse_id

        if warehouse_id:
            warehouse_uuid = _validate_uuid(warehouse_id, "Warehouse ID")
        else:
            # Buscar almacÃ©n Ãºnico activo
            warehouses = db.execute(
                text("SELECT id FROM warehouses WHERE active = true LIMIT 2")
            ).fetchall()

            if len(warehouses) == 0:
                raise HTTPException(status_code=400, detail="No hay almacenes activos disponibles")
            elif len(warehouses) > 1:
                raise HTTPException(
                    status_code=400,
                    detail="MÃºltiples almacenes disponibles, debe especificar warehouse_id",
                )

            warehouse_uuid = warehouses[0][0]

        # 5. Procesar stock por cada lÃ­nea
        lines = db.execute(
            text(
                "SELECT product_id, qty FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        for line in lines:
            product_id = line[0]
            qty_sold = float(line[1])

            # Registrar movimiento de stock
            db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, 'sale', 'pos_receipt', :rid"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": _get_tenant_id(request),
                    "pid": product_id,
                    "wid": warehouse_uuid,
                    "q": qty_sold,
                    "rid": receipt_uuid,
                },
            )

            # Actualizar stock_items con lock
            stock_item = db.execute(
                text(
                    "SELECT id, qty FROM stock_items "
                    "WHERE warehouse_id = :wid AND product_id = :pid "
                    "FOR UPDATE"
                ),
                {"wid": str(warehouse_uuid), "pid": str(product_id)},
            ).first()

            if stock_item is None:
                # Crear registro con stock 0
                db.execute(
                    text(
                        "INSERT INTO stock_items("
                        "id, tenant_id, warehouse_id, product_id, qty"
                        ") VALUES ("
                        "gen_random_uuid(), :tid, :wid, :pid, 0"
                        ")"
                    ),
                    {
                        "tid": str(_get_tenant_id(request)),
                        "wid": str(warehouse_uuid),
                        "pid": str(product_id),
                    },
                )
                current_qty = 0.0
            else:
                current_qty = float(stock_item[1] or 0)

            new_qty = current_qty - qty_sold

            # Advertir si stock queda negativo (pero no bloquear)
            if new_qty < 0:
                # PodrÃ­as loggear esto o enviar una notificaciÃ³n
                pass

            db.execute(
                text(
                    "UPDATE stock_items SET qty = :q "
                    "WHERE warehouse_id = :wid AND product_id = :pid"
                ),
                {"q": new_qty, "wid": str(warehouse_uuid), "pid": str(product_id)},
            )

        # 6. Marcar recibo como pagado
        db.execute(
            text(
                "UPDATE pos_receipts "
                "SET status = 'paid', gross_total = :gt, tax_total = :tt, paid_at = NOW() "
                "WHERE id = :id"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": receipt_uuid, "gt": total, "tt": tax},
        )

        db.commit()

        return {
            "ok": True,
            "receipt_id": str(receipt_uuid),
            "status": "paid",
            "totals": {
                "subtotal": float(subtotal),
                "tax": float(tax),
                "total": float(total),
                "paid": float(paid),
                "change": float(paid - total),
            },
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en checkout: {str(e)}")


@router.get("/receipts", response_model=list[dict])
def list_receipts(
    request: Request,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    shift_id: str | None = None,
    limit: int = Query(default=500, le=1000),
    db: Session = Depends(get_db),
):
    """Lista recibos con filtros opcionales"""
    ensure_guc_from_request(request, db, persist=True)

    sql_parts = [
        "SELECT id, shift_id, register_id, number, status, gross_total, tax_total, "
        "created_at, paid_at "
        "FROM pos_receipts WHERE 1=1"
    ]
    params = {}

    if status:
        sql_parts.append("AND status = :st")
        params["st"] = status

    if shift_id:
        shift_uuid = _validate_uuid(shift_id, "Shift ID")
        sql_parts.append("AND shift_id = :sid")
        params["sid"] = shift_uuid

    if since:
        sql_parts.append("AND created_at >= :since")
        params["since"] = since

    if until:
        sql_parts.append("AND created_at <= :until")
        params["until"] = until

    sql_parts.append(f"ORDER BY created_at DESC LIMIT {min(limit, 1000)}")

    try:
        rows = db.execute(text(" ".join(sql_parts)), params).fetchall()

        return [
            {
                "id": str(r[0]),
                "shift_id": str(r[1]),
                "register_id": str(r[2]),
                "number": r[3],
                "status": r[4],
                "gross_total": float(r[5]) if r[5] else 0,
                "tax_total": float(r[6]) if r[6] else 0,
                "created_at": r[7].isoformat() if r[7] else None,
                "paid_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar recibos: {str(e)}")


@router.get("/receipts/{receipt_id}/print")
def print_receipt(
    receipt_id: str,
    request: Request,
    width: str = "58mm",
    db: Session = Depends(get_db),
):
    """Genera HTML para impresiÃ³n tÃ©rmica del ticket"""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        # Obtener datos del recibo
        receipt = db.execute(
            text(
                "SELECT r.id, r.number, r.gross_total, r.tax_total, r.created_at, r.status "
                "FROM pos_receipts r WHERE r.id = :id"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": receipt_uuid},
        ).fetchone()

        if not receipt:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")

        # Obtener lÃ­neas
        lines = db.execute(
            text(
                "SELECT rl.qty, rl.unit_price, rl.line_total, p.name "
                "FROM pos_receipt_lines rl "
                "LEFT JOIN products p ON rl.product_id = p.id "
                "WHERE rl.receipt_id = :rid "
                "ORDER BY rl.id"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        # Obtener pagos
        payments = db.execute(
            text(
                "SELECT method, amount FROM pos_payments WHERE receipt_id = :rid ORDER BY paid_at"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        # Generar HTML
        lines_html = "".join(
            [
                f'<div class="line">'
                f"<span>{line[0]:.2f}x {line[3] or 'Producto'}</span>"
                f"<span>${line[2]:.2f}</span>"
                f"</div>"
                for line in lines
            ]
        )

        payments_html = "".join(
            [
                f'<div class="line"><span>{p[0].upper()}</span><span>${p[1]:.2f}</span></div>'
                for p in payments
            ]
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ticket {receipt[1]}</title>
    <style>
        @page {{
            width: {width};
            margin: 0;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            width: 100%;
            max-width: 48mm;
            font-family: 'Courier New', Courier, monospace;
            font-size: 9pt;
            margin: 5mm auto;
            padding: 0 2mm;
        }}
        .center {{
            text-align: center;
            margin: 3px 0;
        }}
        .bold {{
            font-weight: bold;
        }}
        .line {{
            display: flex;
            justify-content: space-between;
            margin: 2px 0;
            font-size: 8pt;
        }}
        .line span:first-child {{
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            padding-right: 5px;
        }}
        .line span:last-child {{
            text-align: right;
            white-space: nowrap;
        }}
        hr {{
            border: none;
            border-top: 1px dashed #000;
            margin: 5px 0;
        }}
        .total {{
            margin-top: 5px;
            padding-top: 5px;
            font-weight: bold;
            font-size: 10pt;
        }}
        .section {{
            margin: 8px 0;
        }}
        .section-title {{
            font-weight: bold;
            margin-bottom: 3px;
            font-size: 8pt;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 2mm;
            }}
        }}
    </style>
</head>
<body>
    <div class="center bold" style="font-size: 11pt;">TICKET DE VENTA</div>
    <div class="center">NÂº {receipt[1] or "N/A"}</div>
    <div class="center" style="font-size: 8pt;">
        {receipt[4].strftime("%d/%m/%Y %H:%M") if receipt[4] else ""}
    </div>

    <hr>

    <div class="section">
        <div class="section-title">PRODUCTOS</div>
        {lines_html}
    </div>

    <hr>

    <div class="line">
        <span>SUBTOTAL</span>
        <span>${(receipt[2] - receipt[3]):.2f}</span>
    </div>
    <div class="line">
        <span>IVA</span>
        <span>${receipt[3]:.2f}</span>
    </div>
    <div class="total line">
        <span>TOTAL</span>
        <span>${receipt[2]:.2f}</span>
    </div>

    {
            f'''
    <hr>
    <div class="section">
        <div class="section-title">PAGOS</div>
        {payments_html}
    </div>
    '''
            if payments
            else ""
        }

    <hr>

    <div class="center" style="margin-top: 10px; font-size: 8pt;">
        Â¡Gracias por su compra!
    </div>

    <div class="center" style="margin-top: 8px; font-size: 7pt;">
        Estado: {receipt[5].upper()}
    </div>

    <script>
        // Auto-imprimir al cargar
        window.onload = function() {{
            setTimeout(function() {{
                window.print();
            }}, 500);
        }};
    </script>
</body>
</html>"""

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar ticket: {str(e)}")


# ============================================================================
# ENDPOINTS DEPRECATED (Mantener para retrocompatibilidad)
# ============================================================================


@router.post(
    "/receipts/{receipt_id}/add_item",
    response_model=dict,
    deprecated=True,
    include_in_schema=False,
)
def add_item(receipt_id: str, payload: ItemIn, request: Request, db: Session = Depends(get_db)):
    """
    DEPRECATED: Usa POST /receipts con lÃ­neas incluidas.
    Agrega un item a un recibo en borrador.
    """
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        rec = db.execute(
            text("SELECT status FROM pos_receipts WHERE id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": receipt_uuid},
        ).first()

        if not rec or rec[0] != "draft":
            raise HTTPException(status_code=400, detail="El recibo no estÃ¡ en borrador")

        row = db.execute(
            text(
                "INSERT INTO pos_items(receipt_id, product_id, qty, unit_price, tax) "
                "VALUES (:rid, :pid, :q, :p, :t) RETURNING id"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {
                "rid": receipt_uuid,
                "pid": payload.product_id,
                "q": payload.qty,
                "p": payload.unit_price,
                "t": payload.tax,
            },
        ).first()

        db.commit()
        return {"id": int(row[0])}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al agregar item: {str(e)}")


@router.post(
    "/receipts/{receipt_id}/remove_item",
    response_model=dict,
    deprecated=True,
    include_in_schema=False,
)
def remove_item(
    receipt_id: str,
    payload: RemoveItemIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    DEPRECATED: Usa PUT /receipts/{id} para modificar lÃ­neas.
    Elimina un item de un recibo en borrador.
    """
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        rec = db.execute(
            text("SELECT status FROM pos_receipts WHERE id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": receipt_uuid},
        ).first()

        if not rec or rec[0] != "draft":
            raise HTTPException(status_code=400, detail="El recibo no estÃ¡ en borrador")

        db.execute(
            text("DELETE FROM pos_items WHERE id = :id AND receipt_id = :rid").bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True))
            ),
            {"id": payload.item_id, "rid": receipt_uuid},
        )

        db.commit()
        return {"ok": True}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar item: {str(e)}")


@router.post(
    "/receipts/{receipt_id}/take_payment",
    response_model=dict,
    deprecated=True,
    include_in_schema=False,
)
def take_payment(
    receipt_id: str,
    payload: PaymentsIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    DEPRECATED: Usa POST /receipts/{id}/checkout en su lugar.
    Registra pagos en un recibo.
    """
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        rec = db.execute(
            text("SELECT status FROM pos_receipts WHERE id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": receipt_uuid},
        ).first()

        if not rec or rec[0] != "draft":
            raise HTTPException(status_code=400, detail="El recibo no estÃ¡ en borrador")

        # Insertar pagos
        for payment in payload.payments:
            db.execute(
                text(
                    "INSERT INTO pos_payments(receipt_id, method, amount, ref) "
                    "VALUES (:rid, :m, :a, :ref)"
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {
                    "rid": receipt_uuid,
                    "m": payment.method,
                    "a": payment.amount,
                    "ref": payment.ref,
                },
            )

        # Marcar como pagado (sin validaciÃ³n de monto)
        db.execute(
            text(
                "UPDATE pos_receipts SET status = 'paid', paid_at = NOW() WHERE id = :id"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": receipt_uuid},
        )

        db.commit()
        return {"ok": True, "receipt_id": str(receipt_uuid)}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar pago: {str(e)}")


@router.post(
    "/receipts/{receipt_id}/post",
    response_model=dict,
    deprecated=True,
    include_in_schema=False,
)
def post_receipt(
    receipt_id: str,
    payload: PostReceiptIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    DEPRECATED: Usa POST /receipts/{id}/checkout en su lugar.
    Procesa un recibo y descuenta stock.
    """
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        # Validar estado
        rec = db.execute(
            text("SELECT shift_id, status FROM pos_receipts WHERE id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": receipt_uuid},
        ).first()

        if not rec or rec[1] != "draft":
            raise HTTPException(status_code=400, detail="El recibo no estÃ¡ en borrador")

        shift_id = rec[0]

        # Obtener warehouse (UUID)
        wh_id = payload.warehouse_id
        if wh_id is None:
            row = db.execute(
                text(
                    "SELECT r.default_warehouse_id "
                    "FROM pos_shifts s "
                    "JOIN pos_registers r ON r.id = s.register_id "
                    "WHERE s.id = :sid"
                ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
                {"sid": shift_id},
            ).first()
            wh_id = str(row[0]) if row and row[0] is not None else None

        if wh_id is None:
            raise HTTPException(status_code=400, detail="Se requiere especificar un almacÃ©n")

        # Calcular totales
        tot_row = db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(qty * unit_price), 0) AS subtotal, "
                "COALESCE(SUM(COALESCE(tax, 0)), 0) AS tax "
                "FROM pos_items "
                "WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()

        pay_row = db.execute(
            text(
                "SELECT COALESCE(SUM(amount), 0) FROM pos_payments WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()

        subtotal = float(tot_row[0] or 0)
        tax = float(tot_row[1] or 0)
        total = subtotal + tax
        paid = float(pay_row[0] or 0)

        if paid + 1e-6 < total:
            raise HTTPException(status_code=400, detail="Pago insuficiente")

        # Consumir stock
        items = db.execute(
            text("SELECT product_id, qty FROM pos_items WHERE receipt_id = :rid").bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True))
            ),
            {"rid": receipt_uuid},
        ).fetchall()

        for it in items:
            db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "product_id, warehouse_id, qty, kind, ref_type, ref_id"
                    ") VALUES (:pid, :wid, :q, 'issue', 'pos_receipt', :rid)"
                ).bindparams(
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "pid": it[0],
                    "wid": wh_id,
                    "q": float(it[1]),
                    "rid": receipt_uuid,
                },
            )

            # Actualizar stock_items
            row = db.execute(
                text(
                    "SELECT id, qty FROM stock_items "
                    "WHERE warehouse_id = :wid AND product_id = :pid FOR UPDATE"
                ).bindparams(
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {"wid": wh_id, "pid": it[0]},
            ).first()

            if row is None:
                db.execute(
                    text(
                        "INSERT INTO stock_items(warehouse_id, product_id, qty) "
                        "VALUES (:wid, :pid, 0)"
                    ).bindparams(
                        bindparam("wid", type_=PGUUID(as_uuid=True)),
                        bindparam("pid", type_=PGUUID(as_uuid=True)),
                    ),
                    {"wid": wh_id, "pid": it[0]},
                )
                cur_qty = 0.0
            else:
                cur_qty = float(row[1] or 0)

            new_qty = cur_qty - float(it[1])

            db.execute(
                text(
                    "UPDATE stock_items SET qty = :q "
                    "WHERE warehouse_id = :wid AND product_id = :pid"
                ).bindparams(
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {"q": new_qty, "wid": wh_id, "pid": it[0]},
            )

        # Actualizar recibo
        db.execute(
            text(
                "UPDATE pos_receipts SET status = 'posted', totals = :tot WHERE id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {
                "rid": receipt_uuid,
                "tot": Json({"subtotal": subtotal, "tax": tax, "total": total}),
            },
        )

        db.commit()

        # Intentar encolar webhook (best-effort)
        try:
            webhook_payload = {
                "id": str(receipt_uuid),
                "total": total,
                "shift_id": str(shift_id),
            }
            db.execute(
                text(
                    "INSERT INTO webhook_deliveries(event, payload, target_url, status) "
                    "SELECT 'pos.receipt.posted', :p, s.url, 'PENDING' "
                    "FROM webhook_subscriptions s "
                    "WHERE s.event = 'pos.receipt.posted' AND s.active"
                ),
                {"p": Json(webhook_payload)},
            )
            db.commit()

            # Intentar enviar con Celery
            try:
                from apps.backend.celery_app import celery_app

                rows = db.execute(
                    text(
                        "SELECT id::text FROM webhook_deliveries "
                        "WHERE event = 'pos.receipt.posted' "
                        "ORDER BY created_at DESC LIMIT 10"
                    )
                ).fetchall()
                for r in rows:
                    celery_app.send_task(
                        "apps.backend.app.modules.webhooks.tasks.deliver",
                        args=[str(r[0])],
                    )
            except Exception:
                pass
        except Exception:
            db.rollback()

        return {"id": str(receipt_uuid), "status": "posted", "total": total}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar recibo: {str(e)}")


# ============================================================================
# ENDPOINTS DE SALUD Y UTILIDADES
# ============================================================================


@router.get("/daily_counts", response_model=list[dict])
def list_daily_counts(
    request: Request,
    register_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    """Lista los reportes diarios de caja"""
    ensure_guc_from_request(request, db, persist=True)

    sql_parts = [
        "SELECT id, register_id, shift_id, count_date, opening_float, "
        "cash_sales, card_sales, other_sales, total_sales, expected_cash, "
        "counted_cash, discrepancy, loss_amount, loss_note, created_at "
        "FROM pos_daily_counts WHERE 1=1"
    ]
    params = {}

    if register_id:
        rid = _validate_uuid(register_id, "Register ID")
        sql_parts.append("AND register_id = :rid")
        params["rid"] = rid

    if since:
        sql_parts.append("AND count_date >= :since")
        params["since"] = since

    if until:
        sql_parts.append("AND count_date <= :until")
        params["until"] = until

    sql_parts.append("ORDER BY count_date DESC, created_at DESC LIMIT :limit")
    params["limit"] = limit

    sql = " ".join(sql_parts)

    try:
        rows = db.execute(text(sql), params).fetchall()

        return [
            {
                "id": str(r[0]),
                "register_id": str(r[1]),
                "shift_id": str(r[2]),
                "count_date": r[3].isoformat() if r[3] else None,
                "opening_float": float(r[4] or 0),
                "cash_sales": float(r[5] or 0),
                "card_sales": float(r[6] or 0),
                "other_sales": float(r[7] or 0),
                "total_sales": float(r[8] or 0),
                "expected_cash": float(r[9] or 0),
                "counted_cash": float(r[10] or 0),
                "discrepancy": float(r[11] or 0),
                "loss_amount": float(r[12] or 0),
                "loss_note": r[13],
                "created_at": r[14].isoformat() if r[14] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar reportes diarios: {str(e)}")


@router.get("/health", include_in_schema=False)
def health_check():
    """Endpoint de salud para verificar que el mÃ³dulo POS estÃ¡ funcionando"""
    return {
        "status": "healthy",
        "module": "pos",
        "timestamp": datetime.utcnow().isoformat(),
    }
