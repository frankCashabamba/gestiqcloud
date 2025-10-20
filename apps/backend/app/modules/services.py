"""Module: services.py

Service layer helpers for module assignment to companies and users.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.core.modulo import EmpresaModulo, ModuloAsignado
from app.models.tenant import Tenant
from app.db.rls import set_tenant_guc
from app.modules import crud, schemas


# ---------- EMPRESA-MODULO ----------
def asignar_modulo_a_empresa_si_no_existe(
    db: Session,
    empresa_id: int,
    modulo_in: schemas.EmpresaModuloCreate,
):
    existente = db.query(EmpresaModulo).filter_by(
        empresa_id=empresa_id,
        modulo_id=modulo_in.modulo_id,
    ).first()

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Este módulo ya fue asignado a esta empresa.",
        )

    return crud.asignar_modulo_a_empresa(db, empresa_id, modulo_in)


# ---------- USUARIO-MODULO ----------
def asignar_modulo_a_usuario_si_empresa_lo_tiene(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    modulo_id: int,
):
    # Verifica que la empresa tenga contratado el módulo
    empresa_modulo = db.query(EmpresaModulo).filter_by(
        empresa_id=empresa_id,
        modulo_id=modulo_id,
        activo=True,
    ).first()

    if not empresa_modulo:
        raise HTTPException(
            status_code=403,
            detail="La empresa no tiene contratado este módulo.",
        )

    # Verifica que el usuario aún no tenga el módulo asignado
    existente = db.query(ModuloAsignado).filter_by(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        modulo_id=modulo_id,
    ).first()

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Este módulo ya está asignado al usuario.",
        )

    return crud.asignar_modulo_a_usuario(db, empresa_id, usuario_id, modulo_id)


def upsert_modulo_a_empresa(
    db: Session,
    empresa_id: int,
    modulo_in: schemas.EmpresaModuloCreate,
) -> schemas.EmpresaModuloOutAdmin:
    # Resolve tenant_id from empresa_id to avoid relying on GUC triggers in admin routes
    tenant_row = db.query(Tenant).filter(Tenant.empresa_id == empresa_id).first()
    if not tenant_row:
        raise HTTPException(status_code=400, detail="Empresa sin tenant asociado")
    tenant_uuid = getattr(tenant_row, "id")
    # Set GUC locally for this transaction to satisfy any trigger relying on it
    try:
        set_tenant_guc(db, str(tenant_uuid), persist=False)
    except Exception:
        pass
    existente = db.query(EmpresaModulo).filter_by(
        empresa_id=empresa_id,
        modulo_id=modulo_in.modulo_id,
    ).first()

    if existente:
        existente.activo = modulo_in.activo  # type: ignore[assignment]
        existente.fecha_expiracion = modulo_in.fecha_expiracion  # type: ignore[assignment]
        existente.plantilla_inicial = modulo_in.plantilla_inicial  # type: ignore[assignment]
        db.commit()
        db.refresh(existente)
        asignacion = existente
    else:
        asignacion = EmpresaModulo(
            empresa_id=empresa_id,
            modulo_id=modulo_in.modulo_id,
            tenant_id=tenant_uuid,
            activo=modulo_in.activo,
            fecha_expiracion=modulo_in.fecha_expiracion,
            plantilla_inicial=modulo_in.plantilla_inicial,
        )
        db.add(asignacion)
        db.commit()
        db.refresh(asignacion)

    # Asegura que las relaciones estén cargadas
    db.refresh(asignacion)
    _ = asignacion.empresa
    _ = asignacion.modulo

    # Coalesce de slug profesional: preferir slug, luego nombre, luego empresa_id
    empresa_slug = (
        getattr(asignacion.empresa, "slug", None)
        or getattr(asignacion.empresa, "nombre", None)
        or str(asignacion.empresa_id)
    )

    return schemas.EmpresaModuloOutAdmin(
        id=asignacion.id,  # type: ignore[arg-type]
        empresa_id=asignacion.empresa_id,  # type: ignore[arg-type]
        modulo_id=asignacion.modulo_id,  # type: ignore[arg-type]
        activo=asignacion.activo,  # type: ignore[arg-type]
        fecha_activacion=asignacion.fecha_activacion,  # type: ignore[arg-type]
        fecha_expiracion=asignacion.fecha_expiracion,  # type: ignore[arg-type]
        plantilla_inicial=asignacion.plantilla_inicial,  # type: ignore[arg-type]
        empresa_slug=empresa_slug,
        modulo=schemas.ModuloOut.from_orm(asignacion.modulo),
    )
