from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from ...infrastructure.repositories import ProveedorRepo
from .schemas import ProveedorCreate, ProveedorOut, ProveedorUpdate

router = APIRouter(
    prefix="/tenant/proveedores",
    tags=["Proveedores"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


def _empresa_id(request: Request) -> int:
    claims = getattr(request.state, "access_claims", {})
    empresa = claims.get("tenant_id") or claims.get("empresa_id")
    if empresa is None:
        raise HTTPException(status_code=400, detail="Empresa no encontrada en el token")
    try:
        return int(empresa)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Identificador de empresa invalido")


def _user_id(request: Request) -> str | None:
    claims = getattr(request.state, "access_claims", {})
    return claims.get("user_id") or claims.get("sub")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prepare_payload(
    payload: ProveedorCreate | ProveedorUpdate,
    *,
    request: Request,
    current_iban: str | None = None,
) -> dict:
    data = payload.model_dump()
    confirm = data.pop("iban_confirmacion", None)
    iban = data.get("iban")

    if iban:
        if confirm is None or iban.strip() != confirm.strip():
            raise HTTPException(status_code=400, detail="La confirmacion de IBAN no coincide")
        if iban.strip() != (current_iban or "").strip():
            data["iban_actualizado_por"] = _user_id(request)
            data["iban_actualizado_at"] = _now()
    elif confirm:
        raise HTTPException(status_code=400, detail="Debes indicar el IBAN si aportas confirmacion")
    return data


@router.get("/", response_model=list[ProveedorOut])
def list_proveedores(request: Request, db: Session = Depends(get_db)):
    empresa_id = _empresa_id(request)
    return ProveedorRepo(db).list(empresa_id)


@router.get("/{pid}", response_model=ProveedorOut)
def get_proveedor(pid: int, request: Request, db: Session = Depends(get_db)):
    empresa_id = _empresa_id(request)
    obj = ProveedorRepo(db).get(empresa_id, pid)
    if not obj:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return obj


@router.post("/", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def create_proveedor(
    payload: ProveedorCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = _empresa_id(request)
    repo = ProveedorRepo(db)
    data = _prepare_payload(payload, request=request)
    if data.get("iban"):
        data.setdefault("iban_actualizado_por", _user_id(request))
        data.setdefault("iban_actualizado_at", _now())
    proveedor = repo.create(empresa_id, **data)
    return proveedor


@router.put("/{pid}", response_model=ProveedorOut)
def update_proveedor(
    pid: int,
    payload: ProveedorUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    empresa_id = _empresa_id(request)
    repo = ProveedorRepo(db)
    existing = repo.get(empresa_id, pid)
    if not existing:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    data = _prepare_payload(payload, request=request, current_iban=existing.iban)
    proveedor = repo.update(empresa_id, pid, **data)
    return proveedor


@router.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proveedor(pid: int, request: Request, db: Session = Depends(get_db)):
    empresa_id = _empresa_id(request)
    try:
        ProveedorRepo(db).delete(empresa_id, pid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
