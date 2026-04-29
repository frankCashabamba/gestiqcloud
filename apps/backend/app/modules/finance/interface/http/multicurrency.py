"""Multi-Currency — exchange rates and currency conversion endpoints."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/finance/currencies",
    tags=["Multi-Currency"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {}) or {}
    tid = claims.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id_not_found")
    return UUID(str(tid))


# --- Schemas ---


class ExchangeRateIn(BaseModel):
    from_currency: str = Field(min_length=3, max_length=3)
    to_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0)
    source: str = Field(default="manual", max_length=50)


# --- Endpoints ---


@router.get("", response_model=list[dict[str, Any]])
def list_currencies(request: Request, db: Session = Depends(get_db)):
    """Lista todas las monedas disponibles."""
    ensure_guc_from_request(request, db, persist=True)

    rows = db.execute(
        text(
            "SELECT id, code, name, symbol, decimal_places, is_active "
            "FROM currencies WHERE is_active = true ORDER BY code ASC"
        )
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "code": r[1],
            "name": r[2],
            "symbol": r[3],
            "decimal_places": int(r[4]) if r[4] is not None else 2,
            "is_active": r[5],
        }
        for r in rows
    ]


@router.get("/rates", response_model=list[dict[str, Any]])
def list_exchange_rates(request: Request, db: Session = Depends(get_db)):
    """Lista los tipos de cambio del tenant."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    rows = db.execute(
        text(
            "SELECT id, from_currency, to_currency, rate, effective_date, source, created_at "
            "FROM exchange_rates WHERE tenant_id = :tid "
            "ORDER BY effective_date DESC, from_currency ASC"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id},
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "from_currency": r[1],
            "to_currency": r[2],
            "rate": float(r[3]),
            "effective_date": r[4].isoformat() if r[4] else None,
            "source": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


@router.post("/rates", response_model=dict[str, Any], status_code=201)
def create_exchange_rate(payload: ExchangeRateIn, request: Request, db: Session = Depends(get_db)):
    """Crea o actualiza un tipo de cambio."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    if payload.from_currency == payload.to_currency:
        raise HTTPException(status_code=400, detail="same_currency_pair")

    row = db.execute(
        text(
            "INSERT INTO exchange_rates(tenant_id, from_currency, to_currency, rate, source) "
            "VALUES (:tid, :from_c, :to_c, :rate, :source) "
            "RETURNING id, effective_date, created_at"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {
            "tid": tenant_id,
            "from_c": payload.from_currency,
            "to_c": payload.to_currency,
            "rate": payload.rate,
            "source": payload.source,
        },
    ).first()

    db.commit()

    return {
        "id": str(row[0]),
        "from_currency": payload.from_currency,
        "to_currency": payload.to_currency,
        "rate": float(payload.rate),
        "effective_date": row[1].isoformat() if row[1] else None,
        "created_at": row[2].isoformat() if row[2] else None,
    }


@router.get("/convert", response_model=dict[str, Any])
def convert_amount(
    request: Request,
    amount: Decimal = Query(..., gt=0),
    from_code: str = Query(..., min_length=3, max_length=3),
    to_code: str = Query(..., min_length=3, max_length=3),
    db: Session = Depends(get_db),
):
    """Convierte un monto entre monedas usando el tipo de cambio más reciente."""
    ensure_guc_from_request(request, db, persist=True)

    tenant_id = _get_tenant_id(request)

    if from_code == to_code:
        return {
            "amount": float(amount),
            "from_currency": from_code,
            "to_currency": to_code,
            "rate": 1.0,
            "converted_amount": float(amount),
        }

    rate_row = db.execute(
        text(
            "SELECT rate FROM exchange_rates "
            "WHERE tenant_id = :tid AND from_currency = :from_c AND to_currency = :to_c "
            "ORDER BY effective_date DESC LIMIT 1"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id, "from_c": from_code, "to_c": to_code},
    ).first()

    if not rate_row:
        reverse_row = db.execute(
            text(
                "SELECT rate FROM exchange_rates "
                "WHERE tenant_id = :tid AND from_currency = :to_c AND to_currency = :from_c "
                "ORDER BY effective_date DESC LIMIT 1"
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": tenant_id, "from_c": from_code, "to_c": to_code},
        ).first()
        if not reverse_row:
            raise HTTPException(status_code=404, detail="exchange_rate_not_found")
        rate = Decimal(1) / Decimal(str(reverse_row[0]))
    else:
        rate = Decimal(str(rate_row[0]))

    converted = amount * rate

    return {
        "amount": float(amount),
        "from_currency": from_code,
        "to_currency": to_code,
        "rate": float(rate),
        "converted_amount": float(converted.quantize(Decimal("0.01"))),
    }
