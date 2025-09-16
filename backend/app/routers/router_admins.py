"""Module: router_admins.py

Auto-generated module docstring."""

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.email.email_utils import reenviar_correo_reset
from app.config.database import get_db
from app.models import UsuarioEmpresa
from app.usuarios.schemas import UsuarioEmpresaOut

router = APIRouter()


@router.get("/api/admins-empresa", response_model=List[UsuarioEmpresaOut])
def listar_admins_empresa(db: Session = Depends(get_db)):
    """ Function listar_admins_empresa - auto-generated docstring. """
    return db.query(UsuarioEmpresa).filter(UsuarioEmpresa.es_admin_empresa == True).all()





@router.post("/api/usuarios/{usuario_id}/activar")
def activar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """ Function activar_usuario - auto-generated docstring. """
    usuario = db.query(UsuarioEmpresa).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = True
    db.commit()
    return {"msg": "Usuario activado correctamente"}

@router.post("/api/usuarios/{usuario_id}/desactivar")
def desactivar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """ Function desactivar_usuario - auto-generated docstring. """
    usuario = db.query(UsuarioEmpresa).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = False
    db.commit()
    return {"msg": "Usuario desactivado correctamente"}




@router.post("/api/usuarios/{usuario_id}/reenviar-reset")
def reenviar_reset(usuario_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """ Function reenviar_reset - auto-generated docstring. """
    usuario = db.query(UsuarioEmpresa).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    reenviar_correo_reset(usuario.email, background_tasks)

    return {"msg": "Correo de restablecimiento enviado"}



@router.post("/api/empresas/{empresa_id}/reasignar-admin")
def reasignar_admin(empresa_id: int, nuevo_admin_id: int, db: Session = Depends(get_db)):
    """ Function reasignar_admin - auto-generated docstring. """
    usuarios = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.empresa_id == empresa_id).all()
    
    if not usuarios:
        raise HTTPException(status_code=404, detail="No hay usuarios en esta empresa")

    for u in usuarios:
        u.es_admin_empresa = (u.id == nuevo_admin_id)

    db.commit()
    return {"msg": "Administrador reasignado correctamente"}
