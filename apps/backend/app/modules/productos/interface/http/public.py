from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.modules.productos.interface.http.tenant import (
    CategoryOut,
    get_categories_for_request,
    protected,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "/product-categories",
    response_model=List[CategoryOut],
    dependencies=protected,
)
def list_product_categories(request: Request, db: Session = Depends(get_db)):
    return get_categories_for_request(request, db)
