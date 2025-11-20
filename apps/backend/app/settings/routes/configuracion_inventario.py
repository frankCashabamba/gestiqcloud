"""Module: configuracion_inventario.py

Auto-generated module docstring."""

# routers/configuracion_inventario.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import app.settings.crud.configuracion_inventario as crud
import app.settings.schemas.configuracion_inventario as schemas
from app.config.database import get_db

router = APIRouter()


@router.get(
    "/api/configuracion-inventario/{tenant_id}",
    response_model=schemas.ConfiguracionInventarioOut,
)
def obtener_config(tenant_id: int, db: Session = Depends(get_db)):
    """Function obtener_config - auto-generated docstring."""
    config = crud.get_by_empresa(db, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    return config


@router.post("/api/configuracion-inventario", response_model=schemas.ConfiguracionInventarioOut)
def crear_config(config_in: schemas.ConfiguracionInventarioCreate, db: Session = Depends(get_db)):
    """Function crear_config - auto-generated docstring."""
    return crud.create(db, config_in)


@router.put(
    "/api/configuracion-inventario/{tenant_id}",
    response_model=schemas.ConfiguracionInventarioOut,
)
def actualizar_config(
    tenant_id: int,
    config_in: schemas.ConfiguracionInventarioUpdate,
    db: Session = Depends(get_db),
):
    """Function actualizar_config - auto-generated docstring."""
    config = crud.get_by_empresa(db, tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    return crud.update(db, config, config_in)
