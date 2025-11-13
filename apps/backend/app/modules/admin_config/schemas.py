from typing import Any, Dict, Optional

from app.schemas.sector_plantilla import SectorConfigJSON
from pydantic import BaseModel, ConfigDict, Field


class IdiomaCreate(BaseModel):
    codigo: str
    name: str
    active: bool


class IdiomaUpdate(BaseModel):
    codigo: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None


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
    code: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    active: Optional[bool] = None


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
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None


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
    clave: Optional[str] = None
    name: Optional[str] = None
    orden: Optional[int] = None


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
    dia_id: Optional[int] = None
    inicio: Optional[str] = None
    fin: Optional[str] = None


class HorarioAtencionRead(BaseModel):
    id: int
    dia_id: int
    inicio: str
    fin: str

    model_config = ConfigDict(from_attributes=True)


class SectorPlantillaCreate(BaseModel):
    sector_name: str
    business_type_id: Optional[int] = None
    business_category_id: Optional[int] = None
    template_config: Dict[str, Any] = Field(default_factory=dict)


class SectorPlantillaUpdate(BaseModel):
    sector_name: Optional[str] = None
    business_type_id: Optional[int] = None
    business_category_id: Optional[int] = None
    template_config: Optional[Dict[str, Any]] = None


class SectorPlantillaRead(BaseModel):
    id: int
    sector_name: str
    business_type_id: Optional[int] = None
    business_category_id: Optional[int] = None
    template_config: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TipoEmpresaCreate(BaseModel):
    name: str
    description: Optional[str] = None
    active: bool = True


class TipoEmpresaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class TipoEmpresaRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TipoNegocioCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TipoNegocioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TipoNegocioRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    active: bool = True

    model_config = ConfigDict(from_attributes=True)
