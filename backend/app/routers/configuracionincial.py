"""Module: configuracionincial.py

Auto-generated module docstring."""

# routers/configuracioninicial.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import Empresa, ConfiguracionEmpresa
from app.routers.protected import get_current_user
from app.schemas.configuracion import AuthenticatedUser
from app.schemas.configuracionempresasinicial import (
    ConfiguracionEmpresaCreate, EmpresaConfiguracionOut)

router = APIRouter()

@router.post("/configuracion-inicial")
def guardar_configuracion_inicial(
  
    data: ConfiguracionEmpresaCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    empresa_id = current_user.empresa_id

    existente = db.query(ConfiguracionEmpresa).filter_by(empresa_id=empresa_id).first()
    if existente:
        raise HTTPException(status_code=400, detail="Configuración ya existe para esta empresa")

    nueva = ConfiguracionEmpresa(
        empresa_id=empresa_id,
        idioma_predeterminado=data.idioma_predeterminado,
        zona_horaria=data.zona_horaria,
        moneda=data.moneda,
        logo_empresa=data.logo_empresa,
        color_primario=data.color_primario,
        color_secundario=data.color_secundario
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return {"message": "Configuración guardada", "id": nueva.id}



@router.get("/configuracion/empresa/{empresa_id}", response_model=EmpresaConfiguracionOut)
def get_configuracion_empresa(
    
    empresa_id: int,  # ✅ usa empresa_id, no slug
    db: Session = Depends(get_db)
):
    config = (
        db.query(ConfiguracionEmpresa)
        .filter(ConfiguracionEmpresa.empresa_id == empresa_id)
        .first()
    )

    if not config:
        return {
            "empresa_nombre": f"Empresa {empresa_id}",
            "color_primario": "#4f46e5",
            "color_secundario": "#6c757d",
            "logo_empresa": None,
        }

    return {
        
        "logo_empresa": config.logo_empresa,
        "color_primario": config.color_primario,
        "color_secundario": config.color_secundario,
    }
