from __future__ import annotations

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from psycopg2.extras import Json
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.audit_events import audit_event
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.models.accounting.chart_of_accounts import JournalEntry as AsientoContable
from app.models.accounting.chart_of_accounts import JournalEntryLine as AsientoLinea
from app.models.accounting.pos_settings import PaymentMethod, TenantAccountingSettings
from app.modules.accounting.interface.http.tenant import _generate_numero_asiento
from app.modules.settings.infrastructure.repositories import SettingsRepo
from app.services.inventory_costing import InventoryCostingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
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
        raise HTTPException(status_code=401, detail="Claims inv?lidos")

    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID no encontrado")

    try:
        return UUID(str(tenant_id))
    except Exception:
        raise HTTPException(status_code=401, detail="Tenant ID inv?lido")


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


def _is_company_admin(claims: dict) -> bool:
    return bool(
        claims.get("is_company_admin")
        or claims.get("is_admin_company")
        or claims.get("es_admin_empresa")
    )


def _validate_uuid(value: str, field_name: str = "ID") -> UUID:
    """Valida y convierte un string a UUID"""
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=400, detail=f"{field_name} invÃ¡lido: debe ser un UUID vÃ¡lido"
        )


def _ensure_pos_accounting_settings(settings: TenantAccountingSettings) -> None:
    missing: list[str] = []
    if not getattr(settings, "cash_account_id", None):
        missing.append("cash_account_id")
    if not getattr(settings, "bank_account_id", None):
        missing.append("bank_account_id")
    if not getattr(settings, "sales_bakery_account_id", None):
        missing.append("sales_bakery_account_id")
    if not getattr(settings, "vat_output_account_id", None):
        missing.append("vat_output_account_id")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Config contable POS incompleta: faltan " + ", ".join(missing),
        )


def _to_decimal(value: float) -> Decimal:
    """Convierte float a Decimal con 2 decimales"""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_decimal_q(value: float | Decimal, q: str) -> Decimal:
    """Convierte a Decimal con precision configurable."""
    return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)


def _resolve_tenant_currency(db: Session, tenant_id: UUID) -> str:
    """Resuelve la moneda base del tenant para POS.

    Fuente única: configuración operativa (company_settings / currencies).
    No se usa tenants.base_currency; si no hay configuración, devolvemos error.
    """
    row = db.execute(
        text(
            """
            SELECT COALESCE(
                NULLIF(UPPER(TRIM(cs.currency)), ''),
                NULLIF(UPPER(TRIM(cur.code)), '')
            )
            FROM company_settings cs
            LEFT JOIN currencies cur ON cur.id = cs.currency_id
            WHERE cs.tenant_id = :tid
            LIMIT 1
            """
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id},
    ).first()
    if row and row[0]:
        cur = str(row[0]).strip().upper()
        if cur:
            return cur

    # Fallback: use tenant.base_currency if present, otherwise default USD to keep POS operable
    base = db.execute(
        text(
            "SELECT NULLIF(UPPER(TRIM(base_currency)), '') FROM tenants WHERE id = :tid LIMIT 1"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id},
    ).first()
    if base and base[0]:
        return str(base[0]).strip().upper()

    return "USD"


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
    cashier_id: str | None = None
    customer_id: str | None = None
    lines: list[ReceiptLineIn] = Field(default_factory=list)
    payments: list[PaymentIn] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("shift_id", "register_id", "cashier_id", "customer_id")
    @classmethod
    def validate_ids(cls, v):
        if v is not None:
            _validate_uuid(v, "ID")
        return v


class NumberingCounterOut(BaseModel):
    doc_type: str
    year: int
    series: str
    current_no: int
    updated_at: datetime | None


class NumberingCounterUpdateIn(BaseModel):
    doc_type: str = Field(min_length=1, max_length=30)
    year: int = Field(ge=2000)
    series: str = Field(default="A", max_length=50)
    current_no: int = Field(ge=0)

    @field_validator("series")
    @classmethod
    def normalize_series(cls, v: str) -> str:
        return (v or "").strip() or "A"


class DocSeriesOut(BaseModel):
    id: str
    register_id: str | None
    doc_type: str
    name: str
    current_no: int
    reset_policy: str
    active: bool
    created_at: datetime | None


class DocSeriesUpsertIn(BaseModel):
    id: str | None = None
    register_id: str | None = None
    doc_type: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1, max_length=50)
    current_no: int = Field(ge=0)
    reset_policy: Literal["yearly", "never"] = "yearly"
    active: bool = True

    @field_validator("register_id")
    @classmethod
    def validate_register_id(cls, v):
        if v is not None:
            _validate_uuid(v, "Register ID")
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


class CloseShiftWithIdIn(CloseShiftIn):
    shift_id: str

    @field_validator("shift_id")
    @classmethod
    def validate_shift_id(cls, v):
        _validate_uuid(v, "Shift ID")
        return v


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


class RefundReceiptIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    refund_method: str | None = None  # original|cash|store_credit (frontend may send this)
    restock: bool | None = None
    line_ids: list[str] | None = None
    store_credit_expiry_months: int | None = None


# ============================================================================
# ENDPOINTS - REGISTERS
# ============================================================================


@router.get(
    "/registers",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.register.read"))],
)
def list_registers(request: Request, db: Session = Depends(get_db)):
    """Lista todos los registros POS del tenant actual"""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    try:
        rows = db.execute(
            text(
                "SELECT id, name, store_id, active, created_at "
                "FROM pos_registers "
                "WHERE tenant_id = :tid "
                "ORDER BY created_at DESC"
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": tenant_id},
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


@router.post(
    "/registers",
    response_model=dict,
    status_code=201,
    dependencies=[Depends(require_permission("pos.register.manage"))],
)
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


@router.post(
    "/shifts",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.open"))],
)
@router.post(
    "/open_shift",
    response_model=dict,
    deprecated=True,
    dependencies=[Depends(require_permission("pos.shift.open"))],
)
def open_shift(payload: OpenShiftIn, request: Request, db: Session = Depends(get_db)):
    """Abre un nuevo turno en un registro POS"""
    ensure_guc_from_request(request, db, persist=True)

    user_id = _get_user_id(request)
    tenant_id = _get_tenant_id(request)
    register_uuid = _validate_uuid(payload.register_id, "Register ID")

    try:
        # Verificar que el registro existe y estÃ¡ activo
        register = db.execute(
            text(
                "SELECT active FROM pos_registers WHERE id = :rid AND tenant_id = :tid"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"rid": register_uuid, "tid": tenant_id},
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
        opened_at = datetime.utcnow()
        row = db.execute(
            text(
                "INSERT INTO pos_shifts(register_id, opened_by, opened_at, opening_float, status) "
                "VALUES (:rid, :opened_by, :opened_at, :opening_float, 'open') "
                "RETURNING id"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("opened_by", type_=PGUUID(as_uuid=True)),
                bindparam("opened_at"),
            ),
            {
                "rid": register_uuid,
                "opened_by": user_id,
                "opened_at": opened_at,
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


@router.get(
    "/shifts/current/{register_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.read"))],
)
def get_current_shift(register_id: str, request: Request, db: Session = Depends(get_db)):
    """Obtiene el turno abierto (si existe) para un registro dado"""
    ensure_guc_from_request(request, db, persist=True)
    rid = _validate_uuid(register_id, "Register ID")

    shift = db.execute(
        text(
            "SELECT id, register_id, opened_by, opened_at, closed_at, opening_float, "
            "closing_total, status "
            "FROM pos_shifts "
            "WHERE register_id = :rid AND status = 'open' "
            "ORDER BY opened_at DESC "
            "LIMIT 1"
        ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
        {"rid": rid},
    ).first()

    if not shift:
        raise HTTPException(status_code=404, detail="No hay turno abierto para este registro")

    return {
        "id": str(shift[0]),
        "register_id": str(shift[1]),
        "opened_by": str(shift[2]),
        "opened_at": shift[3].isoformat() if shift[3] else None,
        "closed_at": shift[4].isoformat() if shift[4] else None,
        "opening_float": float(shift[5] or 0),
        "closing_total": float(shift[6] or 0) if shift[6] is not None else None,
        "status": shift[7],
    }


@router.get(
    "/shifts/{shift_id}/summary",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
def get_shift_summary(
    shift_id: str,
    request: Request,
    cashier_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Obtiene resumen del turno: ventas, productos vendidos y stock restante"""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = _validate_uuid(shift_id, "Shift ID")

    cashier_uuid = _validate_uuid(cashier_id, "Cashier ID") if cashier_id else None

    base_filter = "shift_id = :sid"
    params = {"sid": shift_uuid}
    if cashier_uuid:
        base_filter += " AND cashier_id = :cid"
        params["cid"] = cashier_uuid

    try:
        # Verificar recibos pendientes (draft o unpaid)
        pending_receipts = db.execute(
            text(
                "SELECT COUNT(*) FROM pos_receipts "
                f"WHERE {base_filter} AND status IN ('draft', 'unpaid')"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            params,
        ).scalar()

        # Productos vendidos
        items_sold = db.execute(
            text(
                "SELECT rl.product_id, p.name, p.sku AS code, "
                "SUM(rl.qty) as qty_sold, "
                "SUM(rl.qty * rl.unit_price * (1 - rl.discount_pct/100)) as subtotal "
                "FROM pos_receipt_lines rl "
                "JOIN pos_receipts r ON r.id = rl.receipt_id "
                "LEFT JOIN products p ON p.id = rl.product_id "
                f"WHERE r.{base_filter} AND r.status = 'paid' "
                "GROUP BY rl.product_id, p.name, p.sku "
                "ORDER BY p.name"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            params,
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
                f"FROM pos_receipts WHERE {base_filter} AND status = 'paid'"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            params,
        ).scalar()

        # Desglose de pagos por método
        payments_breakdown_rows = db.execute(
            text(
                "SELECT pp.method, COALESCE(SUM(pp.amount), 0) as total "
                "FROM pos_payments pp "
                "JOIN pos_receipts pr ON pr.id = pp.receipt_id "
                f"WHERE pr.{base_filter} AND pr.status = 'paid' "
                "GROUP BY pp.method"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            params,
        ).fetchall()
        payments_breakdown = {row[0]: float(row[1] or 0) for row in payments_breakdown_rows}

        return {
            "pending_receipts": pending_receipts or 0,
            "items_sold": items,
            "sales_total": float(sales_total or 0),
            "receipts_count": len(items_sold),
            "payments": payments_breakdown,
        }

    except Exception as e:
        logger.error(f"Error getting shift summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


@router.post(
    "/shifts/{shift_id}/close",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.close"))],
)
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
        # Verificar que el turno existe
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
        token_tenant_id = _get_tenant_id(request)
        if str(tenant_id) != str(token_tenant_id):
            logger.warning(
                "Tenant mismatch closing shift: shift_tenant_id=%s token_tenant_id=%s shift_id=%s",
                tenant_id,
                token_tenant_id,
                shift_uuid,
            )
            raise HTTPException(status_code=403, detail="tenant_mismatch")

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

        # Totales de impuestos para calcular base imponible
        tax_total = (
            db.execute(
                text(
                    "SELECT COALESCE(SUM(tax_total), 0) FROM pos_receipts "
                    "WHERE shift_id = :sid AND status = 'paid'"
                ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
                {"sid": shift_uuid},
            ).scalar()
            or 0
        )
        net_total = total_sales - float(tax_total)

        # Configuración contable del tenant
        settings = db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()
        if not settings:
            logger.warning(
                "POS accounting settings missing for tenant_id=%s shift_id=%s",
                tenant_id,
                shift_uuid,
            )
            raise HTTPException(
                status_code=400, detail="Config contable POS no configurada para este tenant"
            )

        _ensure_pos_accounting_settings(settings)

        # Medios de pago contables
        pm_rows = db.query(PaymentMethod).filter_by(tenant_id=tenant_id, is_active=True).all()
        pm_map = {p.name.strip().lower(): p.account_id for p in pm_rows}

        # Construir líneas contables
        lines: list[AsientoLinea] = []
        debit_total = 0.0
        credit_total = 0.0

        # Cobros (DEBE) por método de pago
        for method, amount in sales_by_method:
            amt = float(amount or 0)
            if amt <= 0:
                continue
            mkey = (method or "").strip().lower()
            account_id = pm_map.get(mkey)
            if not account_id:
                # Fallback básico
                if mkey == "cash" or mkey == "efectivo":
                    account_id = settings.cash_account_id
                elif mkey in ("card", "tarjeta", "debit", "credit"):
                    account_id = settings.bank_account_id
            if not account_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay cuenta contable para el medio de pago: {method}",
                )
            lines.append(
                AsientoLinea(
                    account_id=account_id, debit=Decimal(str(round(amt, 2)))
                )  # credit=0 por defecto
            )
            debit_total += amt

        # Ventas (HABER) - base imponible
        if net_total > 0:
            lines.append(
                AsientoLinea(
                    account_id=settings.sales_bakery_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(net_total, 2))),
                )
            )
            credit_total += net_total

        # IVA repercutido (HABER)
        if tax_total and float(tax_total) > 0:
            lines.append(
                AsientoLinea(
                    account_id=settings.vat_output_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(float(tax_total), 2))),
                )
            )
            credit_total += float(tax_total)

        # Pérdidas/mermas
        if payload.loss_amount and payload.loss_amount > 0:
            if not settings.loss_account_id:
                raise HTTPException(
                    status_code=400, detail="Config contable: falta cuenta de pérdidas/mermas"
                )
            lines.append(
                AsientoLinea(
                    account_id=settings.loss_account_id,
                    debit=Decimal(str(round(payload.loss_amount, 2))),
                    credit=Decimal("0"),
                )
            )
            lines.append(
                AsientoLinea(
                    account_id=settings.cash_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(payload.loss_amount, 2))),
                )
            )
            debit_total += float(payload.loss_amount)
            credit_total += float(payload.loss_amount)

        # Validar balance
        if round(debit_total - credit_total, 2) != 0:
            raise HTTPException(status_code=400, detail="Asiento no balanceado al cerrar turno")

        # Evitar duplicar asiento por turno
        existing_entry = db.execute(
            text(
                "SELECT id FROM journal_entries WHERE ref_doc_type = 'POS_SHIFT' AND ref_doc_id = :sid AND tenant_id = :tid"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": tenant_id},
        ).first()
        if existing_entry:
            raise HTTPException(
                status_code=400, detail="Ya existe un asiento contable para este turno"
            )

        # Crear asiento contable
        number = _generate_numero_asiento(db, tenant_id, datetime.utcnow().year)
        entry = AsientoContable(
            tenant_id=tenant_id,
            number=number,
            date=datetime.utcnow().date(),
            type="OPERATIONS",
            description=f"Cierre turno POS {shift_id}",
            ref_doc_type="POS_SHIFT",
            ref_doc_id=shift_uuid,
            debit_total=Decimal(str(round(debit_total, 2))),
            credit_total=Decimal(str(round(credit_total, 2))),
            is_balanced=True,
            status="POSTED",
        )
        db.add(entry)
        db.flush()

        # Asociar líneas al asiento
        for idx, line in enumerate(lines):
            line.entry_id = entry.id
            line.line_number = idx + 1
            db.add(line)

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


@router.post(
    "/shifts/{shift_id}/accounting",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
def generate_accounting_for_closed_shift(
    shift_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Genera asiento contable para un turno ya cerrado (no modifica el turno)."""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = _validate_uuid(shift_id, "Shift ID")

    try:
        shift = db.execute(
            text("SELECT status, register_id FROM pos_shifts WHERE id = :sid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True))
            ),
            {"sid": shift_uuid},
        ).first()
        if not shift:
            raise HTTPException(status_code=404, detail="Turno no encontrado")
        if shift[0] != "closed":
            raise HTTPException(status_code=400, detail="El turno debe estar cerrado")

        shift_data = db.execute(
            text(
                "SELECT ps.opening_float, pr.tenant_id FROM pos_shifts ps "
                "JOIN pos_registers pr ON pr.id = ps.register_id "
                "WHERE ps.id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).first()
        if not shift_data:
            raise HTTPException(status_code=404, detail="Datos del turno no encontrados")
        tenant_id = shift_data[1]

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

        total_sales = 0.0
        for method, amount in sales_by_method:
            total_sales += float(amount or 0)

        tax_total = (
            db.execute(
                text(
                    "SELECT COALESCE(SUM(tax_total), 0) FROM pos_receipts "
                    "WHERE shift_id = :sid AND status = 'paid'"
                ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
                {"sid": shift_uuid},
            ).scalar()
            or 0.0
        )
        net_total = total_sales - float(tax_total)

        settings = db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()
        if not settings:
            logger.warning(
                "POS accounting settings missing for tenant_id=%s",
                tenant_id,
            )
            raise HTTPException(
                status_code=400, detail="Config contable POS no configurada para este tenant"
            )

        _ensure_pos_accounting_settings(settings)

        pm_rows = db.query(PaymentMethod).filter_by(tenant_id=tenant_id, is_active=True).all()
        pm_map = {p.name.strip().lower(): p.account_id for p in pm_rows}

        lines: list[AsientoLinea] = []
        debit_total = 0.0
        credit_total = 0.0

        for method, amount in sales_by_method:
            amt = float(amount or 0)
            if amt <= 0:
                continue
            mkey = (method or "").strip().lower()
            account_id = pm_map.get(mkey)
            if not account_id:
                if mkey in ("cash", "efectivo"):
                    account_id = settings.cash_account_id
                elif mkey in ("card", "tarjeta", "debit", "credit"):
                    account_id = settings.bank_account_id
            if not account_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay cuenta contable para el medio de pago: {method}",
                )
            lines.append(
                AsientoLinea(
                    account_id=account_id,
                    debit=Decimal(str(round(amt, 2))),
                    credit=Decimal("0"),
                )
            )
            debit_total += amt

        if net_total > 0:
            lines.append(
                AsientoLinea(
                    account_id=settings.sales_bakery_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(net_total, 2))),
                )
            )
            credit_total += net_total

        if tax_total and float(tax_total) > 0:
            lines.append(
                AsientoLinea(
                    account_id=settings.vat_output_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(float(tax_total), 2))),
                )
            )
            credit_total += float(tax_total)

        loss_amount = db.execute(
            text("SELECT loss_amount FROM pos_daily_counts WHERE shift_id = :sid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True))
            ),
            {"sid": shift_uuid},
        ).scalar()
        if loss_amount and loss_amount > 0:
            if not settings.loss_account_id:
                raise HTTPException(
                    status_code=400, detail="Config contable: falta cuenta de pérdidas/mermas"
                )
            lines.append(
                AsientoLinea(
                    account_id=settings.loss_account_id,
                    debit=Decimal(str(round(loss_amount, 2))),
                    credit=Decimal("0"),
                )
            )
            lines.append(
                AsientoLinea(
                    account_id=settings.cash_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(loss_amount, 2))),
                )
            )
            debit_total += float(loss_amount)
            credit_total += float(loss_amount)

        existing_entry = db.execute(
            text(
                "SELECT id FROM journal_entries WHERE ref_doc_type = 'POS_SHIFT' AND ref_doc_id = :sid AND tenant_id = :tid"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": tenant_id},
        ).first()
        if existing_entry:
            raise HTTPException(
                status_code=400, detail="Ya existe un asiento contable para este turno"
            )

        if round(debit_total - credit_total, 2) != 0:
            raise HTTPException(status_code=400, detail="Asiento no balanceado")

        number = _generate_numero_asiento(db, tenant_id, datetime.utcnow().year)
        entry = AsientoContable(
            tenant_id=tenant_id,
            number=number,
            date=datetime.utcnow().date(),
            type="OPERATIONS",
            description=f"Contabilización turno POS {shift_id}",
            ref_doc_type="POS_SHIFT",
            ref_doc_id=shift_uuid,
            debit_total=Decimal(str(round(debit_total, 2))),
            credit_total=Decimal(str(round(credit_total, 2))),
            is_balanced=True,
            status="POSTED",
        )
        db.add(entry)
        db.flush()
        for idx, line in enumerate(lines):
            line.entry_id = entry.id
            line.line_number = idx + 1
            db.add(line)
        db.commit()
        return {
            "status": "accounted",
            "entry_id": str(entry.id),
            "total_sales": total_sales,
            "debit": debit_total,
            "credit": credit_total,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error generating accounting for shift: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al contabilizar turno: {str(e)}")


@router.post(
    "/shifts/close",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.close"))],
)
def close_shift_with_body(
    payload: CloseShiftWithIdIn, request: Request, db: Session = Depends(get_db)
):
    """Alias de cierre de turno recibiendo shift_id en el body (compatibilidad front)"""
    return close_shift(payload.shift_id, payload, request, db)


@router.get(
    "/shifts",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.shift.read"))],
)
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


@router.get(
    "/shifts/{shift_id}/summary",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
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


@router.post(
    "/receipts/calculate_totals",
    response_model=CalculateTotalsOut,
    dependencies=[Depends(require_permission("pos.receipt.create"))],
)
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


@router.post(
    "/receipts",
    response_model=dict,
    status_code=201,
    dependencies=[Depends(require_permission("pos.receipt.create"))],
)
def create_receipt(payload: ReceiptCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea un nuevo recibo POS"""
    ensure_guc_from_request(request, db, persist=True)

    claims = getattr(request.state, "access_claims", {}) or {}
    tenant_id = _get_tenant_id(request)
    current_user_id = _get_user_id(request)
    shift_uuid = _validate_uuid(payload.shift_id, "Shift ID")
    register_uuid = _validate_uuid(payload.register_id, "Register ID")
    customer_uuid = (
        _validate_uuid(payload.customer_id, "Customer ID") if payload.customer_id else None
    )

    try:
        cashier_id = current_user_id
        if payload.cashier_id:
            requested_cashier_id = _validate_uuid(payload.cashier_id, "Cashier ID")
            if requested_cashier_id != current_user_id and not _is_company_admin(claims):
                raise HTTPException(status_code=403, detail="cashier_override_forbidden")

            exists = db.execute(
                text(
                    "SELECT 1 FROM company_users "
                    "WHERE id = :cid AND tenant_id = :tid AND is_active = TRUE"
                ).bindparams(
                    bindparam("cid", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"cid": requested_cashier_id, "tid": tenant_id},
            ).first()
            if not exists:
                raise HTTPException(status_code=400, detail="cashier_not_found")

            cashier_id = requested_cashier_id

        if customer_uuid:
            exists = db.execute(
                text("SELECT 1 FROM clients " "WHERE id = :cid AND tenant_id = :tid").bindparams(
                    bindparam("cid", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"cid": customer_uuid, "tid": tenant_id},
            ).first()
            if not exists:
                raise HTTPException(status_code=400, detail="customer_not_found")

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

        currency = _resolve_tenant_currency(db, tenant_id)

        # Crear el recibo
        row = db.execute(
            text(
                "INSERT INTO pos_receipts("
                "tenant_id, register_id, shift_id, cashier_id, customer_id, number, status, "
                "gross_total, tax_total, currency, created_at"
                ") VALUES ("
                ":tid, :rid, :sid, :cashier_id, :customer_id, :number, 'draft', "
                "0, 0, :currency, NOW()"
                ") RETURNING id"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("cashier_id", type_=PGUUID(as_uuid=True)),
                bindparam("customer_id", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "rid": register_uuid,
                "sid": shift_uuid,
                "cashier_id": cashier_id,
                "customer_id": customer_uuid,
                "number": ticket_number,
                "currency": currency,
            },
        ).first()

        receipt_id = row[0]

        # Commit the receipt insertion to make it visible for RLS policies
        db.commit()

        # Restore RLS context after commit
        ensure_guc_from_request(request, db, persist=True)

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
                # Solo aplica default si cliente no envió tasa
                if tax_rate is None and default_tax is not None:
                    tax_rate = max(default_tax, 0.0)

                # Normalizar valores enviados
                if tax_rate is None:
                    tax_rate = 0.0
                elif tax_rate > 1:
                    tax_rate = tax_rate / 100.0
                elif tax_rate < 0:
                    tax_rate = 0.0

            qty_sold = abs(float(line.qty or 0))
            unit_price = float(line.unit_price or 0)
            discount_pct = float(line.discount_pct or 0)
            net_total = _to_decimal_q(qty_sold, "0.000001") * _to_decimal_q(unit_price, "0.0001")
            net_total = net_total * (Decimal("1") - (_to_decimal_q(discount_pct, "0.01") / 100))
            net_total = _to_decimal_q(net_total, "0.01")
            tax_total = _to_decimal_q(net_total * Decimal(str(tax_rate)), "0.01")
            line_total = _to_decimal_q(net_total + tax_total, "0.01")

            db.execute(
                text(
                    "INSERT INTO pos_receipt_lines("
                    "receipt_id, product_id, qty, unit_price, tax_rate, discount_pct, line_total, "
                    "uom, net_total, cogs_unit, cogs_total, gross_profit, gross_margin_pct"
                    ") VALUES ("
                    ":receipt_id, :product_id, :qty, :unit_price, :tax_rate, :discount_pct, :line_total, "
                    ":uom, :net_total, :cogs_unit, :cogs_total, :gross_profit, :gross_margin_pct"
                    ")"
                ).bindparams(
                    bindparam("receipt_id", type_=PGUUID(as_uuid=True)),
                    bindparam("product_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "receipt_id": receipt_id,
                    "product_id": product_uuid,
                    "qty": qty_sold,
                    "unit_price": unit_price,
                    "tax_rate": tax_rate,
                    "discount_pct": discount_pct,
                    "line_total": float(line_total),
                    "uom": line.uom,
                    "net_total": float(net_total),
                    "cogs_unit": 0.0,
                    "cogs_total": 0.0,
                    "gross_profit": 0.0,
                    "gross_margin_pct": 0.0,
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


@router.post(
    "/receipts/{receipt_id}/checkout",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.pay"))],
)
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
                    "INSERT INTO pos_payments(id, receipt_id, method, amount, ref, paid_at) "
                    "VALUES (:id, :rid, :m, :a, :ref, :paid_at)"
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": uuid4(),
                    "rid": receipt_uuid,
                    "m": payment.method,
                    "a": payment.amount,
                    "ref": payment.ref,
                    "paid_at": datetime.utcnow(),
                },
            )

        # 3. Calcular totales
        totals = db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100)), 0) AS subtotal, "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100) * rl.tax_rate), 0) AS tax "
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

        # 5. Procesar stock por cada lÃ­nea + snapshot de margen
        lines = db.execute(
            text(
                "SELECT id, product_id, qty, unit_price, discount_pct "
                "FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        costing = InventoryCostingService(db)
        tenant_id = _get_tenant_id(request)

        for line in lines:
            line_id = line[0]
            product_id = line[1]
            qty_sold = float(line[2])
            unit_price = float(line[3])
            discount_pct = float(line[4] or 0)

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
                        "tid": str(tenant_id),
                        "wid": str(warehouse_uuid),
                        "pid": str(product_id),
                    },
                )
                current_qty = 0.0
            else:
                current_qty = float(stock_item[1] or 0)

            cost_price = db.execute(
                text("SELECT cost_price FROM products WHERE id = :pid"),
                {"pid": product_id},
            ).scalar()
            fallback_cost = _to_decimal_q(float(cost_price or 0), "0.000001")

            state = costing.apply_outbound(
                str(tenant_id),
                str(warehouse_uuid),
                str(product_id),
                qty=_to_decimal_q(qty_sold, "0.000001"),
                allow_negative=False,
                initial_qty=_to_decimal_q(current_qty, "0.000001"),
                initial_avg_cost=fallback_cost,
            )

            cogs_unit = state.avg_cost
            cogs_total = _to_decimal_q(qty_sold, "0.000001") * cogs_unit
            net_total = _to_decimal_q(qty_sold, "0.000001") * _to_decimal_q(unit_price, "0.0001")
            net_total = net_total * (Decimal("1") - (_to_decimal_q(discount_pct, "0.01") / 100))
            net_total = _to_decimal_q(net_total, "0.01")
            cogs_total_money = _to_decimal_q(cogs_total, "0.01")
            gross_profit = _to_decimal_q(net_total - cogs_total_money, "0.01")
            if net_total > 0:
                gross_margin_pct = _to_decimal_q(gross_profit / net_total, "0.0001")
            else:
                gross_margin_pct = _to_decimal_q(0, "0.0001")

            db.execute(
                text(
                    "UPDATE pos_receipt_lines "
                    "SET net_total = :net, cogs_unit = :cu, cogs_total = :ct, "
                    "gross_profit = :gp, gross_margin_pct = :gmp "
                    "WHERE id = :id"
                ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
                {
                    "id": line_id,
                    "net": float(net_total),
                    "cu": float(cogs_unit),
                    "ct": float(cogs_total_money),
                    "gp": float(gross_profit),
                    "gmp": float(gross_margin_pct),
                },
            )

            # Registrar movimiento de stock con costo
            db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, "
                    "tentative, posted, unit_cost, total_cost, occurred_at"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, 'sale', 'pos_receipt', :rid, FALSE, TRUE, :uc, :tc, :occurred_at"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "pid": product_id,
                    "wid": warehouse_uuid,
                    "q": qty_sold,
                    "rid": receipt_uuid,
                    "uc": float(cogs_unit),
                    "tc": float(cogs_total_money),
                    "occurred_at": datetime.utcnow(),
                },
            )

            new_qty = current_qty - qty_sold
            if new_qty < 0:
                raise HTTPException(status_code=400, detail="insufficient_stock")

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
                "SET status = 'paid', gross_total = :gt, tax_total = :tt, "
                "warehouse_id = :wid, paid_at = NOW() "
                "WHERE id = :id"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": receipt_uuid, "gt": total, "tt": tax, "wid": warehouse_uuid},
        )

        db.commit()

        # 7. Create complementary documents if modules enabled
        try:
            from app.modules.pos.application.invoice_integration import POSInvoicingService

            service = POSInvoicingService(db, tenant_id)
            documents_created = {}

            # Create invoice if invoicing module enabled
            invoice_result = service.create_invoice_from_receipt(
                receipt_uuid,
                customer_id=None,
                invoice_series=payload.invoice_series
                if hasattr(payload, "invoice_series")
                else "A",
            )
            if invoice_result:
                documents_created["invoice"] = invoice_result

            # Create sale if sales module enabled
            sale_result = service.create_sale_from_receipt(receipt_uuid)
            if sale_result:
                documents_created["sale"] = sale_result

            # Create expense if expense module enabled and type is return
            if hasattr(payload, "type") and payload.type == "return":
                expense_result = service.create_expense_from_receipt(
                    receipt_uuid, expense_type="refund"
                )
                if expense_result:
                    documents_created["expense"] = expense_result

        except Exception as e:
            logger.warning(f"Error creating complementary documents: {e}")
            documents_created = {}

        try:
            claims = getattr(request.state, "access_claims", None)
            user_id = claims.get("user_id") if isinstance(claims, dict) else None
            audit_event(
                db,
                action="issue",
                entity_type="pos_receipt",
                entity_id=str(receipt_uuid),
                actor_type="user" if user_id else "system",
                source="api",
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
                changes={
                    "status": "paid",
                    "totals": {
                        "subtotal": float(subtotal),
                        "tax": float(tax),
                        "total": float(total),
                        "paid": float(paid),
                        "change": float(paid - total),
                    },
                    "documents_created": list(documents_created.keys()),
                },
                req=request,
            )
        except Exception:
            pass

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
            "documents_created": documents_created,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en checkout: {str(e)}")


@router.post(
    "/receipts/{receipt_id}/refund",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.refund"))],
)
def refund_receipt(
    receipt_id: str,
    payload: RefundReceiptIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reversa total del recibo: crea lÃ­neas negativas y repone stock."""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")
    tenant_id = _get_tenant_id(request)

    try:
        receipt = db.execute(
            text(
                "SELECT status, warehouse_id FROM pos_receipts WHERE id = :id FOR UPDATE"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": receipt_uuid},
        ).first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")
        if receipt[0] != "paid":
            raise HTTPException(status_code=400, detail="Recibo no estÃ¡ pagado")

        warehouse_uuid = receipt[1]
        if not warehouse_uuid:
            raise HTTPException(status_code=400, detail="Recibo sin warehouse_id")

        has_refunds = db.execute(
            text(
                "SELECT 1 FROM pos_receipt_lines WHERE receipt_id = :rid AND qty < 0 LIMIT 1"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()
        if has_refunds:
            raise HTTPException(status_code=400, detail="Recibo ya reembolsado")

        lines = db.execute(
            text(
                "SELECT product_id, qty, unit_price, tax_rate, discount_pct, line_total, "
                "net_total, cogs_unit, cogs_total, uom "
                "FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        if not lines:
            raise HTTPException(status_code=400, detail="Recibo sin lÃ­neas")

        costing = InventoryCostingService(db)

        for line in lines:
            product_id = line[0]
            qty = float(line[1])
            unit_price = float(line[2])
            tax_rate = float(line[3] or 0)
            discount_pct = float(line[4] or 0)
            line_total = float(line[5] or 0)
            net_total = float(line[6] or 0)
            cogs_unit = float(line[7] or 0)
            cogs_total = float(line[8] or 0)
            uom = line[9] or "unit"

            qty_return = abs(qty)
            qty_dec = _to_decimal_q(qty_return, "0.000001")
            cogs_unit_dec = _to_decimal_q(cogs_unit, "0.000001")

            stock_item = db.execute(
                text(
                    "SELECT id, qty FROM stock_items "
                    "WHERE warehouse_id = :wid AND product_id = :pid "
                    "FOR UPDATE"
                ),
                {"wid": str(warehouse_uuid), "pid": str(product_id)},
            ).first()
            current_qty = float(stock_item[1] or 0) if stock_item else 0.0
            if stock_item is None:
                db.execute(
                    text(
                        "INSERT INTO stock_items(id, tenant_id, warehouse_id, product_id, qty) "
                        "VALUES (gen_random_uuid(), :tid, :wid, :pid, 0)"
                    ),
                    {
                        "tid": str(tenant_id),
                        "wid": str(warehouse_uuid),
                        "pid": str(product_id),
                    },
                )

            costing.apply_inbound(
                str(tenant_id),
                str(warehouse_uuid),
                str(product_id),
                qty=qty_dec,
                unit_cost=cogs_unit_dec,
                initial_qty=_to_decimal_q(current_qty, "0.000001"),
                initial_avg_cost=cogs_unit_dec,
            )

            db.execute(
                text(
                    "UPDATE stock_items SET qty = :q "
                    "WHERE warehouse_id = :wid AND product_id = :pid"
                ),
                {"q": current_qty + qty_return, "wid": str(warehouse_uuid), "pid": str(product_id)},
            )

            refund_net = -abs(net_total or line_total)
            refund_cogs_total = -abs(cogs_total)
            refund_profit = _to_decimal_q(refund_net - refund_cogs_total, "0.01")
            if refund_net != 0:
                refund_margin = _to_decimal_q(refund_profit / Decimal(str(refund_net)), "0.0001")
            else:
                refund_margin = _to_decimal_q(0, "0.0001")

            db.execute(
                text(
                    "INSERT INTO pos_receipt_lines("
                    "receipt_id, product_id, qty, unit_price, tax_rate, discount_pct, line_total, "
                    "uom, net_total, cogs_unit, cogs_total, gross_profit, gross_margin_pct"
                    ") VALUES ("
                    ":rid, :pid, :qty, :up, :tr, :dp, :lt, :uom, :net, :cu, :ct, :gp, :gmp"
                    ")"
                ).bindparams(
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "rid": receipt_uuid,
                    "pid": product_id,
                    "qty": -abs(qty),
                    "up": unit_price,
                    "tr": tax_rate,
                    "dp": discount_pct,
                    "lt": -abs(line_total),
                    "uom": uom,
                    "net": refund_net,
                    "cu": float(cogs_unit_dec),
                    "ct": refund_cogs_total,
                    "gp": float(refund_profit),
                    "gmp": float(refund_margin),
                },
            )

            db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, tentative, "
                    "posted, unit_cost, total_cost, occurred_at"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, 'return', 'pos_receipt_refund', :rid, FALSE, TRUE, :uc, :tc, :occurred_at"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "pid": product_id,
                    "wid": warehouse_uuid,
                    "q": qty_return,
                    "rid": receipt_uuid,
                    "uc": float(cogs_unit_dec),
                    "tc": float(cogs_unit_dec * qty_dec),
                    "occurred_at": datetime.utcnow(),
                },
            )

        db.commit()

        # Best-effort: mark receipt as refunded (status is used by UI filters)
        try:
            db.execute(
                text("UPDATE pos_receipts SET status = 'refunded' WHERE id = :id").bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True))
                ),
                {"id": receipt_uuid},
            )
            db.commit()
        except Exception:
            db.rollback()

        # Create complementary documents (refund -> expense) if modules enabled
        documents_created: dict = {}
        try:
            from app.modules.pos.application.invoice_integration import POSInvoicingService

            service = POSInvoicingService(db, tenant_id)
            expense_result = service.create_expense_from_receipt(
                receipt_uuid,
                expense_type="refund",
                refund_reason=payload.reason,
                payment_method=("cash" if payload.refund_method == "cash" else None),
            )
            if expense_result:
                documents_created["expense"] = expense_result
        except Exception as e:
            logger.warning(f"Error creating refund documents: {e}")
            documents_created = {}

        try:
            claims = getattr(request.state, "access_claims", None)
            user_id = claims.get("user_id") if isinstance(claims, dict) else None
            audit_event(
                db,
                action="refund",
                entity_type="pos_receipt",
                entity_id=str(receipt_uuid),
                actor_type="user" if user_id else "system",
                source="api",
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
                changes={
                    "status": "refunded",
                    "reason": payload.reason,
                    "documents_created": list(documents_created.keys()),
                },
                req=request,
            )
        except Exception:
            pass
        return {
            "ok": True,
            "receipt_id": str(receipt_uuid),
            "status": "refunded",
            "documents_created": documents_created,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al reembolsar: {str(e)}")


@router.post(
    "/receipts/{receipt_id}/backfill_documents",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.read"))],
)
def backfill_receipt_documents(
    receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea documentos faltantes para un recibo ya pagado (rescate/backfill).

    Útil cuando el recibo quedó en `paid` pero falló la creación de invoice/sales_order en checkout.
    Idempotente: si ya existen, no crea duplicados.
    """
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = _validate_uuid(receipt_id, "Receipt ID")
    tenant_id = _get_tenant_id(request)

    # Lock receipt row to prevent concurrent backfills
    receipt = db.execute(
        text("SELECT status FROM pos_receipts WHERE id = :id FOR UPDATE").bindparams(
            bindparam("id", type_=PGUUID(as_uuid=True))
        ),
        {"id": receipt_uuid},
    ).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recibo no encontrado")
    if receipt[0] != "paid":
        raise HTTPException(status_code=400, detail="invalid_status")

    documents_created: dict = {}
    try:
        from app.modules.pos.application.invoice_integration import POSInvoicingService

        service = POSInvoicingService(db, tenant_id)

        invoice_result = service.create_invoice_from_receipt(receipt_uuid, customer_id=None)
        if invoice_result:
            documents_created["invoice"] = invoice_result

        sale_result = service.create_sale_from_receipt(receipt_uuid)
        if sale_result:
            documents_created["sale"] = sale_result

    except Exception as e:
        logger.warning(f"Error backfilling documents: {e}")

    return {"ok": True, "receipt_id": str(receipt_uuid), "documents_created": documents_created}


@router.get(
    "/receipts",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.receipt.read"))],
)
def list_receipts(
    request: Request,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    shift_id: str | None = None,
    cashier_id: str | None = None,
    limit: int = Query(default=500, le=1000),
    db: Session = Depends(get_db),
):
    """Lista recibos con filtros opcionales"""
    ensure_guc_from_request(request, db, persist=True)

    sql_parts = [
        "SELECT r.id, r.shift_id, r.register_id, r.cashier_id, r.number, r.status, "
        "r.gross_total, r.tax_total, r.created_at, r.paid_at, "
        "u.first_name, u.last_name, u.username, u.email "
        "FROM pos_receipts r "
        "LEFT JOIN company_users u ON u.id = r.cashier_id "
        "WHERE 1=1"
    ]
    params = {}

    if status:
        sql_parts.append("AND status = :st")
        params["st"] = status

    if shift_id:
        shift_uuid = _validate_uuid(shift_id, "Shift ID")
        sql_parts.append("AND shift_id = :sid")
        params["sid"] = shift_uuid

    if cashier_id:
        cashier_uuid = _validate_uuid(cashier_id, "Cashier ID")
        sql_parts.append("AND cashier_id = :cid")
        params["cid"] = cashier_uuid

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
                "cashier_id": str(r[3]) if r[3] else None,
                "number": r[4],
                "status": r[5],
                "gross_total": float(r[6]) if r[6] else 0,
                "tax_total": float(r[7]) if r[7] else 0,
                "created_at": r[8].isoformat() if r[8] else None,
                "paid_at": r[9].isoformat() if r[9] else None,
                "cashier_name": (
                    f"{r[10]} {r[11]}".strip() if r[10] or r[11] else (r[12] or r[13])
                ),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar recibos: {str(e)}")


@router.get(
    "/receipts/{receipt_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.read"))],
)
def get_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    """Obtiene un recibo con sus lÃ­neas y pagos"""
    ensure_guc_from_request(request, db, persist=True)
    rid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        rec = db.execute(
            text(
                "SELECT r.id, r.tenant_id, r.register_id, r.shift_id, r.number, r.status, r.gross_total, "
                "r.tax_total, r.currency, r.customer_id, r.invoice_id, r.created_at, r.paid_at, r.cashier_id, "
                "u.first_name, u.last_name, u.username, u.email "
                "FROM pos_receipts r "
                "LEFT JOIN company_users u ON u.id = r.cashier_id "
                "WHERE r.id = :id"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": rid},
        ).first()

        if not rec:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")

        lines = db.execute(
            text(
                "SELECT rl.id, rl.product_id, p.name, p.sku, rl.qty, rl.uom, rl.unit_price, "
                "rl.tax_rate, rl.discount_pct, rl.line_total "
                "FROM pos_receipt_lines rl "
                "LEFT JOIN products p ON p.id = rl.product_id "
                "WHERE rl.receipt_id = :rid "
                "ORDER BY rl.id"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": rid},
        ).fetchall()

        payments = db.execute(
            text(
                "SELECT id, method, amount, ref, paid_at "
                "FROM pos_payments WHERE receipt_id = :rid ORDER BY paid_at"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": rid},
        ).fetchall()

        return {
            "id": str(rec[0]),
            "tenant_id": str(rec[1]) if rec[1] else None,
            "register_id": str(rec[2]) if rec[2] else None,
            "shift_id": str(rec[3]) if rec[3] else None,
            "number": rec[4],
            "status": rec[5],
            "gross_total": float(rec[6] or 0),
            "tax_total": float(rec[7] or 0),
            "currency": rec[8],
            "customer_id": str(rec[9]) if rec[9] else None,
            "invoice_id": str(rec[10]) if rec[10] else None,
            "created_at": rec[11].isoformat() if rec[11] else None,
            "paid_at": rec[12].isoformat() if rec[12] else None,
            "cashier_id": str(rec[13]) if rec[13] else None,
            "cashier_name": (
                f"{rec[14]} {rec[15]}".strip() if rec[14] or rec[15] else (rec[16] or rec[17])
            ),
            "lines": [
                {
                    "id": str(line_data[0]) if line_data[0] else None,
                    "product_id": str(line_data[1]) if line_data[1] else None,
                    "product_name": line_data[2],
                    "product_code": line_data[3],
                    "qty": float(line_data[4] or 0),
                    "uom": line_data[5],
                    "unit_price": float(line_data[6] or 0),
                    "tax_rate": float(line_data[7] or 0),
                    "discount_pct": float(line_data[8] or 0),
                    "line_total": float(line_data[9] or 0),
                }
                for line_data in lines
            ],
            "payments": [
                {
                    "id": str(p[0]) if p[0] else None,
                    "method": p[1],
                    "amount": float(p[2] or 0),
                    "ref": p[3],
                    "paid_at": p[4].isoformat() if p[4] else None,
                }
                for p in payments
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener recibo: {str(e)}")


@router.delete(
    "/receipts/{receipt_id}",
    status_code=204,
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def delete_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    """Elimina un recibo en borrador o sin pagar."""
    ensure_guc_from_request(request, db, persist=True)
    rid = _validate_uuid(receipt_id, "Receipt ID")

    try:
        row = db.execute(
            text("SELECT status FROM pos_receipts WHERE id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": rid},
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")

        status = row[0]
        if status not in ("draft", "unpaid"):
            raise HTTPException(
                status_code=400, detail="Solo se pueden borrar recibos en borrador o sin pagar"
            )

        db.execute(
            text("DELETE FROM pos_payments WHERE receipt_id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": rid},
        )
        db.execute(
            text("DELETE FROM pos_receipt_lines WHERE receipt_id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": rid},
        )
        db.execute(
            text("DELETE FROM pos_receipts WHERE id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": rid},
        )
        db.commit()
        try:
            tenant_id = _get_tenant_id(request)
            claims = getattr(request.state, "access_claims", None)
            user_id = claims.get("user_id") if isinstance(claims, dict) else None
            audit_event(
                db,
                action="delete",
                entity_type="pos_receipt",
                entity_id=str(rid),
                actor_type="user" if user_id else "system",
                source="api",
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
                changes={"status": status},
                req=request,
            )
        except Exception:
            pass
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar recibo: {str(e)}")


@router.get(
    "/receipts/{receipt_id}/print",
    dependencies=[Depends(require_permission("pos.receipt.print"))],
)
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
    <div class="center">Nº {receipt[1] or "N/A"}</div>
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
                    "INSERT INTO pos_payments(id, receipt_id, method, amount, ref, paid_at) "
                    "VALUES (:id, :rid, :m, :a, :ref, :paid_at)"
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": uuid4(),
                    "rid": receipt_uuid,
                    "m": payment.method,
                    "a": payment.amount,
                    "ref": payment.ref,
                    "paid_at": datetime.utcnow(),
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
    tenant_id = _get_tenant_id(request)

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
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, tentative, posted, occurred_at"
                    ") VALUES (:tid, :pid, :wid, :q, 'issue', 'pos_receipt', :rid, FALSE, TRUE, :occurred_at)"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "pid": it[0],
                    "wid": wh_id,
                    "q": float(it[1]),
                    "rid": receipt_uuid,
                    "occurred_at": datetime.utcnow(),
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
                        "INSERT INTO stock_items(tenant_id, warehouse_id, product_id, qty) "
                        "VALUES (:tid, :wid, :pid, 0)"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("wid", type_=PGUUID(as_uuid=True)),
                        bindparam("pid", type_=PGUUID(as_uuid=True)),
                    ),
                    {"tid": tenant_id, "wid": wh_id, "pid": it[0]},
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

        # Actualizar recibo (use 'paid' not 'posted' - valid statuses: draft, paid, voided, invoiced)
        db.execute(
            text(
                "UPDATE pos_receipts SET status = 'paid', totals = :tot WHERE id = :rid"
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

        return {"id": str(receipt_uuid), "status": "paid", "total": total}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar recibo: {str(e)}")


# ============================================================================
# ENDPOINTS - ANALYTICS (MARGINS)
# ============================================================================


@router.get(
    "/analytics/margins/products",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.analytics.view"))],
)
def margins_by_product(
    request: Request,
    db: Session = Depends(get_db),
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    warehouse_id: str | None = None,
    limit: int = Query(default=100, le=500),
):
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    rows = db.execute(
        text(
            "SELECT "
            "l.product_id, "
            "SUM(l.net_total) AS sales_net, "
            "SUM(l.cogs_total) AS cogs, "
            "SUM(l.gross_profit) AS gross_profit, "
            "CASE WHEN SUM(l.net_total) > 0 "
            "THEN SUM(l.gross_profit)/SUM(l.net_total) "
            "ELSE 0 END AS margin_pct "
            "FROM pos_receipt_lines l "
            "JOIN pos_receipts r ON r.id = l.receipt_id "
            "WHERE r.tenant_id = :tid "
            "AND r.status IN ('paid','invoiced') "
            "AND r.created_at >= :from_date "
            "AND r.created_at < :to_date "
            "AND (:warehouse_id IS NULL OR r.warehouse_id = :warehouse_id) "
            "GROUP BY l.product_id "
            "ORDER BY gross_profit DESC "
            "LIMIT :limit"
        ),
        {
            "tid": tenant_id,
            "from_date": from_date,
            "to_date": to_date,
            "warehouse_id": warehouse_id,
            "limit": limit,
        },
    ).fetchall()

    return [
        {
            "product_id": str(r[0]),
            "sales_net": float(r[1] or 0),
            "cogs": float(r[2] or 0),
            "gross_profit": float(r[3] or 0),
            "margin_pct": float(r[4] or 0),
        }
        for r in rows
    ]


@router.get(
    "/analytics/margins/customers",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.analytics.view"))],
)
def margins_by_customer(
    request: Request,
    db: Session = Depends(get_db),
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    warehouse_id: str | None = None,
    limit: int = Query(default=100, le=500),
):
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    rows = db.execute(
        text(
            "SELECT "
            "r.customer_id, "
            "SUM(l.net_total) AS sales_net, "
            "SUM(l.cogs_total) AS cogs, "
            "SUM(l.gross_profit) AS gross_profit, "
            "CASE WHEN SUM(l.net_total) > 0 "
            "THEN SUM(l.gross_profit)/SUM(l.net_total) "
            "ELSE 0 END AS margin_pct "
            "FROM pos_receipt_lines l "
            "JOIN pos_receipts r ON r.id = l.receipt_id "
            "WHERE r.tenant_id = :tid "
            "AND r.status IN ('paid','invoiced') "
            "AND r.created_at >= :from_date "
            "AND r.created_at < :to_date "
            "AND (:warehouse_id IS NULL OR r.warehouse_id = :warehouse_id) "
            "GROUP BY r.customer_id "
            "ORDER BY gross_profit DESC "
            "LIMIT :limit"
        ),
        {
            "tid": tenant_id,
            "from_date": from_date,
            "to_date": to_date,
            "warehouse_id": warehouse_id,
            "limit": limit,
        },
    ).fetchall()

    return [
        {
            "customer_id": str(r[0]) if r[0] else None,
            "sales_net": float(r[1] or 0),
            "cogs": float(r[2] or 0),
            "gross_profit": float(r[3] or 0),
            "margin_pct": float(r[4] or 0),
        }
        for r in rows
    ]


@router.get(
    "/analytics/margins/product/{product_id}/lines",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.analytics.view"))],
)
def margins_product_lines(
    product_id: str,
    request: Request,
    db: Session = Depends(get_db),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    warehouse_id: str | None = None,
    limit: int = Query(default=200, le=1000),
):
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)
    pid = _validate_uuid(product_id, "Product ID")

    sql = (
        "SELECT l.id, l.receipt_id, l.qty, l.unit_price, l.net_total, "
        "l.cogs_unit, l.cogs_total, l.gross_profit, l.gross_margin_pct, "
        "r.created_at "
        "FROM pos_receipt_lines l "
        "JOIN pos_receipts r ON r.id = l.receipt_id "
        "WHERE r.tenant_id = :tid "
        "AND r.status IN ('paid','invoiced') "
        "AND l.product_id = :pid "
        "AND (:warehouse_id IS NULL OR r.warehouse_id = :warehouse_id) "
    )
    if from_date:
        sql += "AND r.created_at >= :from_date "
    if to_date:
        sql += "AND r.created_at < :to_date "
    sql += "ORDER BY r.created_at DESC LIMIT :limit"

    rows = db.execute(
        text(sql),
        {
            "tid": tenant_id,
            "pid": pid,
            "from_date": from_date,
            "to_date": to_date,
            "warehouse_id": warehouse_id,
            "limit": limit,
        },
    ).fetchall()

    return [
        {
            "line_id": str(r[0]),
            "receipt_id": str(r[1]),
            "qty": float(r[2] or 0),
            "unit_price": float(r[3] or 0),
            "net_total": float(r[4] or 0),
            "cogs_unit": float(r[5] or 0),
            "cogs_total": float(r[6] or 0),
            "gross_profit": float(r[7] or 0),
            "gross_margin_pct": float(r[8] or 0),
            "created_at": r[9].isoformat() if r[9] else None,
        }
        for r in rows
    ]


# ============================================================================
# ENDPOINTS DE SALUD Y UTILIDADES
# ============================================================================


@router.get(
    "/daily_counts",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
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


@router.get(
    "/numbering/counters",
    response_model=list[NumberingCounterOut],
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def list_numbering_counters(
    request: Request,
    doc_type: str | None = None,
    year: int | None = Query(default=None, ge=2000),
    series: str | None = None,
    db: Session = Depends(get_db),
):
    """Lista contadores de numeración por tenant."""
    tenant_id = _get_tenant_id(request)
    sql_parts = [
        "SELECT doc_type, year, series, current_no, updated_at",
        "FROM doc_number_counters",
        "WHERE tenant_id = :tenant_id",
    ]
    params: dict[str, object] = {"tenant_id": tenant_id}

    if doc_type:
        sql_parts.append("AND doc_type = :doc_type")
        params["doc_type"] = doc_type.strip()
    if year is not None:
        sql_parts.append("AND year = :year")
        params["year"] = year
    if series:
        sql_parts.append("AND series = :series")
        params["series"] = series.strip() or "A"

    sql_parts.append("ORDER BY year DESC, doc_type, series")
    sql = " ".join(sql_parts)

    rows = db.execute(text(sql), params).mappings().all()
    return [
        NumberingCounterOut(
            doc_type=row["doc_type"],
            year=row["year"],
            series=row["series"],
            current_no=row["current_no"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.put(
    "/numbering/counters",
    response_model=NumberingCounterOut,
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def upsert_numbering_counter(
    payload: NumberingCounterUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea o actualiza el contador de numeración para un tenant."""
    tenant_id = _get_tenant_id(request)
    doc_type = payload.doc_type.strip()
    series = (payload.series or "").strip() or "A"

    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type requerido")

    row = (
        db.execute(
            text(
                """
            INSERT INTO doc_number_counters (
                tenant_id, doc_type, year, series, current_no, created_at, updated_at
            )
            VALUES (:tenant_id, :doc_type, :year, :series, :current_no, now(), now())
            ON CONFLICT (tenant_id, doc_type, year, series)
            DO UPDATE SET
                current_no = EXCLUDED.current_no,
                updated_at = now()
            RETURNING doc_type, year, series, current_no, updated_at
            """
            ),
            {
                "tenant_id": tenant_id,
                "doc_type": doc_type,
                "year": payload.year,
                "series": series,
                "current_no": payload.current_no,
            },
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el contador")

    db.commit()
    return NumberingCounterOut(
        doc_type=row["doc_type"],
        year=row["year"],
        series=row["series"],
        current_no=row["current_no"],
        updated_at=row["updated_at"],
    )


@router.get(
    "/numbering/series",
    response_model=list[DocSeriesOut],
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def list_doc_series(
    request: Request,
    register_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Lista series de numeracion (doc_series) para el tenant."""
    tenant_id = _get_tenant_id(request)
    params: dict[str, object] = {"tenant_id": tenant_id}
    sql_parts = [
        "SELECT id, register_id, doc_type, name, current_no, reset_policy, active, created_at",
        "FROM doc_series",
        "WHERE tenant_id = :tenant_id",
    ]
    if register_id:
        rid = _validate_uuid(register_id, "Register ID")
        sql_parts.append("AND register_id = :register_id")
        params["register_id"] = rid
    sql_parts.append("ORDER BY doc_type, name")

    rows = db.execute(text(" ".join(sql_parts)), params).mappings().all()
    return [
        DocSeriesOut(
            id=str(r["id"]),
            register_id=str(r["register_id"]) if r["register_id"] else None,
            doc_type=r["doc_type"],
            name=r["name"],
            current_no=r["current_no"],
            reset_policy=r["reset_policy"],
            active=bool(r["active"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.put(
    "/numbering/series",
    response_model=DocSeriesOut,
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def upsert_doc_series(
    payload: DocSeriesUpsertIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea o actualiza una serie de numeracion."""
    tenant_id = _get_tenant_id(request)
    reg_id = payload.register_id
    params = {
        "tenant_id": tenant_id,
        "register_id": reg_id,
        "doc_type": payload.doc_type.strip(),
        "name": payload.name.strip(),
    }

    if payload.id:
        row = (
            db.execute(
                text(
                    """
                UPDATE doc_series
                SET current_no = :current_no,
                    reset_policy = :reset_policy,
                    active = :active
                WHERE id = CAST(:id AS uuid)
                  AND tenant_id = :tenant_id
                RETURNING id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                """
                ),
                {
                    "id": payload.id,
                    "tenant_id": tenant_id,
                    "current_no": payload.current_no,
                    "reset_policy": payload.reset_policy,
                    "active": payload.active,
                },
            )
            .mappings()
            .first()
        )
    else:
        existing = db.execute(
            text(
                """
                SELECT id FROM doc_series
                WHERE tenant_id = :tenant_id
                  AND doc_type = :doc_type
                  AND name = :name
                  AND (register_id IS NOT DISTINCT FROM CAST(:register_id AS uuid))
                LIMIT 1
                """
            ),
            params,
        ).scalar()

        if existing:
            row = (
                db.execute(
                    text(
                        """
                    UPDATE doc_series
                    SET current_no = :current_no,
                        reset_policy = :reset_policy,
                        active = :active
                    WHERE id = CAST(:id AS uuid)
                    RETURNING id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                    """
                    ),
                    {
                        "id": existing,
                        "current_no": payload.current_no,
                        "reset_policy": payload.reset_policy,
                        "active": payload.active,
                    },
                )
                .mappings()
                .first()
            )
        else:
            row = (
                db.execute(
                    text(
                        """
                    INSERT INTO doc_series (
                        id, tenant_id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                    )
                    VALUES (
                        gen_random_uuid(), :tenant_id, CAST(:register_id AS uuid),
                        :doc_type, :name, :current_no, :reset_policy, :active, now()
                    )
                    RETURNING id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                    """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "register_id": reg_id,
                        "doc_type": payload.doc_type.strip(),
                        "name": payload.name.strip(),
                        "current_no": payload.current_no,
                        "reset_policy": payload.reset_policy,
                        "active": payload.active,
                    },
                )
                .mappings()
                .first()
            )

    if not row:
        raise HTTPException(status_code=500, detail="No se pudo actualizar la serie")

    db.commit()
    return DocSeriesOut(
        id=str(row["id"]),
        register_id=str(row["register_id"]) if row["register_id"] else None,
        doc_type=row["doc_type"],
        name=row["name"],
        current_no=row["current_no"],
        reset_policy=row["reset_policy"],
        active=bool(row["active"]),
        created_at=row["created_at"],
    )


@router.post(
    "/numbering/series/reset_yearly",
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def reset_yearly_series(
    request: Request,
    db: Session = Depends(get_db),
):
    """Resetea a 0 las series con reset_policy=yearly."""
    tenant_id = _get_tenant_id(request)
    result = db.execute(
        text(
            """
            UPDATE doc_series
            SET current_no = 0
            WHERE tenant_id = :tenant_id
              AND reset_policy = 'yearly'
            """
        ),
        {"tenant_id": tenant_id},
    )
    db.commit()
    return {"updated": result.rowcount}


@router.get("/health", include_in_schema=False)
def health_check():
    """Endpoint de salud para verificar que el mÃ³dulo POS estÃ¡ funcionando"""
    return {
        "status": "healthy",
        "module": "pos",
        "timestamp": datetime.utcnow().isoformat(),
    }
