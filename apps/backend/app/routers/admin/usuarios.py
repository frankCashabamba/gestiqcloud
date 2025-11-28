from __future__ import annotations

from uuid import UUID

from app.api.email.email_utils import reenviar_correo_reset
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.company.company_user import CompanyUser as CompanyUser
from app.models.tenant import Tenant as Empresa
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="",
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


@router.get("")
def listar_usuarios(db: Session = Depends(get_db)):
    """Lista usuarios principales (admins de empresa)."""
    rows = (
        db.query(CompanyUser)
        .filter(CompanyUser.is_company_admin.is_(True))
        .order_by(CompanyUser.id.desc())
        .limit(500)
        .all()
    )

    def to_item(u: CompanyUser):
        nombre = (
            f"{getattr(u, 'nombre_encargado', '')} {getattr(u, 'apellido_encargado', '')}".strip()
        )
        return {
            # Forzar string para evitar clientes que tiparon number
            "id": str(u.id) if hasattr(u, "id") else None,
            "nombre": nombre,
            "email": getattr(u, "email", None),
            "es_admin": False,
            "is_company_admin": True,
            "activo": bool(getattr(u, "activo", False)),
        }

    return [to_item(u) for u in rows]


@router.post("/{usuario_id}/reenviar-reset")
def reenviar_reset(
    usuario_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Reenvía el correo de restablecimiento de contraseña.

    En desarrollo, si EMAIL_DEV_LOG_ONLY=true (o falta SMTP), se imprime en logs el enlace de reset.
    """
    usuario = db.query(CompanyUser).filter(CompanyUser.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="User not found")

    if not getattr(usuario, "email", None):
        raise HTTPException(status_code=400, detail="User without email")

    reenviar_correo_reset(usuario.email, background_tasks)
    return {"msg": "ok"}


@router.post("/{usuario_id}/activar")
def activar_usuario(usuario_id: UUID, db: Session = Depends(get_db)):
    u = db.query(CompanyUser).filter(CompanyUser.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not bool(getattr(u, "is_company_admin", False)):
        raise HTTPException(status_code=403, detail="not_tenant_admin")
    u.active = True
    db.add(u)
    db.commit()
    return {"ok": True}


@router.post("/{usuario_id}/desactivar")
def desactivar_usuario(usuario_id: UUID, db: Session = Depends(get_db)):
    u = db.query(CompanyUser).filter(CompanyUser.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not bool(getattr(u, "is_company_admin", False)):
        raise HTTPException(status_code=403, detail="not_tenant_admin")
    u.active = False
    db.add(u)
    db.commit()
    return {"ok": True}


@router.post("/{usuario_id}/desactivar-empresa")
def desactivar_empresa(usuario_id: UUID, db: Session = Depends(get_db)):
    u = db.query(CompanyUser).filter(CompanyUser.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    e = db.query(Empresa).filter(Empresa.id == u.tenant_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Company not found")
    e.active = False
    db.add(e)
    db.commit()
    return {"ok": True}
