"""Module: home.py

Auto-generated module docstring."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import Empresa
from app.routers.protected import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(
    request: Request,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    usuario_empresa = False
    empresa = None
    empresa_nombre = None
    tema_empresa = {}

    # Asumiendo que user contiene empresa_id cuando es usuario empresa
    empresa_id = user.get("empresa_id") if user else None

    if empresa_id:
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if empresa:
            usuario_empresa = True
            empresa_nombre = empresa.nombre
            tema_empresa = {
                "color_primario": empresa.color_primario,
                "plantilla": empresa.plantilla,
                "logo": empresa.logo_url  # o como tengas la URL del logo
            }

    return templates.TemplateResponse("base.html", {
        "request": request,
        "user": user,
        "usuario_empresa": usuario_empresa,
        "empresa": empresa,
        "empresa_nombre": empresa_nombre,
        "tema_empresa": tema_empresa,
        "now": datetime.utcnow()
    })
