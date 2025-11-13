"""Schemas Pydantic para Recursos Humanos (Empleados y Vacaciones)"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============================================================================
# EMPLEADOS
# ============================================================================


# Base schema
class EmpleadoBase(BaseModel):
    """Campos comunes de Empleado"""

    name: str = Field(..., max_length=100, description="Nombre completo")
    email: EmailStr | None = Field(None, description="Email corporativo")
    phone: str | None = Field(None, max_length=20, pattern=r"^\+?[\d\s\-()]+$")
    identificacion: str | None = Field(None, max_length=20, description="DNI/RUC/Cédula")
    tipo_identificacion: str | None = Field(None, pattern="^(dni|ruc|cedula|passport)$")
    fecha_nacimiento: date | None = None
    fecha_ingreso: date = Field(default_factory=date.today, description="Fecha de ingreso")
    fecha_salida: date | None = Field(None, description="Fecha de salida (si aplica)")
    cargo: str | None = Field(None, max_length=100, description="Cargo o puesto")
    departamento: str | None = Field(None, max_length=100, description="Departamento")
    salario: float | None = Field(None, ge=0, description="Salario base")
    estado: str = Field(default="active", pattern="^(active|inactive|suspended)$")
    address: str | None = Field(None, max_length=255)
    notas: str | None = None


# Create schema
class EmpleadoCreate(EmpleadoBase):
    """Schema para crear empleado"""

    pass


# Update schema
class EmpleadoUpdate(BaseModel):
    """Schema para actualizar empleado (todos campos opcionales)"""

    name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20, pattern=r"^\+?[\d\s\-()]+$")
    identificacion: str | None = Field(None, max_length=20)
    tipo_identificacion: str | None = Field(None, pattern="^(dni|ruc|cedula|passport)$")
    fecha_nacimiento: date | None = None
    fecha_ingreso: date | None = None
    fecha_salida: date | None = None
    cargo: str | None = Field(None, max_length=100)
    departamento: str | None = Field(None, max_length=100)
    salario: float | None = Field(None, ge=0)
    estado: str | None = Field(None, pattern="^(active|inactive|suspended)$")
    address: str | None = Field(None, max_length=255)
    notas: str | None = None

    model_config = ConfigDict(extra="forbid")


# Response schema
class EmpleadoResponse(EmpleadoBase):
    """Schema de respuesta de empleado"""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class EmpleadoList(BaseModel):
    """Schema para lista paginada de empleados"""

    items: list[EmpleadoResponse]
    total: int
    page: int = 1
    page_size: int = 100


# ============================================================================
# VACACIONES
# ============================================================================


# Base schema
class VacacionBase(BaseModel):
    """Campos comunes de Vacación"""

    empleado_id: UUID = Field(..., description="ID del empleado")
    fecha_inicio: date = Field(..., description="Fecha de inicio")
    fecha_fin: date = Field(..., description="Fecha de fin")
    dias_totales: int = Field(..., ge=1, description="Días totales de vacación")
    tipo: str = Field(default="annual", pattern="^(annual|sick|personal|unpaid)$")
    estado: str = Field(default="pending", pattern="^(pending|approved|rejected|cancelled)$")
    motivo: str | None = Field(None, max_length=500)
    aprobado_por: UUID | None = Field(None, description="ID del usuario que aprobó")
    fecha_aprobacion: datetime | None = None
    notas: str | None = None


# Create schema
class VacacionCreate(VacacionBase):
    """Schema para crear solicitud de vacación"""

    pass


# Update schema
class VacacionUpdate(BaseModel):
    """Schema para actualizar vacación"""

    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    dias_totales: int | None = Field(None, ge=1)
    tipo: str | None = Field(None, pattern="^(annual|sick|personal|unpaid)$")
    estado: str | None = Field(None, pattern="^(pending|approved|rejected|cancelled)$")
    motivo: str | None = Field(None, max_length=500)
    notas: str | None = None

    model_config = ConfigDict(extra="forbid")


# Response schema
class VacacionResponse(VacacionBase):
    """Schema de respuesta de vacación"""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# List schema
class VacacionList(BaseModel):
    """Schema para lista paginada de vacaciones"""

    items: list[VacacionResponse]
    total: int
    page: int = 1
    page_size: int = 100
