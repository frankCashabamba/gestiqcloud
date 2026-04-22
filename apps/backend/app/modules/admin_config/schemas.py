from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IdiomaCreate(BaseModel):
    code: str
    name: str
    active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class IdiomaUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    active: bool | None = None

    model_config = ConfigDict(populate_by_name=True)


class IdiomaRead(BaseModel):
    id: UUID
    code: str
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class MonedaCreate(BaseModel):
    code: str
    name: str
    symbol: str
    active: bool


class MonedaUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    symbol: str | None = None
    active: bool | None = None


class MonedaRead(BaseModel):
    id: UUID
    code: str
    name: str
    symbol: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


# País (Country)
class PaisCreate(BaseModel):
    code: str
    name: str
    active: bool


class PaisUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    active: bool | None = None


class PaisRead(BaseModel):
    id: UUID
    code: str
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class DiaSemanaCreate(BaseModel):
    code: str
    name: str
    order: int


class DiaSemanaUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    order: int | None = None


class DiaSemanaRead(BaseModel):
    id: UUID
    code: str | None = None
    name: str
    order: int

    model_config = ConfigDict(from_attributes=True)


class HorarioAtencionCreate(BaseModel):
    weekday_id: UUID
    start_time: str
    end_time: str


class HorarioAtencionUpdate(BaseModel):
    weekday_id: UUID | None = None
    start_time: str | None = None
    end_time: str | None = None


class HorarioAtencionRead(BaseModel):
    id: UUID
    weekday_id: UUID
    start_time: str
    end_time: str

    model_config = ConfigDict(from_attributes=True)


class SectorPlantillaCreate(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    template_config: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class SectorPlantillaUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    template_config: dict[str, Any] | None = None
    active: bool | None = None


class SectorPlantillaRead(BaseModel):
    id: UUID
    name: str
    code: str | None = None
    description: str | None = None
    template_config: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    config_version: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TipoEmpresaCreate(BaseModel):
    name: str
    description: str | None = None
    active: bool = True


class TipoEmpresaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class TipoEmpresaRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TipoNegocioCreate(BaseModel):
    name: str
    description: str | None = None


class TipoNegocioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TipoNegocioRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


# Tipo de Impuesto (Tax Type)
class TipoImpuestoCreate(BaseModel):
    country_code: str
    code: str
    name: str
    rate_default: float | None = None
    active: bool = True


class TipoImpuestoUpdate(BaseModel):
    country_code: str | None = None
    code: str | None = None
    name: str | None = None
    rate_default: float | None = None
    active: bool | None = None


class TipoImpuestoRead(BaseModel):
    id: str
    country_code: str
    code: str
    name: str
    rate_default: float | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


# Unidad de Medida (Unit of Measure)
class UnidadMedidaCreate(BaseModel):
    code: str
    name: str
    abbreviation: str
    active: bool = True


class UnidadMedidaUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    abbreviation: str | None = None
    active: bool | None = None


class UnidadMedidaRead(BaseModel):
    id: int
    code: str
    name: str
    abbreviation: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


# Tipo de Documento (Document Type)
class TipoDocumentoCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    active: bool = True


class TipoDocumentoUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class TipoDocumentoRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


# Categoría de Gasto (Expense Category)
class CategoriaGastoCreate(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    active: bool = True


class CategoriaGastoUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    parent_code: str | None = None
    active: bool | None = None


class CategoriaGastoRead(BaseModel):
    id: int
    code: str
    name: str
    parent_code: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)


# Método de Pago Plantilla (Payment Method Template)
class MetodoPagoPlantillaCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    active: bool = True


class MetodoPagoPlantillaUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class MetodoPagoPlantillaRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    active: bool

    model_config = ConfigDict(from_attributes=True)
