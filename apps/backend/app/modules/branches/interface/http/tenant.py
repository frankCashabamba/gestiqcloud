"""Branches — CRUD endpoints for tenant branch management."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/branches",
    tags=["Branches"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {}) or {}
    tid = claims.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id_not_found")
    return UUID(str(tid))


# --- Schemas ---


class BranchCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=20)
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    is_main: bool = False


class BranchUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    is_main: bool | None = None
    is_active: bool | None = None


# --- Response Schemas ---


class BranchListItemOut(BaseModel):
    """Item de la lista de sucursales del tenant."""

    id: str
    name: str
    code: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    is_main: bool
    is_active: bool
    created_at: str | None = None


class BranchWarehouseOut(BaseModel):
    id: str
    name: str
    code: str | None = None


class BranchRegisterOut(BaseModel):
    id: str
    name: str


class BranchDetailOut(BranchListItemOut):
    """Detalle de una sucursal, incluye warehouses y registers vinculados."""

    warehouses: list[BranchWarehouseOut] = []
    registers: list[BranchRegisterOut] = []


class BranchCreatedOut(BaseModel):
    """Respuesta tras crear una sucursal."""

    id: str
    name: str
    code: str
    is_main: bool
    created_at: str | None = None


class BranchUpdateStatusOut(BaseModel):
    """Respuesta tras actualizar una sucursal."""

    id: str
    status: str


# --- Endpoints ---


@router.get("", response_model=list[BranchListItemOut])
def list_branches(request: Request, db: Session = Depends(get_db)):
    """Lista todas las sucursales del tenant."""
    ensure_guc_from_request(request, db, persist=True)

    rows = db.execute(
        text(
            "SELECT id, name, code, address, city, phone, is_main, is_active, created_at "
            "FROM branches ORDER BY is_main DESC, name ASC"
        )
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "name": r[1],
            "code": r[2],
            "address": r[3],
            "city": r[4],
            "phone": r[5],
            "is_main": r[6],
            "is_active": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


@router.get("/{branch_id}", response_model=BranchDetailOut)
def get_branch(branch_id: str, request: Request, db: Session = Depends(get_db)):
    """Obtiene detalle de una sucursal con sus warehouses y registers vinculados."""
    ensure_guc_from_request(request, db, persist=True)

    branch = db.execute(
        text(
            "SELECT id, name, code, address, city, phone, is_main, is_active, created_at FROM branches WHERE id = :bid"
        ).bindparams(bindparam("bid", type_=PGUUID(as_uuid=True))),
        {"bid": branch_id},
    ).first()

    if not branch:
        raise HTTPException(status_code=404, detail="branch_not_found")

    warehouses = db.execute(
        text("SELECT id, name, code FROM warehouses WHERE branch_id = :bid").bindparams(
            bindparam("bid", type_=PGUUID(as_uuid=True))
        ),
        {"bid": branch_id},
    ).fetchall()

    registers = db.execute(
        text("SELECT id, name FROM pos_registers WHERE branch_id = :bid").bindparams(
            bindparam("bid", type_=PGUUID(as_uuid=True))
        ),
        {"bid": branch_id},
    ).fetchall()

    return {
        "id": str(branch[0]),
        "name": branch[1],
        "code": branch[2],
        "address": branch[3],
        "city": branch[4],
        "phone": branch[5],
        "is_main": branch[6],
        "is_active": branch[7],
        "created_at": branch[8].isoformat() if branch[8] else None,
        "warehouses": [{"id": str(w[0]), "name": w[1], "code": w[2]} for w in warehouses],
        "registers": [{"id": str(r[0]), "name": r[1]} for r in registers],
    }


@router.post("", response_model=BranchCreatedOut, status_code=201)
def create_branch(payload: BranchCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea una nueva sucursal."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    existing = db.execute(
        text("SELECT id FROM branches WHERE tenant_id = :tid AND code = :code").bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True))
        ),
        {"tid": tenant_id, "code": payload.code},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="branch_code_already_exists")

    if payload.is_main:
        db.execute(
            text("UPDATE branches SET is_main = false WHERE tenant_id = :tid").bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True))
            ),
            {"tid": tenant_id},
        )

    row = db.execute(
        text(
            "INSERT INTO branches(tenant_id, name, code, address, city, phone, is_main) "
            "VALUES (:tid, :name, :code, :address, :city, :phone, :is_main) "
            "RETURNING id, created_at"
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {
            "tid": tenant_id,
            "name": payload.name,
            "code": payload.code,
            "address": payload.address,
            "city": payload.city,
            "phone": payload.phone,
            "is_main": payload.is_main,
        },
    ).first()

    db.commit()

    return {
        "id": str(row[0]),
        "name": payload.name,
        "code": payload.code,
        "is_main": payload.is_main,
        "created_at": row[1].isoformat() if row[1] else None,
    }


@router.patch("/{branch_id}", response_model=BranchUpdateStatusOut)
def update_branch(
    branch_id: str, payload: BranchUpdateIn, request: Request, db: Session = Depends(get_db)
):
    """Actualiza una sucursal."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = _get_tenant_id(request)

    branch = db.execute(
        text("SELECT id FROM branches WHERE id = :bid").bindparams(
            bindparam("bid", type_=PGUUID(as_uuid=True))
        ),
        {"bid": branch_id},
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="branch_not_found")

    updates = []
    params: dict[str, Any] = {"bid": branch_id}

    if payload.name is not None:
        updates.append("name = :name")
        params["name"] = payload.name
    if payload.address is not None:
        updates.append("address = :address")
        params["address"] = payload.address
    if payload.city is not None:
        updates.append("city = :city")
        params["city"] = payload.city
    if payload.phone is not None:
        updates.append("phone = :phone")
        params["phone"] = payload.phone
    if payload.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = payload.is_active
    if payload.is_main is not None:
        if payload.is_main:
            db.execute(
                text("UPDATE branches SET is_main = false WHERE tenant_id = :tid").bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True))
                ),
                {"tid": tenant_id},
            )
        updates.append("is_main = :is_main")
        params["is_main"] = payload.is_main

    if not updates:
        raise HTTPException(status_code=400, detail="no_fields_to_update")

    updates.append("updated_at = NOW()")
    db.execute(
        text(f"UPDATE branches SET {', '.join(updates)} WHERE id = :bid").bindparams(
            bindparam("bid", type_=PGUUID(as_uuid=True))
        ),
        params,
    )
    db.commit()

    return {"id": branch_id, "status": "updated"}


@router.post("/{branch_id}/assign-warehouse/{warehouse_id}", response_model=dict)
def assign_warehouse(
    branch_id: str, warehouse_id: str, request: Request, db: Session = Depends(get_db)
):
    """Vincula un almacén a una sucursal."""
    ensure_guc_from_request(request, db, persist=True)

    db.execute(
        text("UPDATE warehouses SET branch_id = :bid WHERE id = :wid").bindparams(
            bindparam("bid", type_=PGUUID(as_uuid=True)),
            bindparam("wid", type_=PGUUID(as_uuid=True)),
        ),
        {"bid": branch_id, "wid": warehouse_id},
    )
    db.commit()
    return {"status": "assigned", "warehouse_id": warehouse_id, "branch_id": branch_id}


@router.post("/{branch_id}/assign-register/{register_id}", response_model=dict)
def assign_register(
    branch_id: str, register_id: str, request: Request, db: Session = Depends(get_db)
):
    """Vincula un registro POS a una sucursal."""
    ensure_guc_from_request(request, db, persist=True)

    db.execute(
        text("UPDATE pos_registers SET branch_id = :bid WHERE id = :rid").bindparams(
            bindparam("bid", type_=PGUUID(as_uuid=True)),
            bindparam("rid", type_=PGUUID(as_uuid=True)),
        ),
        {"bid": branch_id, "rid": register_id},
    )
    db.commit()
    return {"status": "assigned", "register_id": register_id, "branch_id": branch_id}
