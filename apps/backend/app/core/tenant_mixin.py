"""
Tenant operations mixin for CRUD classes.

Provides common tenant-specific operations that are repeated across
multiple repository classes in the application.

This mixin eliminates code duplication in 30+ repository classes.
"""

from typing import TypeVar

from sqlalchemy.orm import Session

from app.core.base_crud import BaseCRUD
from app.core.types import HasEmpresaID, IDType

# Type variables for proper typing
ModelType = TypeVar("ModelType", bound=HasEmpresaID)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class TenantOperationsMixin(BaseCRUD[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Mixin that provides tenant-specific CRUD operations.
    
    This mixin can be used by any CRUD class that needs to work with
    tenant-scoped models (models that have tenant_id field).
    
    Usage:
        class MyRepository(TenantOperationsMixin[MyModel, MyCreateSchema, MyUpdateSchema]):
            pass
    """
    
    def get_multi_by_tenant(self, db: Session, tenant_id: IDType) -> list[ModelType]:
        """
        Get all records for a specific tenant.
        
        This replaces the duplicate get_multi_by_empresa methods
        found in multiple repository classes.
        """
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()

    def get_multi_by_tenant_with_pagination(
        self, 
        db: Session, 
        tenant_id: IDType, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[ModelType]:
        """
        Get paginated records for a specific tenant.
        """
        return (
            db.query(self.model)
            .filter(self.model.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_tenant(
        self, 
        db: Session, 
        tenant_id: IDType, 
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        Create a new record associated with a tenant.
        
        This replaces the duplicate create_with_empresa methods
        found in multiple repository classes.
        """
        return self.create(db, obj_in, extra_fields={"tenant_id": tenant_id})

    def get_by_tenant_and_id(
        self, 
        db: Session, 
        tenant_id: IDType, 
        record_id: IDType
    ) -> ModelType | None:
        """
        Get a specific record by tenant and ID.
        
        This is a common pattern that was repeated in many places.
        """
        return (
            db.query(self.model)
            .filter(
                self.model.tenant_id == tenant_id,
                self.model.id == record_id
            )
            .first()
        )

    def update_by_tenant_and_id(
        self,
        db: Session,
        tenant_id: IDType,
        record_id: IDType,
        obj_in: UpdateSchemaType
    ) -> ModelType | None:
        """
        Update a record by tenant and ID.
        """
        db_obj = self.get_by_tenant_and_id(db, tenant_id, record_id)
        if not db_obj:
            return None
        return self.update(db, db_obj, obj_in)

    def remove_by_tenant_and_id(
        self,
        db: Session,
        tenant_id: IDType,
        record_id: IDType
    ) -> ModelType | None:
        """
        Remove a record by tenant and ID.
        """
        db_obj = self.get_by_tenant_and_id(db, tenant_id, record_id)
        if not db_obj:
            return None
        return self.remove(db, record_id)

    def count_by_tenant(self, db: Session, tenant_id: IDType) -> int:
        """
        Count records for a specific tenant.
        """
        return (
            db.query(self.model)
            .filter(self.model.tenant_id == tenant_id)
            .count()
        )
