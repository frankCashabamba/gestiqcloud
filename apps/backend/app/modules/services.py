"""Module: services.py

Service layer helpers for module assignment to companies and users.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_guc
from app.models.core.modulo import AssignedModule, CompanyModule
from app.modules import crud, schemas


# ---------- EMPRESA-MODULO ----------
def asignar_modulo_a_empresa_si_no_existe(
    db: Session,
    tenant_id: int,
    modulo_in: schemas.EmpresaModuloCreate,
):
    existente = (
        db.query(CompanyModule)
        .filter_by(
            tenant_id=tenant_id,
            module_id=modulo_in.module_id,
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
        db.query(CompanyModule)
        .filter_by(
            tenant_id=tenant_id,
            module_id=modulo_id,
            active=True,
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
        db.query(AssignedModule)
        .filter_by(
            tenant_id=tenant_id,
            user_id=usuario_id,
            module_id=modulo_id,
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
        db.query(CompanyModule)
        .filter_by(
            tenant_id=tenant_uuid,
            module_id=modulo_in.module_id,
        )
        .first()
    )

    if existente:
        existente.active = modulo_in.active  # type: ignore[assignment]
        existente.expiration_date = modulo_in.expiration_date  # type: ignore[assignment]
        existente.initial_template = modulo_in.initial_template  # type: ignore[assignment]
        db.commit()
        db.refresh(existente)
        asignacion = existente
    else:
        asignacion = CompanyModule(
            tenant_id=tenant_uuid,
            module_id=modulo_in.module_id,
            active=modulo_in.active,
            expiration_date=modulo_in.expiration_date,
            initial_template=modulo_in.initial_template,
        )
        db.add(asignacion)
        db.commit()
        db.refresh(asignacion)

    # Asegura que las relaciones estén cargadas
    db.refresh(asignacion)
    _ = asignacion.tenant
    _ = asignacion.module

    # Coalesce de slug profesional: preferir slug, luego nombre, luego tenant_id
    company_slug = (
        getattr(asignacion.tenant, "slug", None)
        or getattr(asignacion.tenant, "name", None)
        or str(asignacion.tenant_id)
    )

    return schemas.EmpresaModuloOutAdmin(
        id=asignacion.id,  # type: ignore[arg-type]
        tenant_id=asignacion.tenant_id,  # type: ignore[arg-type]
        module_id=asignacion.module_id,  # type: ignore[arg-type]
        active=asignacion.active,  # type: ignore[arg-type]
        activation_date=asignacion.activation_date,  # type: ignore[arg-type]
        expiration_date=asignacion.expiration_date,  # type: ignore[arg-type]
        initial_template=asignacion.initial_template,  # type: ignore[arg-type]
        company_slug=company_slug,
        module=schemas.ModuloOut.from_orm(asignacion.module),
    )
