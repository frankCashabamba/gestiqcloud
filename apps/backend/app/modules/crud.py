"""Module: crud.py

Auto-generated module docstring."""

import os
import re
import shutil

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.core.modulo import AssignedModule, CompanyModule, Module
from app.models.tenant import Tenant
from app.modules import schemas


# ---------- MODULOS ----------
def _normalize_module_name(name: str) -> str:
    return (name or "").strip().lower()


def _asciify(value: str) -> str:
    return value.encode("utf-8", "backslashreplace").decode("ascii")


def crear_estructura_modulo(nombre: str):
    """Function crear_estructura_modulo - auto-generated docstring."""
    # 1. Validar que el nombre sea seguro (letras, nA�meros, guiones, guion_bajo)
    if not re.match(r"^[a-zA-Z0-9_-]+$", nombre):
        raise ValueError(
            "�?O Nombre de mA3dulo invA�lido. Solo se permiten letras, nA�meros, guiones y guiones bajos."
        )

    # 2. Normalizar nombre
    safe_name = _normalize_module_name(nombre).replace(" ", "_")

    # 3. Ruta base del frontend montado
    base_dir = "/app/src/modules"  # Debe coincidir con tu volumen montado
    base_path = os.path.abspath(os.path.join(base_dir, safe_name))

    # 4. Prevenir escritura fuera del directorio
    if not base_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("�?O Ruta invA�lida: intento de escapar del directorio permitido.")

    # 5. Crear carpeta si no existe
    try:
        print("Creating module folder at:", _asciify(base_path))
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
            print(f"Panel.tsx created at: {_asciify(panel_path)}")
        else:
            print(f"Panel.tsx already exists: {_asciify(panel_path)} (skipped)")

    except Exception as e:
        print("Error creating module structure:", e)
        raise


def obtener_modulo(db: Session, modulo_id: int):
    """Function obtener_modulo - auto-generated docstring."""
    return db.query(Module).filter(Module.id == modulo_id).first()


def crear_modulo(db: Session, modulo_data: schemas.ModuloCreate) -> Module:
    """Function crear_modulo - auto-generated docstring."""
    normalized_name = _normalize_module_name(modulo_data.name)
    existente = db.query(Module).filter(func.lower(Module.name) == normalized_name).first()

    if existente:
        raise ValueError(f"Ya existe un mA3dulo con el nombre '{modulo_data.name}'")

    payload = modulo_data.model_dump()
    payload["name"] = normalized_name
    nuevo_modulo = Module(**payload)
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
        if field == "name" and value:
            value = _normalize_module_name(value)
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
            print(f"Module folder deleted: {_asciify(base_path)}")
        else:
            print(f"Module folder not found: {_asciify(base_path)}")
    except Exception as e:
        print(f"Error deleting module folder: {e}")

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


def listar_modulos(db: Session) -> list[Module]:
    """Function listar_modulos - auto-generated docstring."""
    return db.query(Module).filter(Module.active).all()


# ---------- EMPRESA-MODULO ----------
def asignar_modulo_a_empresa(
    db: Session, tenant_id: int, modulo_in: schemas.EmpresaModuloCreate
) -> CompanyModule:
    # Use tenant_id directly (Tenant is now primary entity)
    asignacion = CompanyModule(
        tenant_id=tenant_id,
        module_id=modulo_in.module_id,
        expiration_date=modulo_in.expiration_date,
        initial_template=modulo_in.initial_template,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)
    return asignacion


def obtener_modulos_de_empresa(db: Session, tenant_id):
    """Obtiene módulos de empresa (tenant_id puede ser int o UUID)."""
    return (
        db.query(CompanyModule)
        .join(Tenant, CompanyModule.tenant_id == Tenant.id)
        .options(joinedload(CompanyModule.module), joinedload(CompanyModule.tenant))
        .filter(
            CompanyModule.tenant_id == tenant_id,
            CompanyModule.active,
        )
        .all()
    )


# ---------- MODULO-ASIGNADO ----------
def asignar_modulo_a_usuario(
    db: Session, tenant_id: int, usuario_id: int, modulo_id: int
) -> AssignedModule:
    asignacion = AssignedModule(
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
        db.query(AssignedModule)
        .options(joinedload(AssignedModule.module))  # ó. Esto carga los datos del módulo
        .filter(AssignedModule.tenant_id == tenant_id)
        .filter(AssignedModule.usuario_id == usuario_id)
        .all()
    )


def listar_modulos_publicos(db: Session) -> list[Module]:
    """Function listar_modulos_publicos - auto-generated docstring."""
    return db.query(Module).filter(Module.active).all()


def listar_modulo_admins(db: Session) -> list[Module]:
    """Function listar_modulo_admins - auto-generated docstring."""
    return db.query(Module).all()


def crear_modulo_db_only(db: Session, modulo_data: schemas.ModuloCreate) -> Module:
    """Crear solo el registro del módulo en BD (sin tocar el filesystem)."""
    name = _normalize_module_name(modulo_data.name)
    existente = db.query(Module).filter(func.lower(Module.name) == name).first()

    if existente:
        raise ValueError(f"Ya existe un módulo con el nombre '{name}'")

    data = modulo_data.model_dump()
    nuevo_modulo = Module(
        name=name,
        description=data.get("description"),
        active=bool(data.get("active") if data.get("active") is not None else True),
        icon=data.get("icon"),
        url=data.get("url"),
        initial_template=data.get("initial_template") or name,
        context_type=data.get("context_type") or "none",
        target_model=data.get("target_model"),
        context_filters=data.get("context_filters") or {},
        category=data.get("category"),
    )
    db.add(nuevo_modulo)
    db.commit()
    db.refresh(nuevo_modulo)
    return nuevo_modulo
