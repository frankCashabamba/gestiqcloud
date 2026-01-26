from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

from ...infrastructure.repositories import SupplierRepo
from .schemas import SupplierCreate, SupplierOut, SupplierUpdate

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {})
    tenant = claims.get("tenant_id") or claims.get("tenant_id")
    if tenant is None:
        raise HTTPException(status_code=400, detail="Tenant not found in token")
    try:
        return UUID(str(tenant))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid tenant identifier")


def _supplier_id(value: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid supplier identifier")


def _user_id(request: Request) -> str | None:
    claims = getattr(request.state, "access_claims", {})
    return claims.get("user_id") or claims.get("sub")


def _now() -> datetime:
    return datetime.now(UTC)


def _prepare_payload(
    payload: SupplierCreate | SupplierUpdate,
    *,
    request: Request,
    current_iban: str | None = None,
) -> dict:
    data = payload.model_dump()
    confirm = data.pop("iban_confirmation", None)
    iban = data.get("iban")

    if iban:
        if confirm is None or iban.strip() != confirm.strip():
            raise HTTPException(status_code=400, detail="IBAN confirmation does not match")
        if iban.strip() != (current_iban or "").strip():
            data["iban_updated_by"] = _user_id(request)
            data["iban_updated_at"] = _now()
    elif confirm:
        raise HTTPException(
            status_code=400, detail="IBAN must be provided if confirmation is given"
        )
    return data


@router.get("", response_model=list[SupplierOut])
def list_suppliers(request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id(request)
    return SupplierRepo(db).list(tenant_id)


@router.get("/{pid}", response_model=SupplierOut)
def get_supplier(pid: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id(request)
    obj = SupplierRepo(db).get(tenant_id, _supplier_id(pid))
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return obj


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    repo = SupplierRepo(db)
    data = _prepare_payload(payload, request=request)
    if data.get("iban"):
        data.setdefault("iban_updated_by", _user_id(request))
        data.setdefault("iban_updated_at", _now())
    supplier = repo.create(tenant_id, **data)
    return supplier


@router.put("/{pid}", response_model=SupplierOut)
def update_supplier(
    pid: str,
    payload: SupplierUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    repo = SupplierRepo(db)
    existing = repo.get(tenant_id, _supplier_id(pid))
    if not existing:
        raise HTTPException(status_code=404, detail="Supplier not found")
    data = _prepare_payload(payload, request=request, current_iban=existing.iban)
    supplier = repo.update(tenant_id, _supplier_id(pid), **data)
    return supplier


@router.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(pid: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id(request)
    try:
        SupplierRepo(db).delete(tenant_id, _supplier_id(pid))
    except ValueError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
