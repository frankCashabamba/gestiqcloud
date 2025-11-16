from __future__ import annotations

from app.config.database import get_db
from app.modules.productos.interface.http.tenant import (
    CategoryOut,
    ProductOut,
    get_categories_for_request,
    list_products,
    protected,
)
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "/product-categories",
    response_model=list[CategoryOut],
    dependencies=protected,
)
def list_product_categories(request: Request, db: Session = Depends(get_db)):
    return get_categories_for_request(request, db)


# ============================================================================
# Public products listing (GET /api/v1/products without /tenant prefix)
# ============================================================================
@router.get("", response_model=list[ProductOut])
@router.get("/", response_model=list[ProductOut])
def public_list_products(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="text search on name"),
    categoria: str | None = Query(default=None, description="filter by category"),
    activo: bool | None = Query(default=None, description="filter by active status"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Public endpoint for listing products (no auth required)"""
    return list_products(
        request=request,
        db=db,
        q=q,
        categoria=categoria,
        activo=activo,
        limit=limit,
        offset=offset,
        _tid="",  # Will be extracted from request
    )
