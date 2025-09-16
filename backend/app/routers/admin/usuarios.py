from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.api.email.email_utils import reenviar_correo_reset
from app.models.empresa.usuarioempresa import UsuarioEmpresa


router = APIRouter()


@router.get("")
def listar_usuarios(db: Session = Depends(get_db)):
    """Lista usuarios principales (admins de empresa)."""
    rows = (
        db.query(UsuarioEmpresa)
        .filter(UsuarioEmpresa.es_admin_empresa == True)  # noqa: E712
        .order_by(UsuarioEmpresa.id.desc())
        .limit(500)
        .all()
    )
    def to_item(u: UsuarioEmpresa):
        nombre = f"{getattr(u, 'nombre_encargado', '')} {getattr(u, 'apellido_encargado', '')}".strip()
        return {
            "id": u.id,
            "nombre": nombre,
            "email": getattr(u, "email", None),
            "es_admin": True,
            "activo": bool(getattr(u, "activo", False)),
        }
    return [to_item(u) for u in rows]


@router.post("/{usuario_id}/reenviar-reset")
def reenviar_reset(usuario_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Reenvía el correo de restablecimiento de contraseña.

    En desarrollo, si EMAIL_DEV_LOG_ONLY=true (o falta SMTP), se imprime en logs el enlace de reset.
    """
    usuario = db.query(UsuarioEmpresa).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not getattr(usuario, "email", None):
        raise HTTPException(status_code=400, detail="Usuario sin email")

    reenviar_correo_reset(usuario.email, background_tasks)
    return {"msg": "ok"}


@router.post("/{usuario_id}/activar")
def activar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    u = db.query(UsuarioEmpresa).get(usuario_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.activo = True
    db.add(u)
    db.commit()
    return {"ok": True}


@router.post("/{usuario_id}/desactivar")
def desactivar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    u = db.query(UsuarioEmpresa).get(usuario_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.activo = False
    db.add(u)
    db.commit()
    return {"ok": True}


@router.post("/{usuario_id}/desactivar-empresa")
def desactivar_empresa(usuario_id: int, db: Session = Depends(get_db)):
    from app.models.empresa.empresa import Empresa
    u = db.query(UsuarioEmpresa).get(usuario_id)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    e = db.query(Empresa).get(u.empresa_id)
    if not e:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    e.activo = False
    db.add(e)
    db.commit()
    return {"ok": True}
