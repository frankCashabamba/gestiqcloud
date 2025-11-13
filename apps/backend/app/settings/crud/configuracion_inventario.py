"""Module: configuracion_inventario.py

Auto-generated module docstring."""

# crud/configuracion_inventario.py

from sqlalchemy.orm import Session

from app.models import ConfiguracionInventarioEmpresa
from app.settings.schemas.configuracion_inventario import (
    ConfiguracionInventarioCreate,
    ConfiguracionInventarioUpdate,
)


def get_by_empresa(db: Session, tenant_id: int):
    """Function get_by_empresa - auto-generated docstring."""
    return (
        db.query(ConfiguracionInventarioEmpresa).filter_by(tenant_id=tenant_id).first()
    )


def create(db: Session, obj_in: ConfiguracionInventarioCreate):
    """Function create - auto-generated docstring."""
    data = obj_in.model_dump(exclude_none=True)  # v2: reemplaza .dict()
    config = ConfiguracionInventarioEmpresa(**data)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update(
    db: Session,
    db_obj: ConfiguracionInventarioEmpresa,
    obj_in: ConfiguracionInventarioUpdate,
):
    """Function update - auto-generated docstring."""
    updates = obj_in.model_dump(exclude_unset=True)  # solo campos enviados
    for field, value in updates.items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj
