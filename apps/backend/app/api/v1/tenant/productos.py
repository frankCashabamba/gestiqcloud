from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

router = APIRouter(prefix="/tenant/productos", tags=["productos-compat"])


def _redir(target_path: str, request: Request) -> RedirectResponse:
    qs = request.url.query
    url = target_path if not qs else f"{target_path}?{qs}"
    # 307 preserves method (GET stays GET) and respects body for non-GET
    return RedirectResponse(url=url, status_code=307)


@router.get("")
@router.get("/")
def productos_list(request: Request):
    return _redir("/api/v1/tenant/products", request)


@router.get("/search")
def productos_search(request: Request):
    return _redir("/api/v1/tenant/products/search", request)


@router.get("/by_code/{code}")
def productos_by_code(code: str, request: Request):
    return _redir(f"/api/v1/tenant/products/by_code/{code}", request)


@router.get("/{product_id}")
def productos_get(product_id: str, request: Request):
    return _redir(f"/api/v1/tenant/products/{product_id}", request)


@router.post("")
@router.post("/")
def productos_create(request: Request):
    return _redir("/api/v1/tenant/products", request)


@router.put("/{product_id}")
def productos_update(product_id: str, request: Request):
    return _redir(f"/api/v1/tenant/products/{product_id}", request)


@router.delete("/{product_id}")
def productos_delete(product_id: str, request: Request):
    return _redir(f"/api/v1/tenant/products/{product_id}", request)
