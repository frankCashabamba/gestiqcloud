from pydantic import BaseModel, ConfigDict
from typing import Optional


class IdiomaCreate(BaseModel):
    codigo: str
    nombre: str
    activo: bool


class IdiomaUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    activo: Optional[bool] = None


class IdiomaRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)
class MonedaCreate(BaseModel):
    codigo: str
    nombre: str
    simbolo: str
    activo: bool


class MonedaUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    simbolo: Optional[str] = None
    activo: Optional[bool] = None


class MonedaRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    simbolo: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)
class DiaSemanaCreate(BaseModel):
    clave: str
    nombre: str
    orden: int


class DiaSemanaUpdate(BaseModel):
    clave: Optional[str] = None
    nombre: Optional[str] = None
    orden: Optional[int] = None


class DiaSemanaRead(BaseModel):
    id: int
    clave: str
    nombre: str
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
    nombre: str
    tipo_empresa_id: int
    tipo_negocio_id: int
    config_json: dict


class SectorPlantillaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_empresa_id: Optional[int] = None
    tipo_negocio_id: Optional[int] = None
    config_json: Optional[dict] = None


class SectorPlantillaRead(BaseModel):
    id: int
    nombre: str
    tipo_empresa_id: int
    tipo_negocio_id: int
    config_json: dict

    model_config = ConfigDict(from_attributes=True)
class TipoEmpresaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class TipoEmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class TipoEmpresaRead(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
class TipoNegocioCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class TipoNegocioUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class TipoNegocioRead(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
