from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.products import Product


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)
protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]


class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    stock: float = Field(ge=0)
    unit: str = Field(min_length=1)
    product_metadata: Optional[dict] = None


class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    stock: float
    unit: str
    product_metadata: Optional[dict] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ProductOut])
def list_products(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(default=None, description="text search on name"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = select(Product)
    if q:
        like = f"%{q}%"
        query = query.where(Product.name.ilike(like))
    query = query.order_by(Product.id.asc()).limit(limit).offset(offset)
    rows = db.execute(query).scalars().all()
    return rows


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    obj = db.get(Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="product_not_found")
    return obj


@router.post("/", response_model=ProductOut, status_code=201, dependencies=protected)
def create_product(payload: ProductIn, request: Request, db: Session = Depends(get_db)):
    obj = Product(
        name=payload.name,
        price=payload.price,
        stock=payload.stock,
        unit=payload.unit,
        product_metadata=payload.product_metadata,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{product_id}", response_model=ProductOut, dependencies=protected)
def update_product(product_id: int, payload: ProductIn, db: Session = Depends(get_db)):
    obj = db.get(Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="product_not_found")
    obj.name = payload.name
    obj.price = payload.price
    obj.stock = payload.stock
    obj.unit = payload.unit
    obj.product_metadata = payload.product_metadata
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{product_id}", status_code=204, dependencies=protected)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    obj = db.get(Product, product_id)
    if not obj:
        return  # idempotent
    db.delete(obj)
    db.commit()
    return
