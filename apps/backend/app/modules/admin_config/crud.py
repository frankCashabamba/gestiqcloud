from app.core.base_crud import BaseCRUD
from app.modules.admin_config.schemas import (
    IdiomaCreate, IdiomaUpdate,
    MonedaCreate, MonedaUpdate,
    DiaSemanaCreate, DiaSemanaUpdate,
    HorarioAtencionCreate, HorarioAtencionUpdate,
    SectorPlantillaCreate, SectorPlantillaUpdate,
    TipoEmpresaCreate, TipoEmpresaUpdate,
    TipoNegocioCreate, TipoNegocioUpdate,
)
from app.models import HorarioAtencion, Idioma, DiaSemana, SectorPlantilla, Moneda
from app.models import TipoEmpresa, TipoNegocio


idioma_crud = BaseCRUD[Idioma, IdiomaCreate, IdiomaUpdate](Idioma)
moneda_crud = BaseCRUD[Moneda, MonedaCreate, MonedaUpdate](Moneda)
diasemana_crud = BaseCRUD[DiaSemana, DiaSemanaCreate, DiaSemanaUpdate](DiaSemana)
horarioatencion_crud = BaseCRUD[HorarioAtencion, HorarioAtencionCreate, HorarioAtencionUpdate](HorarioAtencion)
sectorplantilla_crud = BaseCRUD[SectorPlantilla, SectorPlantillaCreate, SectorPlantillaUpdate](SectorPlantilla)

tipo_empresa_crud = BaseCRUD[TipoEmpresa, TipoEmpresaCreate, TipoEmpresaUpdate](TipoEmpresa)
tipo_negocio_crud = BaseCRUD[TipoNegocio, TipoNegocioCreate, TipoNegocioUpdate](TipoNegocio)
