"""Tenant HTTP endpoints for Quotes (presupuestos)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.core.dependencies import get_tenant_uuid
from app.db.rls import ensure_rls
from app.models.quotes import Quote, QuoteStatus
from app.modules.shared.services.document_converter import DocumentConverter

router = APIRouter(
    prefix="/quotes",
    tags=["Quotes"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class QuoteLineIn(BaseModel):
    product_id: str | None = None
    name: str | None = None
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)


class QuoteLineOut(QuoteLineIn):
    line_total: float = 0


class QuoteIn(BaseModel):
    customer_id: str | None = None
    currency: str | None = None
    valid_until: date | None = None
    notes: str | None = None
    lines: list[QuoteLineIn] = Field(default_factory=list)


class QuoteUpdateIn(BaseModel):
    customer_id: str | None = None
    currency: str | None = None
    valid_until: date | None = None
    notes: str | None = None
    lines: list[QuoteLineIn] | None = None


class QuoteOut(BaseModel):
    id: str
    number: str | None
    customer_id: str | None
    status: str
    currency: str | None
    subtotal: float
    tax: float
    total: float
    quote_date: date | None
    valid_until: date | None
    notes: str | None
    converted_to_order_id: str | None
    lines: list[QuoteLineOut] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_or_none(value: str | None) -> UUID | None:
    if value is None or value == "":
        return None
    return UUID(str(value))


def _compute_totals(lines: list[QuoteLineIn]) -> tuple[Decimal, Decimal, Decimal, list[dict]]:
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    serialized: list[dict] = []
    for ln in lines:
        qty = Decimal(str(ln.qty))
        price = Decimal(str(ln.unit_price))
        gross = qty * price
        discount = gross * Decimal(str(ln.discount_percent)) / Decimal("100")
        net = gross - discount
        rate = Decimal(str(ln.tax_rate))
        if rate > 1:
            rate = rate / Decimal("100")
        tax = net * rate
        line_total = net + tax
        subtotal += net
        tax_total += tax
        serialized.append(
            {
                "product_id": ln.product_id,
                "name": ln.name,
                "qty": float(qty),
                "unit_price": float(price),
                "tax_rate": float(rate),
                "discount_percent": float(ln.discount_percent),
                "line_total": float(line_total),
            }
        )
    return subtotal, tax_total, subtotal + tax_total, serialized


def _to_out(q: Quote) -> QuoteOut:
    lines_raw = q.lines or []
    lines = [
        QuoteLineOut(
            product_id=str(ln.get("product_id")) if ln.get("product_id") else None,
            name=ln.get("name"),
            qty=float(ln.get("qty") or 0),
            unit_price=float(ln.get("unit_price") or 0),
            tax_rate=float(ln.get("tax_rate") or 0),
            discount_percent=float(ln.get("discount_percent") or 0),
            line_total=float(ln.get("line_total") or 0),
        )
        for ln in lines_raw
    ]
    return QuoteOut(
        id=str(q.id),
        number=q.number,
        customer_id=str(q.customer_id) if q.customer_id else None,
        status=q.status,
        currency=q.currency,
        subtotal=float(q.subtotal or 0),
        tax=float(q.tax or 0),
        total=float(q.total or 0),
        quote_date=q.quote_date,
        valid_until=q.valid_until,
        notes=q.notes,
        converted_to_order_id=str(q.converted_to_order_id) if q.converted_to_order_id else None,
        lines=lines,
        created_at=q.created_at.isoformat() if getattr(q, "created_at", None) else None,
        updated_at=q.updated_at.isoformat() if getattr(q, "updated_at", None) else None,
    )


def _user_id_from_request(request: Request) -> UUID | None:
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        return None
    uid = claims.get("user_id") or claims.get("sub")
    try:
        return UUID(str(uid)) if uid else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[QuoteOut])
def list_quotes(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = None,
    customer_id: str | None = None,
    q: str | None = Query(default=None, description="Buscar por número"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(require_permission("quotes.manage")),
):
    tenant_uuid = get_tenant_uuid(request)
    qry = db.query(Quote).filter(Quote.tenant_id == tenant_uuid)
    if status:
        qry = qry.filter(Quote.status == status.upper())
    if customer_id:
        qry = qry.filter(Quote.customer_id == _uuid_or_none(customer_id))
    if q:
        qry = qry.filter(Quote.number.ilike(f"%{q}%"))
    rows = qry.order_by(Quote.created_at.desc()).offset(offset).limit(limit).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=QuoteOut, status_code=201)
def create_quote(
    payload: QuoteIn,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("quotes.manage")),
):
    if not payload.lines:
        raise HTTPException(status_code=400, detail="lines_required")
    tenant_uuid = get_tenant_uuid(request)
    subtotal, tax, total, serialized = _compute_totals(payload.lines)
    quote = Quote(
        tenant_id=tenant_uuid,
        number=f"Q-{str(tenant_uuid)[:8]}-{uuid4().hex[:6]}",
        customer_id=_uuid_or_none(payload.customer_id),
        status=QuoteStatus.DRAFT.value,
        lines=serialized,
        subtotal=float(subtotal),
        tax=float(tax),
        total=float(total),
        currency=payload.currency,
        valid_until=payload.valid_until,
        notes=payload.notes,
        created_by=_user_id_from_request(request),
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return _to_out(quote)


def _get_quote_or_404(db: Session, tenant_uuid: UUID, quote_id: str) -> Quote:
    try:
        qid = UUID(str(quote_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_uuid")
    quote = db.query(Quote).filter(Quote.id == qid, Quote.tenant_id == tenant_uuid).first()
    if not quote:
        raise HTTPException(status_code=404, detail="quote_not_found")
    return quote


@router.get("/{quote_id}", response_model=QuoteOut)
def get_quote(
    quote_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("quotes.manage")),
):
    tenant_uuid = get_tenant_uuid(request)
    return _to_out(_get_quote_or_404(db, tenant_uuid, quote_id))


@router.put("/{quote_id}", response_model=QuoteOut)
def update_quote(
    quote_id: str,
    payload: QuoteUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("quotes.manage")),
):
    tenant_uuid = get_tenant_uuid(request)
    quote = _get_quote_or_404(db, tenant_uuid, quote_id)
    if quote.status != QuoteStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="quote_not_editable")
    if payload.customer_id is not None:
        quote.customer_id = _uuid_or_none(payload.customer_id)
    if payload.currency is not None:
        quote.currency = payload.currency
    if payload.valid_until is not None:
        quote.valid_until = payload.valid_until
    if payload.notes is not None:
        quote.notes = payload.notes
    if payload.lines is not None:
        if not payload.lines:
            raise HTTPException(status_code=400, detail="lines_required")
        subtotal, tax, total, serialized = _compute_totals(payload.lines)
        quote.lines = serialized
        quote.subtotal = float(subtotal)
        quote.tax = float(tax)
        quote.total = float(total)
    db.commit()
    db.refresh(quote)
    return _to_out(quote)


@router.post("/{quote_id}/approve", response_model=QuoteOut)
def approve_quote(
    quote_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("quotes.manage")),
):
    tenant_uuid = get_tenant_uuid(request)
    quote = _get_quote_or_404(db, tenant_uuid, quote_id)
    if quote.status != QuoteStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="quote_not_in_draft")
    quote.status = QuoteStatus.APPROVED.value
    quote.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(quote)
    return _to_out(quote)


class ConvertOut(BaseModel):
    quote_id: str
    sales_order_id: str


@router.post("/{quote_id}/convert", response_model=ConvertOut)
def convert_quote(
    quote_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("quotes.manage")),
):
    tenant_uuid = get_tenant_uuid(request)
    quote = _get_quote_or_404(db, tenant_uuid, quote_id)
    converter = DocumentConverter(db)
    try:
        order_id = converter.quote_to_sales_order(
            quote_id=quote.id,
            tenant_id=tenant_uuid,
            user_id=_user_id_from_request(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ConvertOut(quote_id=str(quote.id), sales_order_id=str(order_id))


@router.delete("/{quote_id}", status_code=204)
def delete_quote(
    quote_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("quotes.manage")),
):
    tenant_uuid = get_tenant_uuid(request)
    quote = _get_quote_or_404(db, tenant_uuid, quote_id)
    if quote.status != QuoteStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="only_drafts_can_be_deleted")
    db.delete(quote)
    db.commit()
    return None
