"""Module: crud.py

Auto-generated module docstring."""

import os
import re
import shutil

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from app.models.empresa.empresa import Empresa
from app.models.core.modulo import EmpresaModulo, Modulo, ModuloAsignado
from app.models.tenant import Tenant
from app.modules import schemas


# ---------- MODULOS ----------
def crear_estructura_modulo(nombre: str):
    """ Function crear_estructura_modulo - auto-generated docstring. """
    # 1. Validar que el nombre sea seguro (letras, números, guiones, guion_bajo)
    if not re.match(r"^[a-zA-Z0-9_-]+$", nombre):
        raise ValueError("❌ Nombre de módulo inválido. Solo se permiten letras, números, guiones y guiones bajos.")

    # 2. Normalizar nombre
    safe_name = nombre.lower().replace(" ", "_")

    # 3. Ruta base del frontend montado
    base_dir = "/app/src/modules"  # Debe coincidir con tu volumen montado
    base_path = os.path.abspath(os.path.join(base_dir, safe_name))

    # 4. Prevenir escritura fuera del directorio
    if not base_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("❌ Ruta inválida: intento de escapar del directorio permitido.")

    # 5. Crear carpeta si no existe
    try:
        print("📁 Creando carpeta en:", base_path)
        os.makedirs(base_path, exist_ok=True)

        # 6. Crear archivo Panel.tsx solo si no existe
        panel_path = os.path.join(base_path, "Panel.tsx")
        if not os.path.exists(panel_path):
            with open(panel_path, "w", encoding="utf-8") as f:
                f.write(f"""// Auto-generado para el módulo: {nombre}
import React from 'react';

const Panel = () => {{
  return <div>{nombre} Panel</div>;
}};

export default Panel;
""")
            print(f"✅ Panel.tsx creado en: {panel_path}")
        else:
            print(f"ℹ️ Ya existe: {panel_path} (no se sobrescribe)")

    except Exception as e:
        print("❌ Error al crear la estructura del módulo:", e)
        raise
            

def obtener_modulo(db: Session, modulo_id: int):
    """ Function obtener_modulo - auto-generated docstring. """
    return db.query(Modulo).filter(Modulo.id == modulo_id).first()


def crear_modulo(db: Session, modulo_data: schemas.ModuloCreate) -> Modulo:
    """ Function crear_modulo - auto-generated docstring. """
    existente = db.query(Modulo).filter(
        Modulo.nombre.ilike(modulo_data.nombre.strip())
    ).first()

    if existente:
        raise ValueError(f"Ya existe un módulo con el nombre '{modulo_data.nombre}'")

    nuevo_modulo = Modulo(**modulo_data.model_dump())
    db.add(nuevo_modulo)
    db.commit()
    db.refresh(nuevo_modulo)
    print("⚙️ Creando estructura de módulo:", nuevo_modulo.nombre)

    crear_estructura_modulo(nuevo_modulo.nombre)  # type: ignore[arg-type]
    print("DEBUG tipo:", type(nuevo_modulo.nombre), "valor:", nuevo_modulo.nombre)
    print("✅ Estructura creada")

    return nuevo_modulo


 


def actualizar_modulo(db: Session, modulo_id: int, modulo_data: schemas.ModuloUpdate):
    """ Function actualizar_modulo - auto-generated docstring. """
    modulo = obtener_modulo(db, modulo_id)
    if not modulo:
        return None

    for field, value in modulo_data.dict(exclude_unset=True).items():
        setattr(modulo, field, value)

    db.commit()
    db.refresh(modulo)
    return modulo


def eliminar_modulo(db: Session, modulo_id: int):
    """ Function eliminar_modulo - auto-generated docstring. """
    modulo = obtener_modulo(db, modulo_id)
    if not modulo:
        return None

    # Borrar carpeta del módulo si existe
    try:
        safe_name = modulo.nombre.lower().replace(" ", "_")
        base_path = f"/app/src/modules/{safe_name}"
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
            print(f"🗑️ Carpeta eliminada: {base_path}")
        else:
            print(f"⚠️ Carpeta no encontrada: {base_path}")
    except Exception as e:
        print(f"❌ Error al eliminar carpeta del módulo: {e}")

    # Borrar registro de la base de datos
    db.delete(modulo)
    db.commit()
    return True


def desactivar_modulo(db: Session, modulo_id: int):
    """ Function desactivar_modulo - auto-generated docstring. """
    modulo = obtener_modulo(db, modulo_id)
    if not modulo:
        return None
    modulo.activo = False
    db.commit()
    return modulo


def listar_modulos(db: Session) -> list[Modulo]:
    """ Function listar_modulos - auto-generated docstring. """
    return db.query(Modulo).filter(Modulo.activo == True).all()




# ---------- EMPRESA-MODULO ----------
def asignar_modulo_a_empresa(

    db: Session,
    empresa_id: int,
    modulo_in: schemas.EmpresaModuloCreate
) -> EmpresaModulo:
    # Resolve tenant_id from empresa_id to satisfy NOT NULL and triggers
    tenant_row = db.query(Tenant).filter(Tenant.empresa_id == empresa_id).first()
    if not tenant_row:
        raise ValueError("Empresa sin tenant asociado")
    asignacion = EmpresaModulo(
        empresa_id=empresa_id,
        modulo_id=modulo_in.modulo_id,
        tenant_id=getattr(tenant_row, "id"),
        fecha_expiracion=modulo_in.fecha_expiracion,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)
    return asignacion


def obtener_modulos_de_empresa(db: Session, empresa_id: int):
    """ Function obtener_modulos_de_empresa - auto-generated docstring. """
    return (
        db.query(EmpresaModulo)
        .join(Empresa)
        .options(joinedload(EmpresaModulo.modulo), joinedload(EmpresaModulo.empresa))
        .filter(
            EmpresaModulo.empresa_id == empresa_id,
            EmpresaModulo.activo == True  # ✅ aquí el filtro
        )
        .all()
    )

# ---------- MODULO-ASIGNADO ----------
def asignar_modulo_a_usuario(
   
    db: Session,
    empresa_id: int,
    usuario_id: int,
    modulo_id: int
) -> ModuloAsignado:
    asignacion = ModuloAsignado(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        modulo_id=modulo_id,
        ver_modulo_auto=True,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)
    return asignacion


def obtener_modulos_de_usuario(db: Session, empresa_id: int, usuario_id: int):
    """ Function obtener_modulos_de_usuario - auto-generated docstring. """
    return (
        db.query(ModuloAsignado)
        .options(joinedload(ModuloAsignado.modulo))  # ✅ Esto carga los datos del módulo
        .filter(ModuloAsignado.empresa_id == empresa_id)
        .filter(ModuloAsignado.usuario_id == usuario_id)
        .all()
    )


def listar_modulos_publicos(db: Session) -> list[Modulo]:
    """ Function listar_modulos_publicos - auto-generated docstring. """
    return db.query(Modulo).filter(Modulo.activo == True).all()


def listar_modulo_admins(db: Session) -> list[Modulo]:   
    """ Function listar_modulo_admins - auto-generated docstring. """
    return db.query(Modulo).all()


def crear_modulo_db_only(db: Session, modulo_data: schemas.ModuloCreate) -> Modulo:
    """Crear solo el registro del módulo en BD (sin tocar el filesystem)."""
    existente = db.query(Modulo).filter(
        Modulo.nombre.ilike(modulo_data.nombre.strip())
    ).first()

    if existente:
        raise ValueError(f"Ya existe un mA3dulo con el nombre '{modulo_data.nombre}'")

    nuevo_modulo = Modulo(**modulo_data.model_dump())
    db.add(nuevo_modulo)
    db.commit()
    db.refresh(nuevo_modulo)
    return nuevo_modulo
