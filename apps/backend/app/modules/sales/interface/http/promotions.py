from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import ARRAY, Boolean, Column, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

router = APIRouter(
    prefix="/promotions",
    tags=["Promotions"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_id(request: Request) -> UUID:
    claims = request.state.access_claims
    return UUID(str(claims.get("tenant_id") or claims.get("empresa_id")))


# ---------------------------------------------------------------------------
# SQLAlchemy model (inline para evitar dependencia circular)
# ---------------------------------------------------------------------------

from app.config.database import Base  # noqa: E402


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    type = Column(String(20), nullable=False, default="percentage")
    value = Column(Numeric(12, 4), nullable=False, default=0)
    valid_from = Column(Date)
    valid_to = Column(Date)
    min_purchase = Column(Numeric(12, 2), default=0)
    applies_to = Column(String(20), nullable=False, default="all")
    product_ids = Column(ARRAY(PGUUID(as_uuid=True)))
    promo_code = Column(String(100))
    is_active = Column(Boolean, nullable=False, default=True)
    usage_limit = Column(Integer)
    usage_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PromotionIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    type: str = Field("percentage", pattern="^(percentage|fixed|bogo)$")
    value: float = Field(..., ge=0)
    valid_from: date | None = None
    valid_to: date | None = None
    min_purchase: float = Field(0, ge=0)
    applies_to: str = Field("all", pattern="^(all|products)$")
    product_ids: list[str] | None = None
    promo_code: str | None = Field(None, max_length=100)
    is_active: bool = True
    usage_limit: int | None = Field(None, ge=1)


class PromotionOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str | None = None
    type: str
    value: float
    valid_from: date | None = None
    valid_to: date | None = None
    min_purchase: float
    applies_to: str
    product_ids: list[str] | None = None
    promo_code: str | None = None
    is_active: bool
    usage_limit: int | None = None
    usage_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ValidateIn(BaseModel):
    code: str
    cart_total: float = 0


class ValidateOut(BaseModel):
    valid: bool
    promotion_id: str | None = None
    discount_amount: float = 0
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_out(p: Promotion) -> PromotionOut:
    return PromotionOut(
        id=str(p.id),
        tenant_id=str(p.tenant_id),
        name=p.name,
        description=p.description,
        type=p.type,
        value=float(p.value),
        valid_from=p.valid_from,
        valid_to=p.valid_to,
        min_purchase=float(p.min_purchase or 0),
        applies_to=p.applies_to,
        product_ids=[str(x) for x in p.product_ids] if p.product_ids else None,
        promo_code=p.promo_code,
        is_active=p.is_active,
        usage_limit=p.usage_limit,
        usage_count=p.usage_count or 0,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _compute_discount(promotion: Promotion, cart_total: float) -> float:
    if promotion.type == "percentage":
        return round(cart_total * float(promotion.value) / 100, 4)
    if promotion.type == "fixed":
        return min(float(promotion.value), cart_total)
    # bogo: descuento del 50% como simplificación
    return round(cart_total * 0.5, 4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[PromotionOut])
def list_promotions(
    request: Request,
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    q = db.query(Promotion).filter(Promotion.tenant_id == tenant_id)
    if is_active is not None:
        q = q.filter(Promotion.is_active == is_active)
    rows = q.order_by(Promotion.created_at.desc()).all()
    return [_to_out(p) for p in rows]


@router.post("", response_model=PromotionOut, status_code=201)
def create_promotion(
    request: Request,
    payload: PromotionIn,
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)

    if payload.promo_code:
        exists = (
            db.query(Promotion)
            .filter(
                Promotion.tenant_id == tenant_id,
                Promotion.promo_code == payload.promo_code.upper(),
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="promo_code_already_exists")

    pids = [UUID(x) for x in payload.product_ids] if payload.product_ids else None
    promo = Promotion(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        type=payload.type,
        value=payload.value,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        min_purchase=payload.min_purchase,
        applies_to=payload.applies_to,
        product_ids=pids,
        promo_code=payload.promo_code.upper() if payload.promo_code else None,
        is_active=payload.is_active,
        usage_limit=payload.usage_limit,
        usage_count=0,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return _to_out(promo)


@router.get("/{promotion_id}", response_model=PromotionOut)
def get_promotion(
    request: Request,
    promotion_id: str = Path(...),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    promo = (
        db.query(Promotion)
        .filter(Promotion.id == UUID(promotion_id), Promotion.tenant_id == tenant_id)
        .first()
    )
    if not promo:
        raise HTTPException(status_code=404, detail="promotion_not_found")
    return _to_out(promo)


@router.put("/{promotion_id}", response_model=PromotionOut)
def update_promotion(
    request: Request,
    payload: PromotionIn,
    promotion_id: str = Path(...),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    promo = (
        db.query(Promotion)
        .filter(Promotion.id == UUID(promotion_id), Promotion.tenant_id == tenant_id)
        .first()
    )
    if not promo:
        raise HTTPException(status_code=404, detail="promotion_not_found")

    if payload.promo_code:
        conflict = (
            db.query(Promotion)
            .filter(
                Promotion.tenant_id == tenant_id,
                Promotion.promo_code == payload.promo_code.upper(),
                Promotion.id != UUID(promotion_id),
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="promo_code_already_exists")

    promo.name = payload.name
    promo.description = payload.description
    promo.type = payload.type
    promo.value = payload.value
    promo.valid_from = payload.valid_from
    promo.valid_to = payload.valid_to
    promo.min_purchase = payload.min_purchase
    promo.applies_to = payload.applies_to
    promo.product_ids = [UUID(x) for x in payload.product_ids] if payload.product_ids else None
    promo.promo_code = payload.promo_code.upper() if payload.promo_code else None
    promo.is_active = payload.is_active
    promo.usage_limit = payload.usage_limit
    promo.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(promo)
    return _to_out(promo)


@router.delete("/{promotion_id}", status_code=204)
def delete_promotion(
    request: Request,
    promotion_id: str = Path(...),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    promo = (
        db.query(Promotion)
        .filter(Promotion.id == UUID(promotion_id), Promotion.tenant_id == tenant_id)
        .first()
    )
    if not promo:
        raise HTTPException(status_code=404, detail="promotion_not_found")
    db.delete(promo)
    db.commit()


@router.post("/validate", response_model=ValidateOut)
def validate_promo_code(
    request: Request,
    payload: ValidateIn,
    db: Session = Depends(get_db),
):
    """Valida un código promocional y calcula el descuento aplicable."""
    tenant_id = _tenant_id(request)
    today = date.today()

    promo = (
        db.query(Promotion)
        .filter(
            Promotion.tenant_id == tenant_id,
            Promotion.promo_code == payload.code.upper(),
            Promotion.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not promo:
        return ValidateOut(valid=False, discount_amount=0, message="code_not_found")

    if promo.valid_from and today < promo.valid_from:
        return ValidateOut(valid=False, discount_amount=0, message="code_not_yet_valid")

    if promo.valid_to and today > promo.valid_to:
        return ValidateOut(valid=False, discount_amount=0, message="code_expired")

    if promo.usage_limit and promo.usage_count >= promo.usage_limit:
        return ValidateOut(valid=False, discount_amount=0, message="usage_limit_reached")

    if payload.cart_total < float(promo.min_purchase or 0):
        return ValidateOut(valid=False, discount_amount=0, message="min_purchase_not_met")

    discount = _compute_discount(promo, payload.cart_total)
    return ValidateOut(
        valid=True,
        promotion_id=str(promo.id),
        discount_amount=discount,
        message="ok",
    )
