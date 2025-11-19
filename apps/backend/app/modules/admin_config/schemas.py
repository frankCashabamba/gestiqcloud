from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IdiomaCreate(BaseModel):
    codigo: str
    name: str
    active: bool = Field(True, alias="activo")

    model_config = ConfigDict(populate_by_name=True)


class IdiomaUpdate(BaseModel):
    codigo: str | None = None
    name: str | None = None
    active: bool | None = Field(None, alias="activo")

    model_config = ConfigDict(populate_by_name=True)


class IdiomaRead(BaseModel):
    id: int
    codigo: str
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
    id: int
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
    id: int
    code: str
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class DiaSemanaCreate(BaseModel):
    clave: str
    name: str
    orden: int


class DiaSemanaUpdate(BaseModel):
    clave: str | None = None
    name: str | None = None
    orden: int | None = None


class DiaSemanaRead(BaseModel):
    id: int
    clave: str
    name: str
    orden: int

    model_config = ConfigDict(from_attributes=True)


class HorarioAtencionCreate(BaseModel):
    dia_id: int
    inicio: str
    fin: str


class HorarioAtencionUpdate(BaseModel):
    dia_id: int | None = None
    inicio: str | None = None
    fin: str | None = None


class HorarioAtencionRead(BaseModel):
    id: int
    dia_id: int
    inicio: str
    fin: str

    model_config = ConfigDict(from_attributes=True)


class SectorPlantillaCreate(BaseModel):
    sector_name: str
    business_type_id: int | None = None
    business_category_id: int | None = None
    template_config: dict[str, Any] = Field(default_factory=dict)


class SectorPlantillaUpdate(BaseModel):
    sector_name: str | None = None
    business_type_id: int | None = None
    business_category_id: int | None = None
    template_config: dict[str, Any] | None = None


class SectorPlantillaRead(BaseModel):
    id: int
    sector_name: str
    business_type_id: int | None = None
    business_category_id: int | None = None
    template_config: dict[str, Any] = Field(default_factory=dict)
    active: bool = True

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
    id: int
    name: str
    description: str | None = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)
