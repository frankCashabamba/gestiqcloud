"""Module: base_crud.py

Auto-generated module docstring.
"""

# app/core/base_crud.py
from typing import Generic, List, Optional, Type, TypeVar, Union
from dataclasses import is_dataclass, asdict

from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.types import HasID, IDType

ModelType = TypeVar("ModelType", bound=HasID)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


def _to_dict(data: Union[BaseModel, dict, object], **dump_kwargs) -> dict:
    """
    Convierte un BaseModel (Pydantic v2) o un dict a dict.
    dump_kwargs se pasa a model_dump (p. ej. exclude_unset=True, by_alias=True, etc.).
    """
    if isinstance(data, BaseModel):
        return data.model_dump(**dump_kwargs)
    if isinstance(data, dict):
        return data
    # Dataclass support
    if is_dataclass(data):
        return asdict(data)
    # Fallback: build dict from attributes (DTO simple objects)
    if hasattr(data, "__dict__"):
        return {k: v for k, v in vars(data).items() if not k.startswith("_")}
    # Last resort: try to cast
    try:
        return dict(data)  # type: ignore[arg-type]
    except Exception:
        raise TypeError(f"Unsupported input type for _to_dict: {type(data).__name__}")


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Class BaseCRUD - auto-generated docstring."""

    def __init__(self, model: Type[ModelType]):
        """Function __init__ - auto-generated docstring."""
        self.model = model

    def get(self, db: Session, id: IDType) -> Optional[ModelType]:
        """Function get - auto-generated docstring."""
        model_id = getattr(self.model, "id")  # ayuda a MyPy
        return db.query(self.model).filter(model_id == id).first()

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Function get_multi - auto-generated docstring."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(
        self,
        db: Session,
        obj_in: CreateSchemaType,
        extra_fields: dict | None = None,
    ) -> ModelType:
        """Create instance with optional extra fields and safe transaction handling."""
        # Si necesitas alias o excluir None:
        # obj_data = _to_dict(obj_in, by_alias=True, exclude_none=True)
        obj_data = _to_dict(obj_in)
        obj_data.update(extra_fields or {})
        db_obj = self.model(**obj_data)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError:
            db.rollback()
            raise

    def update(
        self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        """Update instance with safe transaction handling."""
        # exclude_unset=True para solo aplicar campos proporcionados en el schema de actualización
        # Si quieres omitir None explícitos: añade exclude_none=True
        obj_data = _to_dict(obj_in, exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError:
            db.rollback()
            raise

    def remove(self, db: Session, id: IDType) -> Optional[ModelType]:
        """Delete instance by id with safe transaction handling."""
        obj = db.get(self.model, id)
        if not obj:
            return None
        try:
            db.delete(obj)
            db.commit()
            return obj
        except SQLAlchemyError:
            db.rollback()
            raise
