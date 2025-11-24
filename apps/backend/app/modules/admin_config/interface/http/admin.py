from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn
from app.modules.admin_config.application.dias_semana.use_cases import (
    ActualizarDiaSemana,
    CrearDiaSemana,
    EliminarDiaSemana,
    ListarDiasSemana,
    ObtenerDiaSemana,
)
from app.modules.admin_config.application.horarios_atencion.dto import HorarioAtencionIn
from app.modules.admin_config.application.horarios_atencion.use_cases import (
    ActualizarHorarioAtencion,
    CrearHorarioAtencion,
    EliminarHorarioAtencion,
    ListarHorariosAtencion,
    ObtenerHorarioAtencion,
)
from app.modules.admin_config.application.idiomas.dto import IdiomaIn
from app.modules.admin_config.application.idiomas.use_cases import (
    ActualizarIdioma,
    CrearIdioma,
    EliminarIdioma,
    ListarIdiomas,
    ObtenerIdioma,
)
from app.modules.admin_config.application.locales.dto import LocaleIn
from app.modules.admin_config.application.locales.use_cases import (
    ActualizarLocale,
    CrearLocale,
    EliminarLocale,
    ListarLocales,
    ObtenerLocale,
)
from app.modules.admin_config.application.monedas.dto import MonedaIn
from app.modules.admin_config.application.monedas.use_cases import (
    ActualizarMoneda,
    CrearMoneda,
    EliminarMoneda,
    ListarMonedas,
    ObtenerMoneda,
)
from app.modules.admin_config.application.paises.dto import PaisIn
from app.modules.admin_config.application.paises.use_cases import (
    ActualizarPais,
    CrearPais,
    EliminarPais,
    ListarPaises,
    ObtenerPais,
)
from app.modules.admin_config.application.sectores_plantilla.dto import SectorPlantillaIn
from app.modules.admin_config.application.sectores_plantilla.use_cases import (
    ActualizarSectorPlantilla,
    CrearSectorPlantilla,
    EliminarSectorPlantilla,
    ListarSectoresPlantilla,
    ObtenerSectorPlantilla,
)
from app.modules.admin_config.application.timezones.dto import TimezoneIn
from app.modules.admin_config.application.timezones.use_cases import (
    ActualizarTimezone,
    CrearTimezone,
    EliminarTimezone,
    ListarTimezones,
    ObtenerTimezone,
)
from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn
from app.modules.admin_config.application.tipos_empresa.use_cases import (
    ActualizarTipoEmpresa,
    CrearTipoEmpresa,
    EliminarTipoEmpresa,
    ListarTiposEmpresa,
    ObtenerTipoEmpresa,
)
from app.modules.admin_config.application.tipos_negocio.dto import TipoNegocioIn
from app.modules.admin_config.application.tipos_negocio.use_cases import (
    ActualizarTipoNegocio,
    CrearTipoNegocio,
    EliminarTipoNegocio,
    ListarTiposNegocio,
    ObtenerTipoNegocio,
)
from app.modules.admin_config.infrastructure.dias_semana.repository import SqlAlchemyDiaSemanaRepo
from app.modules.admin_config.infrastructure.horarios_atencion.repository import (
    SqlAlchemyHorarioAtencionRepo,
)
from app.modules.admin_config.infrastructure.idiomas.repository import SqlAlchemyIdiomaRepo
from app.modules.admin_config.infrastructure.locales.repository import SqlAlchemyLocaleRepo
from app.modules.admin_config.infrastructure.monedas.repository import SqlAlchemyMonedaRepo
from app.modules.admin_config.infrastructure.paises.repository import SqlAlchemyPaisRepo
from app.modules.admin_config.infrastructure.sectores_plantilla.repository import (
    SqlAlchemySectorPlantillaRepo,
)
from app.modules.admin_config.infrastructure.timezones.repository import SqlAlchemyTimezoneRepo
from app.modules.admin_config.infrastructure.tipos_empresa.repository import (
    SqlAlchemyTipoCompanyRepo,
)
from app.modules.admin_config.infrastructure.tipos_negocio.repository import (
    SqlAlchemyTipoNegocioRepo,
)

# Use modern use cases (all legacy CRUD migrated)
from app.modules.admin_config.schemas import (  # Reusar MonedaRead para listas simples (name/code) no aplica; endpoints devolverán objetos completos
    DiaSemanaCreate,
    DiaSemanaRead,
    DiaSemanaUpdate,
    HorarioAtencionCreate,
    HorarioAtencionRead,
    HorarioAtencionUpdate,
    IdiomaCreate,
    IdiomaRead,
    IdiomaUpdate,
    MonedaCreate,
    MonedaRead,
    MonedaUpdate,
    PaisCreate,
    PaisRead,
    PaisUpdate,
    SectorPlantillaCreate,
    SectorPlantillaRead,
    SectorPlantillaUpdate,
    TipoEmpresaCreate,
    TipoEmpresaRead,
    TipoEmpresaUpdate,
    TipoNegocioCreate,
    TipoNegocioRead,
    TipoNegocioUpdate,
)

router = APIRouter(prefix="/config", tags=["admin:config"])


def _moneda_repo(db: Session) -> SqlAlchemyMonedaRepo:
    return SqlAlchemyMonedaRepo(db)


def _moneda_schema(out) -> MonedaRead:
    return MonedaRead.model_validate(out.__dict__)


def _moneda_in_from_create(payload: MonedaCreate) -> MonedaIn:
    data = payload.model_dump()
    return MonedaIn(**data)


def _moneda_in_from_update(payload: MonedaUpdate, current) -> MonedaIn:
    data = payload.model_dump(exclude_unset=True)
    return MonedaIn(
        code=data.get("code", current.code),
        name=data.get("name", current.name),
        symbol=data.get("symbol", current.symbol),
        active=data.get("active", current.active),
    )


def _idioma_repo(db: Session) -> SqlAlchemyIdiomaRepo:
    return SqlAlchemyIdiomaRepo(db)


def _idioma_schema(out) -> IdiomaRead:
    return IdiomaRead.model_validate(
        {
            "id": out.id,
            "codigo": out.codigo,
            "name": out.nombre,
            "active": out.active,
        }
    )


def _idioma_in_from_create(payload: IdiomaCreate) -> IdiomaIn:
    data = payload.model_dump()
    return IdiomaIn(
        codigo=data["codigo"],
        nombre=data["name"],
        active=data.get("active", True),
    )


def _idioma_in_from_update(payload: IdiomaUpdate, current) -> IdiomaIn:
    data = payload.model_dump(exclude_unset=True)
    return IdiomaIn(
        codigo=data.get("codigo", current.codigo),
        nombre=data.get("name", current.nombre),
        active=data.get("active", current.active),
    )


def _pais_repo(db: Session) -> SqlAlchemyPaisRepo:
    return SqlAlchemyPaisRepo(db)


def _pais_schema(out) -> PaisRead:
    return PaisRead.model_validate(out.__dict__)


def _pais_in_from_create(payload: PaisCreate) -> PaisIn:
    data = payload.model_dump()
    return PaisIn(**data)


def _pais_in_from_update(payload: PaisUpdate, current) -> PaisIn:
    data = payload.model_dump(exclude_unset=True)
    return PaisIn(
        code=data.get("code", current.code),
        name=data.get("name", current.name),
        active=data.get("active", current.active),
    )


def _dias_repo(db: Session) -> SqlAlchemyDiaSemanaRepo:
    return SqlAlchemyDiaSemanaRepo(db)


def _dias_schema(out) -> DiaSemanaRead:
    return DiaSemanaRead.model_validate(out.__dict__)


def _dias_in_from_create(payload: DiaSemanaCreate) -> DiaSemanaIn:
    data = payload.model_dump()
    return DiaSemanaIn(**data)


def _dias_in_from_update(payload: DiaSemanaUpdate, current) -> DiaSemanaIn:
    data = payload.model_dump(exclude_unset=True)
    return DiaSemanaIn(
        clave=data.get("clave", current.clave),
        nombre=data.get("nombre", current.nombre),
        orden=data.get("orden", current.orden),
    )


def _horarios_repo(db: Session) -> SqlAlchemyHorarioAtencionRepo:
    return SqlAlchemyHorarioAtencionRepo(db)


def _horarios_schema(out) -> HorarioAtencionRead:
    return HorarioAtencionRead.model_validate(out.__dict__)


def _horarios_in_from_create(payload: HorarioAtencionCreate) -> HorarioAtencionIn:
    data = payload.model_dump()
    return HorarioAtencionIn(**data)


def _horarios_in_from_update(payload: HorarioAtencionUpdate, current) -> HorarioAtencionIn:
    data = payload.model_dump(exclude_unset=True)
    return HorarioAtencionIn(
        dia_id=data.get("dia_id", current.dia_id),
        inicio=data.get("inicio", current.inicio),
        fin=data.get("fin", current.fin),
    )


def _sectores_repo(db: Session) -> SqlAlchemySectorPlantillaRepo:
    return SqlAlchemySectorPlantillaRepo(db)


def _sectores_schema(out) -> SectorPlantillaRead:
    return SectorPlantillaRead.model_validate(out.__dict__)


def _sectores_in_from_create(payload: SectorPlantillaCreate) -> SectorPlantillaIn:
    data = payload.model_dump()
    return SectorPlantillaIn(**data)


def _sectores_in_from_update(payload: SectorPlantillaUpdate, current) -> SectorPlantillaIn:
    data = payload.model_dump(exclude_unset=True)
    return SectorPlantillaIn(
        sector_name=data.get("sector_name", current.sector_name),
        business_type_id=data.get("business_type_id", current.business_type_id),
        business_category_id=data.get("business_category_id", current.business_category_id),
        template_config=data.get("template_config", current.template_config),
        active=data.get("active", current.active),
    )


def _tipos_empresa_repo(db: Session) -> SqlAlchemyTipoCompanyRepo:
    return SqlAlchemyTipoCompanyRepo(db)


def _tipos_empresa_schema(out) -> TipoEmpresaRead:
    return TipoEmpresaRead.model_validate(out.__dict__)


def _tipos_empresa_in_from_create(payload: TipoEmpresaCreate) -> TipoEmpresaIn:
    data = payload.model_dump()
    return TipoEmpresaIn(**data)


def _tipos_empresa_in_from_update(payload: TipoEmpresaUpdate, current) -> TipoEmpresaIn:
    data = payload.model_dump(exclude_unset=True)
    return TipoEmpresaIn(
        name=data.get("name", current.name),
        description=data.get("description", current.description),
        active=data.get("active", current.active),
    )


def _tipos_negocio_repo(db: Session) -> SqlAlchemyTipoNegocioRepo:
    return SqlAlchemyTipoNegocioRepo(db)


def _tipos_negocio_schema(out) -> TipoNegocioRead:
    return TipoNegocioRead.model_validate(out.__dict__)


def _tipos_negocio_in_from_create(payload: TipoNegocioCreate) -> TipoNegocioIn:
    data = payload.model_dump()
    return TipoNegocioIn(**data)


def _tipos_negocio_in_from_update(payload: TipoNegocioUpdate, current) -> TipoNegocioIn:
    data = payload.model_dump(exclude_unset=True)
    return TipoNegocioIn(
        name=data.get("name", current.name),
        description=data.get("description", current.description),
        active=data.get("active", current.active),
    )


def _timezones_repo(db: Session) -> SqlAlchemyTimezoneRepo:
    return SqlAlchemyTimezoneRepo(db)


def _timezones_schema(out) -> dict:
    return out.__dict__


def _timezones_in_from_create(data: dict) -> TimezoneIn:
    return TimezoneIn(**data)


def _timezones_in_from_update(data: dict, current) -> TimezoneIn:
    return TimezoneIn(
        name=data.get("name", current.name),
        display_name=data.get("display_name", current.display_name),
        offset_minutes=data.get("offset_minutes", current.offset_minutes),
        active=data.get("active", current.active),
    )


def _locales_repo(db: Session) -> SqlAlchemyLocaleRepo:
    return SqlAlchemyLocaleRepo(db)


def _locales_schema(out) -> dict:
    return out.__dict__


def _locales_in_from_create(data: dict) -> LocaleIn:
    return LocaleIn(**data)


def _locales_in_from_update(data: dict, current) -> LocaleIn:
    return LocaleIn(
        code=data.get("code", current.code),
        name=data.get("name", current.name),
        active=data.get("active", current.active),
    )


# Idiomas
@router.get("/idioma", response_model=list[IdiomaRead])
def list_idiomas(db: Session = Depends(get_db)):
    use = ListarIdiomas(_idioma_repo(db))
    items = use.execute()
    return [_idioma_schema(item) for item in items]


@router.post("/idioma", response_model=IdiomaRead)
def create_idioma(data: IdiomaCreate, db: Session = Depends(get_db)):
    use = CrearIdioma(_idioma_repo(db))
    created = use.execute(_idioma_in_from_create(data))
    return _idioma_schema(created)


@router.put("/idioma/{id}", response_model=IdiomaRead)
def update_idioma(id: int, data: IdiomaUpdate, db: Session = Depends(get_db)):
    repo = _idioma_repo(db)
    try:
        current = ObtenerIdioma(repo).execute(id)
        payload = _idioma_in_from_update(data, current)
        updated = ActualizarIdioma(repo).execute(id, payload)
        return _idioma_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Idioma no encontrado")


@router.delete("/idioma/{id}")
def delete_idioma(id: int, db: Session = Depends(get_db)):
    repo = _idioma_repo(db)
    try:
        EliminarIdioma(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Idioma no encontrado")
    return {"ok": True}


# Monedas
@router.get("/moneda", response_model=list[MonedaRead])
def list_monedas(db: Session = Depends(get_db)):
    use = ListarMonedas(_moneda_repo(db))
    items = use.execute()
    return [_moneda_schema(item) for item in items]


@router.post("/moneda", response_model=MonedaRead)
def create_moneda(data: MonedaCreate, db: Session = Depends(get_db)):
    use = CrearMoneda(_moneda_repo(db))
    created = use.execute(_moneda_in_from_create(data))
    return _moneda_schema(created)


@router.put("/moneda/{id}", response_model=MonedaRead)
def update_moneda(id: int, data: MonedaUpdate, db: Session = Depends(get_db)):
    repo = _moneda_repo(db)
    try:
        current = ObtenerMoneda(repo).execute(id)
        payload = _moneda_in_from_update(data, current)
        updated = ActualizarMoneda(repo).execute(id, payload)
        return _moneda_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Moneda no encontrada")


@router.delete("/moneda/{id}")
def delete_moneda(id: int, db: Session = Depends(get_db)):
    repo = _moneda_repo(db)
    try:
        EliminarMoneda(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Moneda no encontrada")
    return {"ok": True}


# Países
@router.get("/pais", response_model=list[PaisRead])
def list_paises(db: Session = Depends(get_db)):
    use = ListarPaises(_pais_repo(db))
    items = use.execute()
    return [_pais_schema(item) for item in items]


@router.post("/pais", response_model=PaisRead)
def create_pais(data: PaisCreate, db: Session = Depends(get_db)):
    use = CrearPais(_pais_repo(db))
    created = use.execute(_pais_in_from_create(data))
    return _pais_schema(created)


@router.put("/pais/{id}", response_model=PaisRead)
def update_pais(id: int, data: PaisUpdate, db: Session = Depends(get_db)):
    repo = _pais_repo(db)
    try:
        current = ObtenerPais(repo).execute(id)
        payload = _pais_in_from_update(data, current)
        updated = ActualizarPais(repo).execute(id, payload)
        return _pais_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="País no encontrado")


@router.delete("/pais/{id}")
def delete_pais(id: int, db: Session = Depends(get_db)):
    repo = _pais_repo(db)
    try:
        EliminarPais(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="País no encontrado")
    return {"ok": True}


# Timezones (CRUD simple)
@router.get("/timezone")
def list_timezones(db: Session = Depends(get_db)):
    use = ListarTimezones(_timezones_repo(db))
    items = use.execute()
    return [_timezones_schema(item) for item in items]


@router.post("/timezone")
def create_timezone(data: dict, db: Session = Depends(get_db)):
    use = CrearTimezone(_timezones_repo(db))
    created = use.execute(_timezones_in_from_create(data))
    return _timezones_schema(created)


@router.put("/timezone/{name}")
def update_timezone(name: str, data: dict, db: Session = Depends(get_db)):
    repo = _timezones_repo(db)
    try:
        current = ObtenerTimezone(repo).execute(name)
        payload = _timezones_in_from_update(data, current)
        updated = ActualizarTimezone(repo).execute(name, payload)
        return _timezones_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Timezone no encontrado")


@router.delete("/timezone/{name}")
def delete_timezone(name: str, db: Session = Depends(get_db)):
    repo = _timezones_repo(db)
    try:
        EliminarTimezone(repo).execute(name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Timezone no encontrado")
    return {"ok": True}


# Locales (CRUD simple)
@router.get("/locale")
def list_locales(db: Session = Depends(get_db)):
    use = ListarLocales(_locales_repo(db))
    items = use.execute()
    return [_locales_schema(item) for item in items]


@router.post("/locale")
def create_locale(data: dict, db: Session = Depends(get_db)):
    use = CrearLocale(_locales_repo(db))
    created = use.execute(_locales_in_from_create(data))
    return _locales_schema(created)


@router.put("/locale/{code}")
def update_locale(code: str, data: dict, db: Session = Depends(get_db)):
    repo = _locales_repo(db)
    try:
        current = ObtenerLocale(repo).execute(code)
        payload = _locales_in_from_update(data, current)
        updated = ActualizarLocale(repo).execute(code, payload)
        return _locales_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Locale no encontrado")


@router.delete("/locale/{code}")
def delete_locale(code: str, db: Session = Depends(get_db)):
    repo = _locales_repo(db)
    try:
        EliminarLocale(repo).execute(code)
    except ValueError:
        raise HTTPException(status_code=404, detail="Locale no encontrado")
    return {"ok": True}


# Días de semana (ruta moderna `/dias`)
@router.get("/dias", response_model=list[DiaSemanaRead])
def list_dias(db: Session = Depends(get_db)):
    use = ListarDiasSemana(_dias_repo(db))
    items = use.execute()
    return [_dias_schema(item) for item in items]


@router.post("/dias", response_model=DiaSemanaRead)
def create_dia(data: DiaSemanaCreate, db: Session = Depends(get_db)):
    use = CrearDiaSemana(_dias_repo(db))
    created = use.execute(_dias_in_from_create(data))
    return _dias_schema(created)


@router.put("/dias/{id}", response_model=DiaSemanaRead)
def update_dia(id: int, data: DiaSemanaUpdate, db: Session = Depends(get_db)):
    repo = _dias_repo(db)
    try:
        current = ObtenerDiaSemana(repo).execute(id)
        payload = _dias_in_from_update(data, current)
        updated = ActualizarDiaSemana(repo).execute(id, payload)
        return _dias_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Día no encontrado")


@router.delete("/dias/{id}")
def delete_dia(id: int, db: Session = Depends(get_db)):
    repo = _dias_repo(db)
    try:
        EliminarDiaSemana(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Día no encontrado")
    return {"ok": True}


# Horario de atención (ruta moderna `/horario_atencion`)
@router.get("/horario_atencion", response_model=list[HorarioAtencionRead])
def list_horarios(db: Session = Depends(get_db)):
    use = ListarHorariosAtencion(_horarios_repo(db))
    items = use.execute()
    return [_horarios_schema(item) for item in items]


@router.post("/horario_atencion", response_model=HorarioAtencionRead)
def create_horario(data: HorarioAtencionCreate, db: Session = Depends(get_db)):
    use = CrearHorarioAtencion(_horarios_repo(db))
    created = use.execute(_horarios_in_from_create(data))
    return _horarios_schema(created)


@router.put("/horario_atencion/{id}", response_model=HorarioAtencionRead)
def update_horario(id: int, data: HorarioAtencionUpdate, db: Session = Depends(get_db)):
    repo = _horarios_repo(db)
    try:
        current = ObtenerHorarioAtencion(repo).execute(id)
        payload = _horarios_in_from_update(data, current)
        updated = ActualizarHorarioAtencion(repo).execute(id, payload)
        return _horarios_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Horario no encontrado")


@router.delete("/horario_atencion/{id}")
def delete_horario(id: int, db: Session = Depends(get_db)):
    repo = _horarios_repo(db)
    try:
        EliminarHorarioAtencion(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    return {"ok": True}


# Sectores (plantillas)
@router.get("/sectores", response_model=list[SectorPlantillaRead])
def list_sectores(db: Session = Depends(get_db)):
    use = ListarSectoresPlantilla(_sectores_repo(db))
    items = use.execute()
    return [_sectores_schema(item) for item in items]


@router.post("/sectores", response_model=SectorPlantillaRead)
def create_sector(data: SectorPlantillaCreate, db: Session = Depends(get_db)):
    use = CrearSectorPlantilla(_sectores_repo(db))
    created = use.execute(_sectores_in_from_create(data))
    return _sectores_schema(created)


@router.get("/sectores/{id}", response_model=SectorPlantillaRead)
def get_sector(id: int, db: Session = Depends(get_db)):
    use = ObtenerSectorPlantilla(_sectores_repo(db))
    try:
        sector = use.execute(id)
        return _sectores_schema(sector)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sector no encontrado")


@router.put("/sectores/{id}", response_model=SectorPlantillaRead)
def update_sector(id: int, data: SectorPlantillaUpdate, db: Session = Depends(get_db)):
    repo = _sectores_repo(db)
    try:
        current = ObtenerSectorPlantilla(repo).execute(id)
        payload = _sectores_in_from_update(data, current)
        updated = ActualizarSectorPlantilla(repo).execute(id, payload)
        return _sectores_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sector no encontrado")


@router.delete("/sectores/{id}")
def delete_sector(id: int, db: Session = Depends(get_db)):
    repo = _sectores_repo(db)
    try:
        EliminarSectorPlantilla(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Sector no encontrado")
    return {"ok": True}


# Tipo empresa
@router.get("/tipo-empresa", response_model=list[TipoEmpresaRead])
def list_tipo_empresa(db: Session = Depends(get_db)):
    use = ListarTiposEmpresa(_tipos_empresa_repo(db))
    items = use.execute()
    return [_tipos_empresa_schema(item) for item in items]


@router.post("/tipo-empresa", response_model=TipoEmpresaRead)
def create_tipo_empresa(data: TipoEmpresaCreate, db: Session = Depends(get_db)):
    use = CrearTipoEmpresa(_tipos_empresa_repo(db))
    created = use.execute(_tipos_empresa_in_from_create(data))
    return _tipos_empresa_schema(created)


@router.put("/tipo-empresa/{id}", response_model=TipoEmpresaRead)
def update_tipo_empresa(id: str, data: TipoEmpresaUpdate, db: Session = Depends(get_db)):
    from uuid import UUID as _UUID

    try:
        uid = _UUID(id)
    except ValueError:
        uid = id
    repo = _tipos_empresa_repo(db)
    try:
        current = ObtenerTipoEmpresa(repo).execute(uid)
        payload = _tipos_empresa_in_from_update(data, current)
        updated = ActualizarTipoEmpresa(repo).execute(uid, payload)
        return _tipos_empresa_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tipo de empresa no encontrado")


@router.delete("/tipo-empresa/{id}")
def delete_tipo_empresa(id: str, db: Session = Depends(get_db)):
    from uuid import UUID as _UUID

    try:
        uid = _UUID(id)
    except ValueError:
        uid = id
    repo = _tipos_empresa_repo(db)
    try:
        EliminarTipoEmpresa(repo).execute(uid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tipo de empresa no encontrado")
    return {"ok": True}


# Tipo negocio
@router.get("/tipo-negocio", response_model=list[TipoNegocioRead])
def list_tipo_negocio(db: Session = Depends(get_db)):
    use = ListarTiposNegocio(_tipos_negocio_repo(db))
    items = use.execute()
    return [_tipos_negocio_schema(item) for item in items]


@router.post("/tipo-negocio", response_model=TipoNegocioRead)
def create_tipo_negocio(data: TipoNegocioCreate, db: Session = Depends(get_db)):
    use = CrearTipoNegocio(_tipos_negocio_repo(db))
    created = use.execute(_tipos_negocio_in_from_create(data))
    return _tipos_negocio_schema(created)


@router.put("/tipo-negocio/{id}", response_model=TipoNegocioRead)
def update_tipo_negocio(id: int, data: TipoNegocioUpdate, db: Session = Depends(get_db)):
    repo = _tipos_negocio_repo(db)
    try:
        current = ObtenerTipoNegocio(repo).execute(id)
        payload = _tipos_negocio_in_from_update(data, current)
        updated = ActualizarTipoNegocio(repo).execute(id, payload)
        return _tipos_negocio_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tipo de negocio no encontrado")


@router.delete("/tipo-negocio/{id}")
def delete_tipo_negocio(id: int, db: Session = Depends(get_db)):
    repo = _tipos_negocio_repo(db)
    try:
        EliminarTipoNegocio(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tipo de negocio no encontrado")
    return {"ok": True}
