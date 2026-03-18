"""
Endpoints para variantes de producto (talla, color, etc.)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

router = APIRouter(
    prefix="/products/variants",
    tags=["Product Variants"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# Schemas
# ============================================================================


class AttributeIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    values: list[str] = Field(default_factory=list)


class VariantIn(BaseModel):
    product_id: UUID
    sku: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    price: float | None = None
    cost: float | None = None
    barcode: str | None = None
    is_active: bool = True


class VariantUpdate(BaseModel):
    sku: str | None = None
    attributes: dict[str, str] | None = None
    price: float | None = None
    cost: float | None = None
    barcode: str | None = None
    is_active: bool | None = None


# ============================================================================
# Attributes CRUD
# ============================================================================


@router.get("/attributes")
def list_attributes(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> list[dict[str, Any]]:
    tid = claims["tenant_id"]
    rows = db.execute(
        text(
            "SELECT id, name, values, is_active, created_at "
            "FROM product_variant_attributes "
            "WHERE tenant_id = :tid AND is_active = true ORDER BY name"
        ),
        {"tid": str(tid)},
    ).fetchall()
    return [
        {"id": str(r[0]), "name": r[1], "values": r[2], "is_active": r[3], "created_at": str(r[4])}
        for r in rows
    ]


@router.post("/attributes", status_code=201)
def create_attribute(
    payload: AttributeIn,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict[str, Any]:
    tid = claims["tenant_id"]
    import json as _json

    row = db.execute(
        text(
            "INSERT INTO product_variant_attributes (tenant_id, name, values) "
            "VALUES (:tid, :name, :vals::jsonb) "
            "ON CONFLICT (tenant_id, name) DO UPDATE SET values = EXCLUDED.values, updated_at = now() "
            "RETURNING id, name, values, is_active"
        ),
        {"tid": str(tid), "name": payload.name, "vals": _json.dumps(payload.values)},
    ).first()
    db.commit()
    return {"id": str(row[0]), "name": row[1], "values": row[2], "is_active": row[3]}


@router.delete("/attributes/{attr_id}")
def delete_attribute(
    attr_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict:
    tid = claims["tenant_id"]
    db.execute(
        text(
            "UPDATE product_variant_attributes SET is_active = false "
            "WHERE id = :aid AND tenant_id = :tid"
        ),
        {"aid": str(attr_id), "tid": str(tid)},
    )
    db.commit()
    return {"ok": True}


# ============================================================================
# Variants CRUD
# ============================================================================


@router.get("/{product_id}")
def list_variants(
    product_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> list[dict[str, Any]]:
    tid = claims["tenant_id"]
    rows = db.execute(
        text(
            "SELECT id, product_id, sku, attributes, price, cost, barcode, is_active, created_at "
            "FROM product_variants "
            "WHERE tenant_id = :tid AND product_id = :pid "
            "ORDER BY created_at"
        ),
        {"tid": str(tid), "pid": str(product_id)},
    ).fetchall()
    return [
        {
            "id": str(r[0]),
            "product_id": str(r[1]),
            "sku": r[2],
            "attributes": r[3],
            "price": float(r[4]) if r[4] is not None else None,
            "cost": float(r[5]) if r[5] is not None else None,
            "barcode": r[6],
            "is_active": r[7],
            "created_at": str(r[8]),
        }
        for r in rows
    ]


@router.post("", status_code=201)
def create_variant(
    payload: VariantIn,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict[str, Any]:
    import json as _json

    tid = claims["tenant_id"]
    row = db.execute(
        text(
            "INSERT INTO product_variants "
            "(tenant_id, product_id, sku, attributes, price, cost, barcode, is_active) "
            "VALUES (:tid, :pid, :sku, :attrs::jsonb, :price, :cost, :barcode, :active) "
            "RETURNING id, product_id, sku, attributes, price, cost, barcode, is_active"
        ),
        {
            "tid": str(tid),
            "pid": str(payload.product_id),
            "sku": payload.sku,
            "attrs": _json.dumps(payload.attributes),
            "price": payload.price,
            "cost": payload.cost,
            "barcode": payload.barcode,
            "active": payload.is_active,
        },
    ).first()
    db.commit()
    return {
        "id": str(row[0]),
        "product_id": str(row[1]),
        "sku": row[2],
        "attributes": row[3],
        "price": float(row[4]) if row[4] is not None else None,
        "cost": float(row[5]) if row[5] is not None else None,
        "barcode": row[6],
        "is_active": row[7],
    }


@router.put("/{variant_id}")
def update_variant(
    variant_id: UUID,
    payload: VariantUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict[str, Any]:
    import json as _json

    tid = claims["tenant_id"]
    fields: list[str] = []
    params: dict[str, Any] = {"vid": str(variant_id), "tid": str(tid)}
    if payload.sku is not None:
        fields.append("sku = :sku")
        params["sku"] = payload.sku
    if payload.attributes is not None:
        fields.append("attributes = :attrs::jsonb")
        params["attrs"] = _json.dumps(payload.attributes)
    if payload.price is not None:
        fields.append("price = :price")
        params["price"] = payload.price
    if payload.cost is not None:
        fields.append("cost = :cost")
        params["cost"] = payload.cost
    if payload.barcode is not None:
        fields.append("barcode = :barcode")
        params["barcode"] = payload.barcode
    if payload.is_active is not None:
        fields.append("is_active = :active")
        params["active"] = payload.is_active
    if not fields:
        raise HTTPException(status_code=400, detail="no_fields_to_update")
    fields.append("updated_at = now()")
    row = db.execute(
        text(
            f"UPDATE product_variants SET {', '.join(fields)} "
            "WHERE id = :vid AND tenant_id = :tid "
            "RETURNING id, sku, attributes, price, cost, barcode, is_active"
        ),
        params,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="variant_not_found")
    db.commit()
    return {
        "id": str(row[0]),
        "sku": row[1],
        "attributes": row[2],
        "price": float(row[3]) if row[3] is not None else None,
        "cost": float(row[4]) if row[4] is not None else None,
        "barcode": row[5],
        "is_active": row[6],
    }


@router.delete("/{variant_id}")
def delete_variant(
    variant_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict:
    tid = claims["tenant_id"]
    db.execute(
        text("DELETE FROM product_variants WHERE id = :vid AND tenant_id = :tid"),
        {"vid": str(variant_id), "tid": str(tid)},
    )
    db.commit()
    return {"ok": True}
