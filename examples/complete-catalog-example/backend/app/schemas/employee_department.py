"""
Employee Department Schemas - Example using schema generator
"""

from app.utils.schema_generator import get_catalog_schemas

# Generate all schemas automatically - no manual definition needed!
EmployeeDepartmentSchemas = get_catalog_schemas("EmployeeDepartment")
EmployeeDepartmentBase = EmployeeDepartmentSchemas["Base"]
EmployeeDepartmentCreate = EmployeeDepartmentSchemas["Create"]
EmployeeDepartmentUpdate = EmployeeDepartmentSchemas["Update"]
EmployeeDepartmentResponse = EmployeeDepartmentSchemas["Response"]

# Export for easy import
__all__ = [
    "EmployeeDepartmentBase",
    "EmployeeDepartmentCreate",
    "EmployeeDepartmentUpdate", 
    "EmployeeDepartmentResponse",
]

# This replaces ~80 lines of manual schema definitions:
#
# class EmployeeDepartmentBase(BaseModel):
#     name: str = Field(..., min_length=1, max_length=100)
#     code: str | None = Field(None, max_length=50)
#     description: str | None = Field(None)
#     is_active: bool = Field(default=True)
#     tenant_id: UUID | None = Field(None)
#
# class EmployeeDepartmentCreate(EmployeeDepartmentBase):
#     pass
#
# class EmployeeDepartmentUpdate(BaseModel):
#     name: str | None = Field(None, min_length=1, max_length=100)
#     code: str | None = Field(None, max_length=50)
#     description: str | None = Field(None)
#     is_active: bool | None = Field(None)
#
# class EmployeeDepartmentResponse(EmployeeDepartmentBase):
#     id: UUID
#     tenant_id: UUID
#     created_at: str
#     updated_at: str
