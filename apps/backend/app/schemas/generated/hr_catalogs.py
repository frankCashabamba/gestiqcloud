"""
Auto-generated schemas for HR catalog entities.
This demonstrates how to use the schema generator to eliminate duplication.
"""

from app.utils.schema_generator import get_catalog_schemas

# Generate all schemas for HR catalog entities
# No manual schema definition needed!

# Employee Department schemas
EmployeeDepartmentSchemas = get_catalog_schemas("EmployeeDepartment")
EmployeeDepartmentBase = EmployeeDepartmentSchemas["Base"]
EmployeeDepartmentCreate = EmployeeDepartmentSchemas["Create"]
EmployeeDepartmentUpdate = EmployeeDepartmentSchemas["Update"]
EmployeeDepartmentResponse = EmployeeDepartmentSchemas["Response"]

# Payroll Concept schemas
PayrollConceptSchemas = get_catalog_schemas(
    "PayrollConcept",
    extra_fields={
        "concept_type": ("EARNING" | "DEDUCTION", ...),
        "amount": ("float | None", None),
        "is_base": ("bool", True),
    },
)
PayrollConceptBase = PayrollConceptSchemas["Base"]
PayrollConceptCreate = PayrollConceptSchemas["Create"]
PayrollConceptUpdate = PayrollConceptSchemas["Update"]
PayrollConceptResponse = PayrollConceptSchemas["Response"]

# Export all schemas for easy import
__all__ = [
    # Employee Department
    "EmployeeDepartmentBase",
    "EmployeeDepartmentCreate",
    "EmployeeDepartmentUpdate",
    "EmployeeDepartmentResponse",
    # Payroll Concept
    "PayrollConceptBase",
    "PayrollConceptCreate",
    "PayrollConceptUpdate",
    "PayrollConceptResponse",
]

# Example of how this would have been written manually (for comparison):
#
# class EmployeeDepartmentBase(BaseModel):
#     name: str = Field(..., min_length=1, max_length=100)
#     code: str | None = Field(None, max_length=50)
#     description: str | None = Field(None)
#     is_active: bool = Field(default=True)
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
#
# That's ~20 lines of code vs 3 lines using the generator!
