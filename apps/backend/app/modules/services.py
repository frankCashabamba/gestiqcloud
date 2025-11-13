"""Module: services.py

Service layer helpers for module assignment to companies and users.
"""

import uuid

from app.db.rls import set_tenant_guc
from app.models.core.modulo import EmpresaModulo, ModuloAsignado
from app.modules import crud, schemas
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------- EMPRESA-MODULO ----------
def asignar_modulo_a_empresa_si_no_existe(
    db: Session,
    tenant_id: int,
    modulo_in: schemas.EmpresaModuloCreate,
):
    existente = (
        db.query(EmpresaModulo)
        .filter_by(
            tenant_id=tenant_id,
            modulo_id=modulo_in.modulo_id,
        )
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Este módulo ya fue asignado a esta empresa.",
        )

    return crud.asignar_modulo_a_empresa(db, tenant_id, modulo_in)


# ---------- USUARIO-MODULO ----------
def asignar_modulo_a_usuario_si_empresa_lo_tiene(
    db: Session,
    tenant_id: int,
    usuario_id: int,
    modulo_id: int,
):
    # Verifica que la empresa tenga contratado el módulo
    empresa_modulo = (
        db.query(EmpresaModulo)
        .filter_by(
            tenant_id=tenant_id,
            modulo_id=modulo_id,
            activo=True,
        )
        .first()
    )

    if not empresa_modulo:
        raise HTTPException(
            status_code=403,
            detail="La empresa no tiene contratado este módulo.",
        )

    # Verifica que el usuario aún no tenga el módulo asignado
    existente = (
        db.query(ModuloAsignado)
        .filter_by(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            modulo_id=modulo_id,
        )
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Este módulo ya está asignado al usuario.",
        )

    return crud.asignar_modulo_a_usuario(db, tenant_id, usuario_id, modulo_id)


def upsert_modulo_a_empresa(
    db: Session,
    tenant_id: str,
    modulo_in: schemas.EmpresaModuloCreate,
) -> schemas.EmpresaModuloOutAdmin:
    """Create/update module assignment for a tenant.

    Accepts modern tenant UUIDs. For backward compatibility, also accepts a slug
    and tries to resolve it. The historical integer mapping via tenants.tenant_id
    was removed in migrations, so do not rely on that column anymore.
    """
    tenant_uuid: str | None = None

    # 1) If it's a UUID, use it directly
    try:
        _ = uuid.UUID(str(tenant_id))
        tenant_uuid = str(tenant_id)
    except Exception:
        tenant_uuid = None

    # 2) If not a UUID, try resolve by slug
    if not tenant_uuid:
        row = db.execute(
            text("SELECT id::text FROM tenants WHERE slug = :slug"),
            {"slug": str(tenant_id)},
        ).first()
        if row and row[0]:
            tenant_uuid = row[0]

    if not tenant_uuid:
        raise HTTPException(status_code=400, detail="tenant_not_found")
    # Set GUC locally for this transaction to satisfy any trigger relying on it
    try:
        set_tenant_guc(db, str(tenant_uuid), persist=False)
    except Exception:
        pass
    existente = (
        db.query(EmpresaModulo)
        .filter_by(
            tenant_id=tenant_uuid,
            modulo_id=modulo_in.modulo_id,
        )
        .first()
    )

    if existente:
        existente.active = modulo_in.active  # type: ignore[assignment]
        existente.fecha_expiracion = modulo_in.fecha_expiracion  # type: ignore[assignment]
        existente.plantilla_inicial = modulo_in.plantilla_inicial  # type: ignore[assignment]
        db.commit()
        db.refresh(existente)
        asignacion = existente
    else:
        asignacion = EmpresaModulo(
            tenant_id=tenant_uuid,
            modulo_id=modulo_in.modulo_id,
            activo=modulo_in.active,
            fecha_expiracion=modulo_in.fecha_expiracion,
            plantilla_inicial=modulo_in.plantilla_inicial,
        )
        db.add(asignacion)
        db.commit()
        db.refresh(asignacion)

    # Asegura que las relaciones estén cargadas
    db.refresh(asignacion)
    _ = asignacion.tenant
    _ = asignacion.modulo

    # Coalesce de slug profesional: preferir slug, luego nombre, luego tenant_id
    empresa_slug = (
        getattr(asignacion.tenant, "slug", None)
        or getattr(asignacion.tenant, "nombre", None)
        or str(asignacion.tenant_id)
    )

    return schemas.EmpresaModuloOutAdmin(
        id=asignacion.id,  # type: ignore[arg-type]
        tenant_id=asignacion.tenant_id,  # type: ignore[arg-type]
        modulo_id=asignacion.modulo_id,  # type: ignore[arg-type]
        active=asignacion.active,  # type: ignore[arg-type]
        fecha_activacion=asignacion.fecha_activacion,  # type: ignore[arg-type]
        fecha_expiracion=asignacion.fecha_expiracion,  # type: ignore[arg-type]
        plantilla_inicial=asignacion.plantilla_inicial,  # type: ignore[arg-type]
        empresa_slug=empresa_slug,
        modulo=schemas.ModuloOut.from_orm(asignacion.modulo),
    )
