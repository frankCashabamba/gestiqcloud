"""Module: empresa_crud.py

Auto-generated module docstring."""

# app/core/empresa_crud.py
from typing import List, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.base_crud import BaseCRUD
from app.core.types import HasEmpresaID, IDType

# Declarar los genéricos con restricciones adecuadas
ModelType = TypeVar("ModelType", bound=HasEmpresaID)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class EmpresaCRUD(BaseCRUD[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Class EmpresaCRUD - auto-generated docstring."""

    def __init__(self, model: Type[ModelType]):
        """Function __init__ - auto-generated docstring."""
        super().__init__(model)

    def get_multi_by_empresa(self, db: Session, tenant_id: IDType) -> List[ModelType]:
        """Function get_multi_by_empresa - auto-generated docstring."""
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()  # type: ignore[arg-type]

    def create_with_empresa(
        self, db: Session, tenant_id: IDType, obj_in: CreateSchemaType
    ) -> ModelType:
        """Function create_with_empresa - auto-generated docstring."""
        # Use resolved tenant_id when creating records
        return self.create(db, obj_in, extra_fields={"tenant_id": tenant_id})
