"""Module: crud.py

Auto-generated module docstring."""

import os
import re
import shutil

from sqlalchemy.orm import Session, joinedload

from app.models.core.modulo import EmpresaModulo, Modulo, ModuloAsignado
from app.models.tenant import Tenant
from app.modules import schemas


# ---------- MODULOS ----------
def crear_estructura_modulo(nombre: str):
    """Function crear_estructura_modulo - auto-generated docstring."""
    # 1. Validar que el nombre sea seguro (letras, nA�meros, guiones, guion_bajo)
    if not re.match(r"^[a-zA-Z0-9_-]+$", nombre):
        raise ValueError(
            "�?O Nombre de mA3dulo invA�lido. Solo se permiten letras, nA�meros, guiones y guiones bajos."
        )

    # 2. Normalizar nombre
    safe_name = nombre.lower().replace(" ", "_")

    # 3. Ruta base del frontend montado
    base_dir = "/app/src/modules"  # Debe coincidir con tu volumen montado
    base_path = os.path.abspath(os.path.join(base_dir, safe_name))

    # 4. Prevenir escritura fuera del directorio
    if not base_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("�?O Ruta invA�lida: intento de escapar del directorio permitido.")

    # 5. Crear carpeta si no existe
    try:
        print("📁 Creando carpeta en:", base_path)
        os.makedirs(base_path, exist_ok=True)

        # 6. Crear archivo Panel.tsx solo si no existe
        panel_path = os.path.join(base_path, "Panel.tsx")
        if not os.path.exists(panel_path):
            with open(panel_path, "w", encoding="utf-8") as f:
                f.write(
                    f"""// Auto-generado para el módulo: {nombre}
import React from 'react';

const Panel = () => {{
  return <div>{nombre} Panel</div>;
}};

export default Panel;
"""
                )
            print(f"✓ Panel.tsx creado en: {panel_path}")
        else:
            print(f"⚠ Ya existe: {panel_path} (no se sobrescribe)")

    except Exception as e:
        print("✗ Error al crear la estructura del módulo:", e)
        raise


def obtener_modulo(db: Session, modulo_id: int):
    """Function obtener_modulo - auto-generated docstring."""
    return db.query(Modulo).filter(Modulo.id == modulo_id).first()


def crear_modulo(db: Session, modulo_data: schemas.ModuloCreate) -> Modulo:
    """Function crear_modulo - auto-generated docstring."""
    existente = db.query(Modulo).filter(Modulo.name.ilike(modulo_data.name.strip())).first()

    if existente:
        raise ValueError(f"Ya existe un mA3dulo con el nombre '{modulo_data.name}'")

    nuevo_modulo = Modulo(**modulo_data.model_dump())
    db.add(nuevo_modulo)
    db.commit()
    db.refresh(nuevo_modulo)
    print("�sT�,? Creando estructura de mA3dulo:", nuevo_modulo.name)

    crear_estructura_modulo(nuevo_modulo.name)  # type: ignore[arg-type]
    print("DEBUG tipo:", type(nuevo_modulo.name), "valor:", nuevo_modulo.name)
    print("�o. Estructura creada")

    return nuevo_modulo


def actualizar_modulo(db: Session, modulo_id: int, modulo_data: schemas.ModuloUpdate):
    """Function actualizar_modulo - auto-generated docstring."""
    modulo = obtener_modulo(db, modulo_id)
    if not modulo:
        return None

    for field, value in modulo_data.dict(exclude_unset=True).items():
        setattr(modulo, field, value)

    db.commit()
    db.refresh(modulo)
    return modulo


def eliminar_modulo(db: Session, modulo_id: int):
    """Function eliminar_modulo - auto-generated docstring."""
    modulo = obtener_modulo(db, modulo_id)
    if not modulo:
        return None

    # Borrar carpeta del mA3dulo si existe
    try:
        safe_name = modulo.name.lower().replace(" ", "_")
        base_path = f"/app/src/modules/{safe_name}"
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
            print(f"dY-`�,? Carpeta eliminada: {base_path}")
        else:
            print(f"�s��,? Carpeta no encontrada: {base_path}")
    except Exception as e:
        print(f"�?O Error al eliminar carpeta del mA3dulo: {e}")

    # Borrar registro de la base de datos
    db.delete(modulo)
    db.commit()
    return True


def desactivar_modulo(db: Session, modulo_id: int):
    """Function desactivar_modulo - auto-generated docstring."""
    modulo = obtener_modulo(db, modulo_id)
    if not modulo:
        return None
    modulo.active = False
    db.commit()
    return modulo


def listar_modulos(db: Session) -> list[Modulo]:
    """Function listar_modulos - auto-generated docstring."""
    return db.query(Modulo).filter(Modulo.active).all()


# ---------- EMPRESA-MODULO ----------
def asignar_modulo_a_empresa(
    db: Session, tenant_id: int, modulo_in: schemas.EmpresaModuloCreate
) -> EmpresaModulo:
    # Use tenant_id directly (Tenant is now primary entity)
    asignacion = EmpresaModulo(
        tenant_id=tenant_id,
        modulo_id=modulo_in.modulo_id,
        fecha_expiracion=modulo_in.fecha_expiracion,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)
    return asignacion


def obtener_modulos_de_empresa(db: Session, tenant_id):
    """Obtiene módulos de empresa (tenant_id puede ser int o UUID)."""
    return (
        db.query(EmpresaModulo)
        .join(Tenant, EmpresaModulo.tenant_id == Tenant.id)
        .options(joinedload(EmpresaModulo.modulo), joinedload(EmpresaModulo.tenant))
        .filter(
            EmpresaModulo.tenant_id == tenant_id,
            EmpresaModulo.activo,
        )
        .all()
    )


# ---------- MODULO-ASIGNADO ----------
def asignar_modulo_a_usuario(
    db: Session, tenant_id: int, usuario_id: int, modulo_id: int
) -> ModuloAsignado:
    asignacion = ModuloAsignado(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        modulo_id=modulo_id,
        ver_modulo_auto=True,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)
    return asignacion


def obtener_modulos_de_usuario(db: Session, tenant_id: int, usuario_id: int):
    """Function obtener_modulos_de_usuario - auto-generated docstring."""
    return (
        db.query(ModuloAsignado)
        .options(joinedload(ModuloAsignado.modulo))  # �o. Esto carga los datos del mA3dulo
        .filter(ModuloAsignado.tenant_id == tenant_id)
        .filter(ModuloAsignado.usuario_id == usuario_id)
        .all()
    )


def listar_modulos_publicos(db: Session) -> list[Modulo]:
    """Function listar_modulos_publicos - auto-generated docstring."""
    return db.query(Modulo).filter(Modulo.active).all()


def listar_modulo_admins(db: Session) -> list[Modulo]:
    """Function listar_modulo_admins - auto-generated docstring."""
    return db.query(Modulo).all()


def crear_modulo_db_only(db: Session, modulo_data: schemas.ModuloCreate) -> Modulo:
    """Crear solo el registro del mA3dulo en BD (sin tocar el filesystem)."""
    existente = db.query(Modulo).filter(Modulo.name.ilike(modulo_data.name.strip())).first()

    if existente:
        raise ValueError(f"Ya existe un mA3dulo con el nombre '{modulo_data.name}'")

    nuevo_modulo = Modulo(**modulo_data.model_dump())
    db.add(nuevo_modulo)
    db.commit()
    db.refresh(nuevo_modulo)
    return nuevo_modulo
