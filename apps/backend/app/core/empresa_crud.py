"""Module: empresa_crud.py

Refactored to use TenantOperationsMixin for cleaner, DRY code.
"""

# app/core/empresa_crud.py
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.tenant_mixin import TenantOperationsMixin
from app.core.types import HasEmpresaID, IDType

# Declarar los genéricos con restricciones adecuadas
ModelType = TypeVar("ModelType", bound=HasEmpresaID)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class EmpresaCRUD(TenantOperationsMixin[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Empresa-specific CRUD operations using TenantOperationsMixin.

    This class now inherits all tenant operations from the mixin,
    eliminating code duplication across the application.
    """

    def __init__(self, model: type[ModelType]):
        """Initialize with model and inherit all tenant operations."""
        super().__init__(model)

    # Legacy method aliases for backward compatibility
    def get_multi_by_empresa(self, db: Session, tenant_id: IDType) -> list[ModelType]:
        """Legacy alias for get_multi_by_tenant."""
        return self.get_multi_by_tenant(db, tenant_id)

    def create_with_empresa(
        self, db: Session, tenant_id: IDType, obj_in: CreateSchemaType
    ) -> ModelType:
        """Legacy alias for create_with_tenant."""
        return self.create_with_tenant(db, tenant_id, obj_in)
