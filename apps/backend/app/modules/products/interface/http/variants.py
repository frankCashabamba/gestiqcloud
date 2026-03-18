"""Product Variants — CRUD endpoints for product attributes and variants."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
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
    prefix="/products/variants",
    tags=["Product Variants"],
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


class AttributeCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    values: list[str] = Field(default_factory=list)


class VariantCreateIn(BaseModel):
    sku: str | None = Field(default=None, max_length=50)
    attributes: dict[str, str] = Field(default_factory=dict)
    price_override: Decimal | None = None
    cost_override: Decimal | None = None
    barcode: str | None = Field(default=None, max_length=50)
    is_active: bool = True
    sort_order: int = 0


class VariantUpdateIn(BaseModel):
    sku: str | None = Field(default=None, max_length=50)
    attributes: dict[str, str] | None = None
    price_override: Decimal | None = None
    cost_override: Decimal | None = None
    barcode: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    sort_order: int | None = None


# --- Attribute Endpoints ---


@router.get("/attributes", response_model=list[dict[str, Any]])
def list_attributes(request: Request, db: Session = Depends(get_db)):
    """Lista todos los atributos de producto del tenant."""
    ensure_guc_from_request(request, db, persist=True)

    rows = db.execute(
        text(
            "SELECT id, name, values, is_active, created_at "
            "FROM product_attributes ORDER BY name ASC"
        )
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "name": r[1],
            "values": r[2],
            "is_active": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


@router.post("/attributes", response_model=dict[str, Any], status_code=201)
def create_attribute(payload: AttributeCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea un nuevo atributo de producto."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    existing = db.execute(
        text("SELECT id FROM product_attributes WHERE tenant_id = :tid AND name = :name").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": tenant_id, "name": payload.name},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="attribute_name_already_exists")

    row = db.execute(
        text(
            "INSERT INTO product_attributes(tenant_id, name, values) "
            "VALUES (:tid, :name, :vals::jsonb) "
            "RETURNING id, created_at"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {
            "tid": tenant_id,
            "name": payload.name,
            "vals": __import__("json").dumps(payload.values),
        },
    ).first()

    db.commit()

    return {
        "id": str(row[0]),
        "name": payload.name,
        "values": payload.values,
        "created_at": row[1].isoformat() if row[1] else None,
    }


# --- Variant Endpoints ---


@router.get("/{product_id}", response_model=list[dict[str, Any]])
def list_variants(product_id: str, request: Request, db: Session = Depends(get_db)):
    """Lista todas las variantes de un producto."""
    ensure_guc_from_request(request, db, persist=True)

    rows = db.execute(
        text(
            "SELECT id, sku, attributes, price_override, cost_override, barcode, "
            "is_active, sort_order, created_at, updated_at "
            "FROM product_variants WHERE product_id = :pid "
            "ORDER BY sort_order ASC, created_at ASC"
        ).bindparams(bindparam("pid", type_=PGUUID(as_uuid=True))),
        {"pid": product_id},
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "product_id": product_id,
            "sku": r[1],
            "attributes": r[2],
            "price_override": float(r[3]) if r[3] is not None else None,
            "cost_override": float(r[4]) if r[4] is not None else None,
            "barcode": r[5],
            "is_active": r[6],
            "sort_order": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
            "updated_at": r[9].isoformat() if r[9] else None,
        }
        for r in rows
    ]


@router.post("/{product_id}", response_model=dict[str, Any], status_code=201)
def create_variant(product_id: str, payload: VariantCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea una variante para un producto."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    product = db.execute(
        text("SELECT id FROM products WHERE id = :pid AND tenant_id = :tid").bindparams(
            bindparam("pid", type_=PGUUID(as_uuid=True)),
            bindparam("tid", type_=PGUUID(as_uuid=True)),
        ),
        {"pid": product_id, "tid": tenant_id},
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="product_not_found")

    import json

    row = db.execute(
        text(
            "INSERT INTO product_variants(tenant_id, product_id, sku, attributes, "
            "price_override, cost_override, barcode, is_active, sort_order) "
            "VALUES (:tid, :pid, :sku, :attrs::jsonb, :price_override, :cost_override, "
            ":barcode, :is_active, :sort_order) "
            "RETURNING id, created_at"
        ).bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True)),
            bindparam("pid", type_=PGUUID(as_uuid=True)),
        ),
        {
            "tid": tenant_id,
            "pid": product_id,
            "sku": payload.sku,
            "attrs": json.dumps(payload.attributes),
            "price_override": payload.price_override,
            "cost_override": payload.cost_override,
            "barcode": payload.barcode,
            "is_active": payload.is_active,
            "sort_order": payload.sort_order,
        },
    ).first()

    db.commit()

    return {
        "id": str(row[0]),
        "product_id": product_id,
        "sku": payload.sku,
        "attributes": payload.attributes,
        "created_at": row[1].isoformat() if row[1] else None,
    }


@router.put("/{variant_id}", response_model=dict[str, Any])
def update_variant(variant_id: str, payload: VariantUpdateIn, request: Request, db: Session = Depends(get_db)):
    """Actualiza una variante."""
    ensure_guc_from_request(request, db, persist=True)

    variant = db.execute(
        text("SELECT id FROM product_variants WHERE id = :vid").bindparams(
            bindparam("vid", type_=PGUUID(as_uuid=True))
        ),
        {"vid": variant_id},
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="variant_not_found")

    updates = []
    params: dict[str, Any] = {"vid": variant_id}

    if payload.sku is not None:
        updates.append("sku = :sku")
        params["sku"] = payload.sku
    if payload.attributes is not None:
        import json
        updates.append("attributes = :attrs::jsonb")
        params["attrs"] = json.dumps(payload.attributes)
    if payload.price_override is not None:
        updates.append("price_override = :price_override")
        params["price_override"] = payload.price_override
    if payload.cost_override is not None:
        updates.append("cost_override = :cost_override")
        params["cost_override"] = payload.cost_override
    if payload.barcode is not None:
        updates.append("barcode = :barcode")
        params["barcode"] = payload.barcode
    if payload.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = payload.is_active
    if payload.sort_order is not None:
        updates.append("sort_order = :sort_order")
        params["sort_order"] = payload.sort_order

    if not updates:
        raise HTTPException(status_code=400, detail="no_fields_to_update")

    updates.append("updated_at = NOW()")
    db.execute(
        text(f"UPDATE product_variants SET {', '.join(updates)} WHERE id = :vid").bindparams(
            bindparam("vid", type_=PGUUID(as_uuid=True))
        ),
        params,
    )
    db.commit()

    return {"id": variant_id, "status": "updated"}


@router.delete("/{variant_id}", response_model=dict[str, Any])
def delete_variant(variant_id: str, request: Request, db: Session = Depends(get_db)):
    """Elimina una variante."""
    ensure_guc_from_request(request, db, persist=True)

    variant = db.execute(
        text("SELECT id FROM product_variants WHERE id = :vid").bindparams(
            bindparam("vid", type_=PGUUID(as_uuid=True))
        ),
        {"vid": variant_id},
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="variant_not_found")

    db.execute(
        text("DELETE FROM product_variants WHERE id = :vid").bindparams(
            bindparam("vid", type_=PGUUID(as_uuid=True))
        ),
        {"vid": variant_id},
    )
    db.commit()

    return {"id": variant_id, "status": "deleted"}
