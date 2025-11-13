from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from ...infrastructure.repositories import GastoRepo
from .schemas import GastoCreate, GastoUpdate, GastoOut

router = APIRouter(
    prefix="/gastos",
    tags=["Gastos"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[GastoOut])
def list_gastos(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    return GastoRepo(db).list(tenant_id)


@router.get("/{gid}", response_model=GastoOut)
def get_gasto(
    gid: int,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    obj = GastoRepo(db).get(tenant_id, gid)
    if not obj:
        raise HTTPException(404, "No encontrado")
    return obj


@router.post("", response_model=GastoOut)
def create_gasto(
    payload: GastoCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    return GastoRepo(db).create(tenant_id, **payload.model_dump())


@router.put("/{gid}", response_model=GastoOut)
def update_gasto(
    gid: int,
    payload: GastoUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        return GastoRepo(db).update(tenant_id, gid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "No encontrado")


@router.delete("/{gid}")
def delete_gasto(
    gid: int,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        GastoRepo(db).delete(tenant_id, gid)
    except ValueError:
        raise HTTPException(404, "No encontrado")
    return {"success": True}
