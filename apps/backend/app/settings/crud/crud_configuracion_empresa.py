"""Module: crud_configuracion_empresa.py

Auto-generated module docstring."""

# crud/configuracion_empresa.py

from app.models import ConfiguracionEmpresa
from app.settings.schemas.configuracion_empresa import (
    ConfiguracionEmpresaCreate,
    ConfiguracionEmpresaUpdate,
)
from sqlalchemy.orm import Session


def get_by_empresa(db: Session, tenant_id: int):
    """Function get_by_empresa - auto-generated docstring."""
    return db.query(ConfiguracionEmpresa).filter_by(tenant_id=tenant_id).first()


def create(db: Session, obj_in: ConfiguracionEmpresaCreate):
    """Function create - auto-generated docstring."""
    data = obj_in.model_dump(exclude_none=True)  # v2: reemplaza .dict()
    config = ConfiguracionEmpresa(**data)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update(db: Session, db_obj: ConfiguracionEmpresa, obj_in: ConfiguracionEmpresaUpdate):
    """Function update - auto-generated docstring."""
    updates = obj_in.model_dump(exclude_unset=True)  # v2: reemplaza .dict(exclude_unset=True)
    for field, value in updates.items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj
