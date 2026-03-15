"""POS — Router de cajas/terminales (registers)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls

from ._deps import RegisterIn, get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS — Registers"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


@router.get(
    "/registers",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.register.read"))],
)
def list_registers(request: Request, db: Session = Depends(get_db)):
    """Lista todos los registros POS del tenant actual."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = get_tenant_id(request)

    try:
        rows = db.execute(
            text(
                "SELECT id, name, store_id, active, created_at "
                "FROM pos_registers "
                "WHERE tenant_id = :tid "
                "ORDER BY created_at DESC"
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": tenant_id},
        ).fetchall()

        return [
            {
                "id": str(r[0]),
                "name": r[1],
                "store_id": str(r[2]) if r[2] else None,
                "active": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar registros: {str(e)}")


@router.post(
    "/registers",
    response_model=dict,
    status_code=201,
    dependencies=[Depends(require_permission("pos.register.manage"))],
)
def create_register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    """Crea un nuevo registro POS."""
    ensure_guc_from_request(request, db, persist=True)
    tid = get_tenant_id(request)

    try:
        row = db.execute(
            text(
                "INSERT INTO pos_registers(tenant_id, name, active) "
                "VALUES (:tid, :name, TRUE) RETURNING id"
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": tid, "name": payload.name},
        ).first()

        db.commit()
        return {"id": str(row[0])}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear registro: {str(e)}")
