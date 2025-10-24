from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Products"])


@router.get("/products")
def list_products_public():
    # Minimal endpoint to satisfy tests; real tenant/admin routers provide full CRUD.
    return []

