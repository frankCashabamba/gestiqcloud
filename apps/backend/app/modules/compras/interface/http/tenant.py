from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...infrastructure.repositories import CompraRepo
from .schemas import CompraCreate, CompraOut, CompraUpdate

router = APIRouter(
    prefix="/compras",
    tags=["Compras"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[CompraOut])
def list_compras(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = claims["tenant_id"]
    return CompraRepo(db).list(tenant_id)


@router.get("/{cid}", response_model=CompraOut)
def get_compra(cid: int, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = claims["tenant_id"]
    obj = CompraRepo(db).get(tenant_id, cid)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.post("", response_model=CompraOut)
def create_compra(
    payload: CompraCreate, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    return CompraRepo(db).create(tenant_id, **payload.model_dump())


@router.put("/{cid}", response_model=CompraOut)
def update_compra(
    cid: int,
    payload: CompraUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    try:
        return CompraRepo(db).update(tenant_id, cid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "No encontrado")


@router.delete("/{cid}")
def delete_compra(
    cid: int, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        CompraRepo(db).delete(tenant_id, cid)
    except ValueError:
        raise HTTPException(404, "No encontrado")
    return {"success": True}
