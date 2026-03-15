"""POS — Router de numeración de documentos (contadores y series)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_rls

from ._deps import (
    DocSeriesOut,
    DocSeriesUpsertIn,
    NumberingCounterOut,
    NumberingCounterUpdateIn,
    get_tenant_id,
    validate_uuid,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS — Numbering"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


@router.get(
    "/numbering/counters",
    response_model=list[NumberingCounterOut],
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def list_numbering_counters(
    request: Request,
    doc_type: str | None = None,
    year: int | None = Query(default=None, ge=2000),
    series: str | None = None,
    db: Session = Depends(get_db),
):
    """Lista contadores de numeración por tenant."""
    tenant_id = get_tenant_id(request)
    sql_parts = [
        "SELECT doc_type, year, series, current_no, updated_at",
        "FROM doc_number_counters",
        "WHERE tenant_id = :tenant_id",
    ]
    params: dict[str, object] = {"tenant_id": tenant_id}

    if doc_type:
        sql_parts.append("AND doc_type = :doc_type")
        params["doc_type"] = doc_type.strip()
    if year is not None:
        sql_parts.append("AND year = :year")
        params["year"] = year
    if series:
        sql_parts.append("AND series = :series")
        params["series"] = series.strip() or "A"

    sql_parts.append("ORDER BY year DESC, doc_type, series")

    rows = db.execute(text(" ".join(sql_parts)), params).mappings().all()
    return [NumberingCounterOut.model_validate(dict(row)) for row in rows]


@router.put(
    "/numbering/counters",
    response_model=NumberingCounterOut,
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def upsert_numbering_counter(
    payload: NumberingCounterUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea o actualiza el contador de numeración para un tenant."""
    tenant_id = get_tenant_id(request)
    doc_type = payload.doc_type.strip()
    series = (payload.series or "").strip() or "A"

    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type requerido")

    row = (
        db.execute(
            text(
                """
            INSERT INTO doc_number_counters (
                tenant_id, doc_type, year, series, current_no, created_at, updated_at
            )
            VALUES (:tenant_id, :doc_type, :year, :series, :current_no, now(), now())
            ON CONFLICT (tenant_id, doc_type, year, series)
            DO UPDATE SET
                current_no = EXCLUDED.current_no,
                updated_at = now()
            RETURNING doc_type, year, series, current_no, updated_at
            """
            ),
            {
                "tenant_id": tenant_id,
                "doc_type": doc_type,
                "year": payload.year,
                "series": series,
                "current_no": payload.current_no,
            },
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(status_code=500, detail="No se pudo actualizar el contador")

    db.commit()
    return NumberingCounterOut.model_validate(dict(row))


@router.get(
    "/numbering/series",
    response_model=list[DocSeriesOut],
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def list_doc_series(
    request: Request,
    register_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Lista series de numeración para el tenant."""
    tenant_id = get_tenant_id(request)
    params: dict[str, object] = {"tenant_id": tenant_id}
    sql_parts = [
        "SELECT id, register_id, doc_type, name, current_no, reset_policy, active, created_at",
        "FROM doc_series",
        "WHERE tenant_id = :tenant_id",
    ]
    if register_id:
        rid = validate_uuid(register_id, "Register ID")
        sql_parts.append("AND register_id = :register_id")
        params["register_id"] = rid
    sql_parts.append("ORDER BY doc_type, name")

    rows = db.execute(text(" ".join(sql_parts)), params).mappings().all()
    return [
        DocSeriesOut(
            id=str(r["id"]),
            register_id=str(r["register_id"]) if r["register_id"] else None,
            doc_type=r["doc_type"],
            name=r["name"],
            current_no=r["current_no"],
            reset_policy=r["reset_policy"],
            active=bool(r["active"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.put(
    "/numbering/series",
    response_model=DocSeriesOut,
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def upsert_doc_series(
    payload: DocSeriesUpsertIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea o actualiza una serie de numeración."""
    tenant_id = get_tenant_id(request)
    reg_id = payload.register_id
    params = {
        "tenant_id": tenant_id,
        "register_id": reg_id,
        "doc_type": payload.doc_type.strip(),
        "name": payload.name.strip(),
    }

    if payload.id:
        row = (
            db.execute(
                text(
                    """
                UPDATE doc_series
                SET current_no = :current_no,
                    reset_policy = :reset_policy,
                    active = :active
                WHERE id = CAST(:id AS uuid)
                  AND tenant_id = :tenant_id
                RETURNING id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                """
                ),
                {
                    "id": payload.id,
                    "tenant_id": tenant_id,
                    "current_no": payload.current_no,
                    "reset_policy": payload.reset_policy,
                    "active": payload.active,
                },
            )
            .mappings()
            .first()
        )
    else:
        existing = db.execute(
            text(
                """
                SELECT id FROM doc_series
                WHERE tenant_id = :tenant_id
                  AND doc_type = :doc_type
                  AND name = :name
                  AND (register_id IS NOT DISTINCT FROM CAST(:register_id AS uuid))
                LIMIT 1
                """
            ),
            params,
        ).scalar()

        if existing:
            row = (
                db.execute(
                    text(
                        """
                    UPDATE doc_series
                    SET current_no = :current_no,
                        reset_policy = :reset_policy,
                        active = :active
                    WHERE id = CAST(:id AS uuid)
                    RETURNING id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                    """
                    ),
                    {
                        "id": existing,
                        "current_no": payload.current_no,
                        "reset_policy": payload.reset_policy,
                        "active": payload.active,
                    },
                )
                .mappings()
                .first()
            )
        else:
            row = (
                db.execute(
                    text(
                        """
                    INSERT INTO doc_series (
                        id, tenant_id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                    )
                    VALUES (
                        gen_random_uuid(), :tenant_id, CAST(:register_id AS uuid),
                        :doc_type, :name, :current_no, :reset_policy, :active, now()
                    )
                    RETURNING id, register_id, doc_type, name, current_no, reset_policy, active, created_at
                    """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "register_id": reg_id,
                        "doc_type": payload.doc_type.strip(),
                        "name": payload.name.strip(),
                        "current_no": payload.current_no,
                        "reset_policy": payload.reset_policy,
                        "active": payload.active,
                    },
                )
                .mappings()
                .first()
            )

    if not row:
        raise HTTPException(status_code=500, detail="No se pudo actualizar la serie")

    db.commit()
    return DocSeriesOut(
        id=str(row["id"]),
        register_id=str(row["register_id"]) if row["register_id"] else None,
        doc_type=row["doc_type"],
        name=row["name"],
        current_no=row["current_no"],
        reset_policy=row["reset_policy"],
        active=bool(row["active"]),
        created_at=row["created_at"],
    )


@router.post(
    "/numbering/series/reset_yearly",
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def reset_yearly_series(
    request: Request,
    db: Session = Depends(get_db),
):
    """Resetea a 0 las series con reset_policy=yearly."""
    tenant_id = get_tenant_id(request)
    result = db.execute(
        text(
            """
            UPDATE doc_series
            SET current_no = 0
            WHERE tenant_id = :tenant_id
              AND reset_policy = 'yearly'
            """
        ),
        {"tenant_id": tenant_id},
    )
    db.commit()
    return {"updated": result.rowcount}
