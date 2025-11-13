"""Schemas Pydantic para Recursos Humanos (Empleados y Vacaciones)"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, EmailStr


# ============================================================================
# EMPLEADOS
# ============================================================================


# Base schema
class EmpleadoBase(BaseModel):
    """Campos comunes de Empleado"""

    name: str = Field(..., max_length=100, description="Nombre completo")
    email: Optional[EmailStr] = Field(None, description="Email corporativo")
    phone: Optional[str] = Field(None, max_length=20, pattern=r"^\+?[\d\s\-()]+$")
    identificacion: Optional[str] = Field(
        None, max_length=20, description="DNI/RUC/Cédula"
    )
    tipo_identificacion: Optional[str] = Field(
        None, pattern="^(dni|ruc|cedula|passport)$"
    )
    fecha_nacimiento: Optional[date] = None
    fecha_ingreso: date = Field(
        default_factory=date.today, description="Fecha de ingreso"
    )
    fecha_salida: Optional[date] = Field(
        None, description="Fecha de salida (si aplica)"
    )
    cargo: Optional[str] = Field(None, max_length=100, description="Cargo o puesto")
    departamento: Optional[str] = Field(
        None, max_length=100, description="Departamento"
    )
    salario: Optional[float] = Field(None, ge=0, description="Salario base")
    estado: str = Field(default="active", pattern="^(active|inactive|suspended)$")
    address: Optional[str] = Field(None, max_length=255)
    notas: Optional[str] = None


# Create schema
class EmpleadoCreate(EmpleadoBase):
    """Schema para crear empleado"""

    pass


# Update schema
class EmpleadoUpdate(BaseModel):
    """Schema para actualizar empleado (todos campos opcionales)"""

    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20, pattern=r"^\+?[\d\s\-()]+$")
    identificacion: Optional[str] = Field(None, max_length=20)
    tipo_identificacion: Optional[str] = Field(
        None, pattern="^(dni|ruc|cedula|passport)$"
    )
    fecha_nacimiento: Optional[date] = None
    fecha_ingreso: Optional[date] = None
    fecha_salida: Optional[date] = None
    cargo: Optional[str] = Field(None, max_length=100)
    departamento: Optional[str] = Field(None, max_length=100)
    salario: Optional[float] = Field(None, ge=0)
    estado: Optional[str] = Field(None, pattern="^(active|inactive|suspended)$")
    address: Optional[str] = Field(None, max_length=255)
    notas: Optional[str] = None

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
    estado: str = Field(
        default="pending", pattern="^(pending|approved|rejected|cancelled)$"
    )
    motivo: Optional[str] = Field(None, max_length=500)
    aprobado_por: Optional[UUID] = Field(None, description="ID del usuario que aprobó")
    fecha_aprobacion: Optional[datetime] = None
    notas: Optional[str] = None


# Create schema
class VacacionCreate(VacacionBase):
    """Schema para crear solicitud de vacación"""

    pass


# Update schema
class VacacionUpdate(BaseModel):
    """Schema para actualizar vacación"""

    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    dias_totales: Optional[int] = Field(None, ge=1)
    tipo: Optional[str] = Field(None, pattern="^(annual|sick|personal|unpaid)$")
    estado: Optional[str] = Field(
        None, pattern="^(pending|approved|rejected|cancelled)$"
    )
    motivo: Optional[str] = Field(None, max_length=500)
    notas: Optional[str] = None

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
