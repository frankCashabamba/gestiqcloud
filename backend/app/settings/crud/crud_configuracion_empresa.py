"""Module: crud_configuracion_empresa.py

Auto-generated module docstring."""

# crud/configuracion_empresa.py

from sqlalchemy.orm import Session

from app.models import ConfiguracionEmpresa
from app.settings.schemas.configuracion_empresa import (
    ConfiguracionEmpresaCreate, ConfiguracionEmpresaUpdate)


def get_by_empresa(db: Session, empresa_id: int):
    """ Function get_by_empresa - auto-generated docstring. """
    return db.query(ConfiguracionEmpresa).filter_by(empresa_id=empresa_id).first()

def create(db: Session, obj_in: ConfiguracionEmpresaCreate):
    """ Function create - auto-generated docstring. """
    config = ConfiguracionEmpresa(**obj_in.dict())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

def update(db: Session, db_obj: ConfiguracionEmpresa, obj_in: ConfiguracionEmpresaUpdate):
    """ Function update - auto-generated docstring. """
    for field, value in obj_in.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj
