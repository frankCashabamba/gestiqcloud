from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls, tenant_id_from_request

router = APIRouter(
    prefix="/export",
    tags=["Export"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _csv(rows, header):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow([r.get(h) for h in header])
    return buf.getvalue().encode("utf-8")


@router.get("/products.csv", response_class=Response)
def export_products(request: Request, db: Session = Depends(get_db)):
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    rows = db.execute(
        text(
            "SELECT id, COALESCE(sku,'') AS sku, name, price, unit "
            "FROM products WHERE tenant_id=:tid ORDER BY id"
        ),
        {"tid": tenant_id},
    )
    items = [dict(r) for r in rows.mappings().all()]
    data = _csv(items, ["id", "sku", "name", "price", "unit"])
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.get("/clients.csv", response_class=Response)
def export_clients(request: Request, db: Session = Depends(get_db)):
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    rows = db.execute(
        text(
            "SELECT id, nombre, COALESCE(email,'') AS email, "
            "COALESCE(telefono,'') AS telefono FROM clients "
            "WHERE tenant_id=:tid ORDER BY id"
        ),
        {"tid": tenant_id},
    )
    items = [dict(r) for r in rows.mappings().all()]
    data = _csv(items, ["id", "nombre", "email", "telefono"])
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clients.csv"},
    )


@router.get("/stock.csv", response_class=Response)
def export_stock(request: Request, db: Session = Depends(get_db)):
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    rows = db.execute(
        text(
            "SELECT warehouse_id, product_id, qty FROM stock_items "
            "WHERE tenant_id=:tid ORDER BY warehouse_id, product_id"
        ),
        {"tid": tenant_id},
    )
    items = [dict(r) for r in rows.mappings().all()]
    data = _csv(items, ["warehouse_id", "product_id", "qty"])
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock.csv"},
    )
