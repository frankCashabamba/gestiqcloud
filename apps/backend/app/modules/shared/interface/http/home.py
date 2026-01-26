"""Home page router."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.tenant import Tenant
from app.routers.protected import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    is_company_user = False
    company = None
    company_name = None
    company_theme = {}

    tenant_id = user.get("tenant_id") if user else None

    if tenant_id:
        company = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if company:
            is_company_user = True
            company_name = company.name
            company_theme = {
                "color_primario": getattr(company, "color_primario", None),
                "plantilla": getattr(company, "plantilla_inicio", None),
                "logo": getattr(company, "logo", None),
            }

    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "user": user,
            "usuario_empresa": is_company_user,
            "empresa": company,
            "empresa_nombre": company_name,
            "tema_empresa": company_theme,
            "now": datetime.utcnow(),
        },
    )
