"""
POS Module — Dependencias y utilidades compartidas entre routers.

Contiene:
- Helpers de claims JWT
- Validación de UUIDs
- Helpers de Decimal
- Helpers de stock
- Helpers de settings/config
- Todos los modelos Pydantic de request/response del módulo POS
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models.accounting.pos_settings import TenantAccountingSettings
from app.modules.settings.infrastructure.repositories import SettingsRepo

logger = logging.getLogger(__name__)


# ============================================================================
# CLAIMS / AUTH
# ============================================================================


def get_tenant_id(request: Request) -> UUID:
    """Obtiene tenant_id como UUID desde los claims JWT."""
    claims = getattr(request.state, "access_claims", {}) or {}
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="invalid_claims")
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_not_found")
    try:
        return UUID(str(tenant_id))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_tenant_id")


def get_user_id(request: Request) -> UUID:
    """Obtiene user_id como UUID desde los claims JWT."""
    claims = getattr(request.state, "access_claims", {}) or {}
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="invalid_claims")
    user_id = claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="user_not_authenticated")
    try:
        return UUID(str(user_id))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_user_id")


def get_claims(request: Request) -> dict:
    return getattr(request.state, "access_claims", {}) or {}


def is_company_admin(claims: dict) -> bool:
    return bool(
        claims.get("is_company_admin")
        or claims.get("is_admin_company")
        or claims.get("es_admin_empresa")
    )


# ============================================================================
# VALIDACIÓN
# ============================================================================


def validate_uuid(value: str, field_name: str = "ID") -> UUID:
    """Valida y convierte un string a UUID."""
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} inválido: debe ser un UUID válido",
        )


# ============================================================================
# DECIMAL
# ============================================================================


def to_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_decimal_q(value: float | Decimal, q: str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)


# ============================================================================
# SETTINGS / CONFIG
# ============================================================================


def ensure_pos_accounting_settings(settings: TenantAccountingSettings) -> None:
    """Valida que las cuentas contables POS estén configuradas."""
    missing: list[str] = []
    if not getattr(settings, "cash_account_id", None):
        missing.append("cash_account_id")
    if not getattr(settings, "bank_account_id", None):
        missing.append("bank_account_id")
    if not getattr(settings, "sales_bakery_account_id", None):
        missing.append("sales_account_id (ventas)")
    if not getattr(settings, "vat_output_account_id", None):
        missing.append("vat_output_account_id")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Config contable POS incompleta: faltan " + ", ".join(missing),
        )


def resolve_tenant_currency(db: Session, tenant_id: UUID) -> str:
    """Resuelve la moneda base del tenant para POS."""
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

    base = db.execute(
        text(
            "SELECT NULLIF(UPPER(TRIM(base_currency)), '') FROM tenants WHERE id = :tid LIMIT 1"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id},
    ).first()
    if base and base[0]:
        return str(base[0]).strip().upper()

    return "USD"


def resolve_inventory_costing_method(db: Session) -> str:
    """Obtiene el método de costeo configurado para inventario/POS."""
    try:
        repo = SettingsRepo(db)
        inventory_cfg = repo.get("inventory") or {}
        pos_cfg = repo.get("pos") or {}
        candidate = None
        if isinstance(inventory_cfg, dict):
            candidate = inventory_cfg.get("costing_method")
        if candidate is None and isinstance(pos_cfg, dict):
            candidate = (pos_cfg.get("inventory") or {}).get("costing_method")
        method = str(candidate or "avg").strip().lower()
        return method if method in {"avg", "fifo", "lifo"} else "avg"
    except Exception:
        return "avg"


def resolve_default_tax_rate(db: Session) -> float | None:
    """Obtiene la tasa de IVA por defecto desde settings."""
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


def is_tax_enabled(db: Session) -> bool:
    """Lee si los impuestos están habilitados desde settings."""
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


# ============================================================================
# STOCK HELPERS
# ============================================================================


def normalize_lot(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def load_locked_stock_rows(db: Session, warehouse_id: UUID, product_id: UUID):
    return db.execute(
        text(
            "SELECT id, qty, lot, expires_at FROM stock_items "
            "WHERE warehouse_id = :wid AND product_id = :pid "
            "FOR UPDATE"
        ).bindparams(
            bindparam("wid", type_=PGUUID(as_uuid=True)),
            bindparam("pid", type_=PGUUID(as_uuid=True)),
        ),
        {"wid": warehouse_id, "pid": product_id},
    ).fetchall()


def sum_stock_rows_qty(rows) -> float:
    return float(sum(float(row[1] or 0) for row in rows))


def resolve_outbound_stock_row(rows):
    positive_rows = [row for row in rows if float(row[1] or 0) > 0]
    if len(positive_rows) > 1:
        raise HTTPException(status_code=409, detail="lot_selection_required")
    if positive_rows:
        return positive_rows[0]
    return rows[0] if rows else None


def resolve_outbound_stock_fifo(rows, qty_needed: float) -> tuple[list[tuple], float]:
    """FIFO automático entre lotes.

    Orden de consumo: sin lote primero (stock antiguo sin trazabilidad),
    luego por nombre de lote ascendente, luego por vencimiento ascendente.

    Returns:
        (allocations, remaining)
        allocations: list of (stock_row, alloc_qty, lot, expires_at)
        remaining: qty no cubierta (> 0 si stock insuficiente)
    """

    def _sort_key(row):
        lot = normalize_lot(row[2])
        exp = row[3]
        return (
            0 if lot is None else 1,
            lot or "",
            str(exp) if exp is not None else "",
        )

    positive_rows = sorted(
        [row for row in rows if float(row[1] or 0) > 0],
        key=_sort_key,
    )

    allocations: list[tuple] = []
    remaining = qty_needed

    for row in positive_rows:
        if remaining <= 0:
            break
        available = float(row[1] or 0)
        alloc = min(available, remaining)
        allocations.append((row, alloc, normalize_lot(row[2]), row[3]))
        remaining -= alloc

    return allocations, remaining


def resolve_selected_stock_row(rows, *, lot: str | None, expires_at: date | None):
    normalized_lot = normalize_lot(lot)
    matches = []
    for row in rows:
        row_lot = normalize_lot(row[2])
        row_exp = row[3]
        if row_lot != normalized_lot:
            continue
        if expires_at is None:
            if row_exp is not None:
                continue
        elif str(row_exp) != str(expires_at):
            continue
        matches.append(row)

    if not matches:
        raise HTTPException(status_code=400, detail="selected_lot_not_found")

    positive_rows = [row for row in matches if float(row[1] or 0) > 0]
    if len(positive_rows) > 1 or (len(matches) > 1 and not positive_rows):
        raise HTTPException(status_code=409, detail="lot_selection_required")
    if positive_rows:
        return positive_rows[0]
    return matches[0]


def ensure_generic_stock_row(
    db: Session,
    *,
    tenant_id: UUID,
    warehouse_id: UUID,
    product_id: UUID,
):
    row = db.execute(
        text(
            "SELECT id, qty FROM stock_items "
            "WHERE warehouse_id = :wid AND product_id = :pid "
            "AND lot IS NULL AND expires_at IS NULL "
            "FOR UPDATE"
        ).bindparams(
            bindparam("wid", type_=PGUUID(as_uuid=True)),
            bindparam("pid", type_=PGUUID(as_uuid=True)),
        ),
        {"wid": warehouse_id, "pid": product_id},
    ).first()
    if row is not None:
        return row
    db.execute(
        text(
            "INSERT INTO stock_items(id, tenant_id, warehouse_id, product_id, qty, lot, expires_at) "
            "VALUES (gen_random_uuid(), :tid, :wid, :pid, 0, NULL, NULL)"
        ).bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True)),
            bindparam("wid", type_=PGUUID(as_uuid=True)),
            bindparam("pid", type_=PGUUID(as_uuid=True)),
        ),
        {"tid": tenant_id, "wid": warehouse_id, "pid": product_id},
    )
    return db.execute(
        text(
            "SELECT id, qty FROM stock_items "
            "WHERE warehouse_id = :wid AND product_id = :pid "
            "AND lot IS NULL AND expires_at IS NULL "
            "FOR UPDATE"
        ).bindparams(
            bindparam("wid", type_=PGUUID(as_uuid=True)),
            bindparam("pid", type_=PGUUID(as_uuid=True)),
        ),
        {"wid": warehouse_id, "pid": product_id},
    ).first()


# ============================================================================
# MODELOS PYDANTIC — INPUT
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
            validate_uuid(v, "Warehouse ID")
        return v


class OpenShiftIn(BaseModel):
    register_id: str
    opening_float: float = Field(ge=0, description="Monto inicial debe ser >= 0")

    @field_validator("register_id")
    @classmethod
    def validate_register_id(cls, v):
        validate_uuid(v, "Register ID")
        return v


class CloseShiftIn(BaseModel):
    closing_cash: float = Field(ge=0)
    loss_amount: float | None = 0.0
    loss_note: str | None = None


class ReceiptLineIn(BaseModel):
    product_id: str
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0, le=1, default=0)
    discount_pct: float = Field(ge=0, le=100, default=0)
    uom: str = Field(default="unit", max_length=20)

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v):
        validate_uuid(v, "Product ID")
        return v

    @property
    def line_total(self) -> float:
        subtotal = self.qty * self.unit_price
        discount = subtotal * (self.discount_pct / 100)
        return subtotal - discount


class PaymentIn(BaseModel):
    method: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    ref: str | None = Field(default=None, max_length=200)


class ReceiptCreateIn(BaseModel):
    shift_id: str
    register_id: str
    cashier_id: str | None = None
    customer_id: str | None = None
    client_request_id: str | None = Field(default=None, min_length=1, max_length=120)
    lines: list[ReceiptLineIn] = Field(default_factory=list)
    payments: list[PaymentIn] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("shift_id", "register_id", "cashier_id", "customer_id")
    @classmethod
    def validate_ids(cls, v):
        if v is not None:
            validate_uuid(v, "ID")
        return v


class CheckoutLineStockAllocationIn(BaseModel):
    lot: str | None = Field(default=None, max_length=100)
    expires_at: date | None = None
    qty: float = Field(gt=0)

    @field_validator("lot")
    @classmethod
    def _normalize(cls, v):
        return normalize_lot(v)


class CheckoutLineStockSelectionIn(BaseModel):
    line_id: str
    allocations: list[CheckoutLineStockAllocationIn] = Field(min_length=1)

    @field_validator("line_id")
    @classmethod
    def validate_line_id(cls, v):
        validate_uuid(v, "Receipt line ID")
        return v


class CheckoutIn(BaseModel):
    payments: list[PaymentIn] = Field(min_length=1)
    warehouse_id: str | None = None
    stock_selections: list[CheckoutLineStockSelectionIn] = Field(default_factory=list)

    @field_validator("warehouse_id")
    @classmethod
    def validate_warehouse_id(cls, v):
        if v is not None:
            validate_uuid(v, "Warehouse ID")
        return v


class CalculateTotalsLineIn(BaseModel):
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0, le=1, default=0)
    discount_pct: float = Field(ge=0, le=100, default=0)


class CalculateTotalsIn(BaseModel):
    lines: list[CalculateTotalsLineIn]
    global_discount_pct: float = Field(ge=0, le=100, default=0)


class CalculateTotalsOut(BaseModel):
    subtotal: float
    line_discounts: float
    global_discount: float
    base_after_discounts: float
    tax: float
    total: float


class RefundReceiptIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    refund_method: str | None = None
    restock: bool | None = None
    line_ids: list[str] | None = None
    store_credit_expiry_months: int | None = None


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
            validate_uuid(v, "Register ID")
        return v
