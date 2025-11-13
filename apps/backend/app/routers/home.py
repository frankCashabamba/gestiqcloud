"""Module: home.py

Auto-generated module docstring."""

from datetime import datetime

from app.config.database import get_db
from app.models.tenant import Tenant
from app.routers.protected import get_current_user
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    usuario_empresa = False
    empresa = None
    empresa_nombre = None
    tema_empresa = {}

    # Asumiendo que user contiene tenant_id cuando es usuario empresa
    tenant_id = user.get("tenant_id") if user else None

    if tenant_id:
        empresa = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if empresa:
            usuario_empresa = True
            empresa_nombre = empresa.name
            tema_empresa = {
                "color_primario": getattr(empresa, "color_primario", None),
                "plantilla": getattr(empresa, "plantilla_inicio", None),
                "logo": getattr(empresa, "logo", None),
            }

    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "user": user,
            "usuario_empresa": usuario_empresa,
            "empresa": empresa,
            "empresa_nombre": empresa_nombre,
            "tema_empresa": tema_empresa,
            "now": datetime.utcnow(),
        },
    )
