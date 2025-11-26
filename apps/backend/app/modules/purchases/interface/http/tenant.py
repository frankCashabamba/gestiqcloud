from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...infrastructure.repositories import PurchaseRepo
from .schemas import PurchaseCreate, PurchaseOut, PurchaseUpdate

router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[PurchaseOut])
def list_purchases(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = claims["tenant_id"]
    return PurchaseRepo(db).list(tenant_id)


@router.get("/{cid}", response_model=PurchaseOut)
def get_purchase(
    cid: int, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    obj = PurchaseRepo(db).get(tenant_id, cid)
    if not obj:
        raise HTTPException(404, "Not found")
    return obj


@router.post("", response_model=PurchaseOut)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    return PurchaseRepo(db).create(tenant_id, **payload.model_dump())


@router.put("/{cid}", response_model=PurchaseOut)
def update_purchase(
    cid: int,
    payload: PurchaseUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    try:
        return PurchaseRepo(db).update(tenant_id, cid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "Not found")


@router.delete("/{cid}")
def delete_purchase(
    cid: int, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        PurchaseRepo(db).delete(tenant_id, cid)
    except ValueError:
        raise HTTPException(404, "Not found")
    return {"success": True}
