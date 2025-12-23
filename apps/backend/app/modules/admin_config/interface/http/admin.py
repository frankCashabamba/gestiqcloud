from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.modules.admin_config.application.dias_semana.dto import DiaSemanaIn
from app.modules.admin_config.application.dias_semana.use_cases import (
    CreateWeekDay,
    DeleteWeekDay,
    GetWeekDay,
    ListWeekDays,
    UpdateWeekDay,
)
from app.modules.admin_config.application.horarios_atencion.dto import HorarioAtencionIn
from app.modules.admin_config.application.horarios_atencion.use_cases import (
    CreateAttentionSchedule,
    DeleteAttentionSchedule,
    GetAttentionSchedule,
    ListAttentionSchedules,
    UpdateAttentionSchedule,
)
from app.modules.admin_config.application.idiomas.dto import IdiomaIn
from app.modules.admin_config.application.idiomas.use_cases import (
    CreateLanguage,
    DeleteLanguage,
    GetLanguage,
    ListLanguages,
    UpdateLanguage,
)
from app.modules.admin_config.application.locales.dto import LocaleIn
from app.modules.admin_config.application.locales.use_cases import (
    CreateLocale,
    DeleteLocale,
    GetLocale,
    ListLocales,
    UpdateLocale,
)
from app.modules.admin_config.application.monedas.dto import MonedaIn
from app.modules.admin_config.application.monedas.use_cases import (
    CreateCurrency,
    DeleteCurrency,
    GetCurrency,
    ListCurrencies,
    UpdateCurrency,
)
from app.modules.admin_config.application.paises.dto import PaisIn
from app.modules.admin_config.application.paises.use_cases import (
    CreateCountry,
    DeleteCountry,
    GetCountry,
    ListCountries,
    UpdateCountry,
)
from app.modules.admin_config.application.sectores_plantilla.dto import SectorPlantillaIn
from app.modules.admin_config.application.sectores_plantilla.use_cases import (
    CreateTemplateSector,
    DeleteTemplateSector,
    GetTemplateSector,
    ListTemplateSectors,
    UpdateTemplateSector,
)
from app.modules.admin_config.application.timezones.dto import TimezoneIn
from app.modules.admin_config.application.timezones.use_cases import (
    CreateTimezone,
    DeleteTimezone,
    GetTimezone,
    ListTimezones,
    UpdateTimezone,
)
from app.modules.admin_config.application.tipos_empresa.dto import TipoEmpresaIn
from app.modules.admin_config.application.tipos_empresa.use_cases import (
    CreateCompanyType,
    DeleteCompanyType,
    GetCompanyType,
    ListCompanyTypes,
    UpdateCompanyType,
)
from app.modules.admin_config.application.tipos_negocio.dto import TipoNegocioIn
from app.modules.admin_config.application.tipos_negocio.use_cases import (
    CreateBusinessType,
    DeleteBusinessType,
    GetBusinessType,
    ListBusinessTypes,
    UpdateBusinessType,
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


def _currency_repo(db: Session) -> SqlAlchemyMonedaRepo:
    return SqlAlchemyMonedaRepo(db)


def _currency_schema(out) -> MonedaRead:
    return MonedaRead.model_validate(out.__dict__)


def _currency_in_from_create(payload: MonedaCreate) -> MonedaIn:
    data = payload.model_dump()
    return MonedaIn(**data)


def _currency_in_from_update(payload: MonedaUpdate, current) -> MonedaIn:
    data = payload.model_dump(exclude_unset=True)
    return MonedaIn(
        code=data.get("code", current.code),
        name=data.get("name", current.name),
        symbol=data.get("symbol", current.symbol),
        active=data.get("active", current.active),
    )


def _language_repo(db: Session) -> SqlAlchemyIdiomaRepo:
    return SqlAlchemyIdiomaRepo(db)


def _language_schema(out) -> IdiomaRead:
    return IdiomaRead.model_validate(
        {
            "id": out.id,
            "code": out.code,
            "name": out.name,
            "active": out.active,
        }
    )


def _language_in_from_create(payload: IdiomaCreate) -> IdiomaIn:
    data = payload.model_dump()
    return IdiomaIn(
        code=data["code"],
        name=data["name"],
        active=data.get("active", True),
    )


def _language_in_from_update(payload: IdiomaUpdate, current) -> IdiomaIn:
    data = payload.model_dump(exclude_unset=True)
    return IdiomaIn(
        code=data.get("code", current.code),
        name=data.get("name", current.name),
        active=data.get("active", current.active),
    )


def _country_repo(db: Session) -> SqlAlchemyPaisRepo:
    return SqlAlchemyPaisRepo(db)


def _country_schema(out) -> PaisRead:
    return PaisRead.model_validate(out.__dict__)


def _country_in_from_create(payload: PaisCreate) -> PaisIn:
    data = payload.model_dump()
    return PaisIn(**data)


def _country_in_from_update(payload: PaisUpdate, current) -> PaisIn:
    data = payload.model_dump(exclude_unset=True)
    return PaisIn(
        code=data.get("code", current.code),
        name=data.get("name", current.name),
        active=data.get("active", current.active),
    )


def _weekday_repo(db: Session) -> SqlAlchemyDiaSemanaRepo:
    return SqlAlchemyDiaSemanaRepo(db)


def _weekday_schema(out) -> DiaSemanaRead:
    return DiaSemanaRead.model_validate(out.__dict__)


def _weekday_in_from_create(payload: DiaSemanaCreate) -> DiaSemanaIn:
    data = payload.model_dump()
    return DiaSemanaIn(**data)


def _weekday_in_from_update(payload: DiaSemanaUpdate, current) -> DiaSemanaIn:
    data = payload.model_dump(exclude_unset=True)
    return DiaSemanaIn(
        clave=data.get("clave", current.clave),
        nombre=data.get("nombre", current.nombre),
        orden=data.get("orden", current.orden),
    )


def _attention_schedule_repo(db: Session) -> SqlAlchemyHorarioAtencionRepo:
    return SqlAlchemyHorarioAtencionRepo(db)


def _attention_schedule_schema(out) -> HorarioAtencionRead:
    return HorarioAtencionRead.model_validate(out.__dict__)


def _attention_schedule_in_from_create(payload: HorarioAtencionCreate) -> HorarioAtencionIn:
    data = payload.model_dump()
    return HorarioAtencionIn(**data)


def _attention_schedule_in_from_update(
    payload: HorarioAtencionUpdate, current
) -> HorarioAtencionIn:
    data = payload.model_dump(exclude_unset=True)
    return HorarioAtencionIn(
        dia_id=data.get("dia_id", current.dia_id),
        inicio=data.get("inicio", current.inicio),
        fin=data.get("fin", current.fin),
    )


def _template_sector_repo(db: Session) -> SqlAlchemySectorPlantillaRepo:
    return SqlAlchemySectorPlantillaRepo(db)


def _template_sector_schema(out) -> SectorPlantillaRead:
    return SectorPlantillaRead.model_validate(out.__dict__)


def _template_sector_in_from_create(payload: SectorPlantillaCreate) -> SectorPlantillaIn:
    data = payload.model_dump()
    return SectorPlantillaIn(**data)


def _template_sector_in_from_update(payload: SectorPlantillaUpdate, current) -> SectorPlantillaIn:
    data = payload.model_dump(exclude_unset=True)
    new_active = current.active if "active" not in data else data.get("active", current.active)
    return SectorPlantillaIn(
        name=data.get("name", current.name),
        code=data.get("code", current.code),
        description=data.get("description", current.description),
        template_config=data.get("template_config", current.template_config),
        active=new_active,
    )


def _business_type_repo(db: Session) -> SqlAlchemyTipoCompanyRepo:
    return SqlAlchemyTipoCompanyRepo(db)


def _business_type_schema(out) -> TipoEmpresaRead:
    return TipoEmpresaRead.model_validate(out.__dict__)


def _business_type_in_from_create(payload: TipoEmpresaCreate) -> TipoEmpresaIn:
    data = payload.model_dump()
    return TipoEmpresaIn(**data)


def _business_type_in_from_update(payload: TipoEmpresaUpdate, current) -> TipoEmpresaIn:
    data = payload.model_dump(exclude_unset=True)
    return TipoEmpresaIn(
        name=data.get("name", current.name),
        description=data.get("description", current.description),
        active=data.get("active", current.active),
    )


def _business_category_repo(db: Session) -> SqlAlchemyTipoNegocioRepo:
    return SqlAlchemyTipoNegocioRepo(db)


def _business_category_schema(out) -> TipoNegocioRead:
    return TipoNegocioRead.model_validate(out.__dict__)


def _business_category_in_from_create(payload: TipoNegocioCreate) -> TipoNegocioIn:
    data = payload.model_dump()
    return TipoNegocioIn(**data)


def _business_category_in_from_update(payload: TipoNegocioUpdate, current) -> TipoNegocioIn:
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


# Languages

@router.get("/language", response_model=list[IdiomaRead])
def list_languages(db: Session = Depends(get_db)):
    use = ListLanguages(_language_repo(db))
    items = use.execute()
    return [_language_schema(item) for item in items]


@router.post("/language", response_model=IdiomaRead)
def create_language(data: IdiomaCreate, db: Session = Depends(get_db)):
    use = CreateLanguage(_language_repo(db))
    created = use.execute(_language_in_from_create(data))
    return _language_schema(created)


@router.put("/language/{id}", response_model=IdiomaRead)
def update_language(id: int, data: IdiomaUpdate, db: Session = Depends(get_db)):
    repo = _language_repo(db)
    try:
        current = GetLanguage(repo).execute(id)
        payload = _language_in_from_update(data, current)
        updated = UpdateLanguage(repo).execute(id, payload)
        return _language_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Language not found")


@router.delete("/language/{id}")
def delete_language(id: int, db: Session = Depends(get_db)):
    repo = _language_repo(db)
    try:
        DeleteLanguage(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Language not found")
    return {"ok": True}


# Currencies
@router.get("/currency", response_model=list[MonedaRead])
def list_currencies(db: Session = Depends(get_db)):
    use = ListCurrencies(_currency_repo(db))
    items = use.execute()
    return [_currency_schema(item) for item in items]


@router.post("/currency", response_model=MonedaRead)
def create_currency(data: MonedaCreate, db: Session = Depends(get_db)):
    use = CreateCurrency(_currency_repo(db))
    created = use.execute(_currency_in_from_create(data))
    return _currency_schema(created)


@router.put("/currency/{id}", response_model=MonedaRead)
def update_currency(id: int, data: MonedaUpdate, db: Session = Depends(get_db)):
    repo = _currency_repo(db)
    try:
        current = GetCurrency(repo).execute(id)
        payload = _currency_in_from_update(data, current)
        updated = UpdateCurrency(repo).execute(id, payload)
        return _currency_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Currency not found")


@router.delete("/currency/{id}")
def delete_currency(id: int, db: Session = Depends(get_db)):
    repo = _currency_repo(db)
    try:
        DeleteCurrency(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Currency not found")
    return {"ok": True}


# Countries
@router.get("/country", response_model=list[PaisRead])
def list_countries(db: Session = Depends(get_db)):
    use = ListCountries(_country_repo(db))
    items = use.execute()
    return [_country_schema(item) for item in items]


@router.post("/country", response_model=PaisRead)
def create_country(data: PaisCreate, db: Session = Depends(get_db)):
    use = CreateCountry(_country_repo(db))
    created = use.execute(_country_in_from_create(data))
    return _country_schema(created)


@router.put("/country/{id}", response_model=PaisRead)
def update_country(id: int, data: PaisUpdate, db: Session = Depends(get_db)):
    repo = _country_repo(db)
    try:
        current = GetCountry(repo).execute(id)
        payload = _country_in_from_update(data, current)
        updated = UpdateCountry(repo).execute(id, payload)
        return _country_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Country not found")


@router.delete("/country/{id}")
def delete_country(id: int, db: Session = Depends(get_db)):
    repo = _country_repo(db)
    try:
        DeleteCountry(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"ok": True}


# Timezones (CRUD simple)
@router.get("/timezone")
def list_timezones(db: Session = Depends(get_db)):
    use = ListTimezones(_timezones_repo(db))
    items = use.execute()
    return [_timezones_schema(item) for item in items]


@router.post("/timezone")
def create_timezone(data: dict, db: Session = Depends(get_db)):
    use = CreateTimezone(_timezones_repo(db))
    created = use.execute(_timezones_in_from_create(data))
    return _timezones_schema(created)


@router.put("/timezone/{name}")
def update_timezone(name: str, data: dict, db: Session = Depends(get_db)):
    repo = _timezones_repo(db)
    try:
        current = GetTimezone(repo).execute(name)
        payload = _timezones_in_from_update(data, current)
        updated = UpdateTimezone(repo).execute(name, payload)
        return _timezones_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Timezone no encontrado")


@router.delete("/timezone/{name}")
def delete_timezone(name: str, db: Session = Depends(get_db)):
    repo = _timezones_repo(db)
    try:
        DeleteTimezone(repo).execute(name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Timezone no encontrado")
    return {"ok": True}


# Locales (CRUD simple)
@router.get("/locale")
def list_locales(db: Session = Depends(get_db)):
    use = ListLocales(_locales_repo(db))
    items = use.execute()
    return [_locales_schema(item) for item in items]


@router.post("/locale")
def create_locale(data: dict, db: Session = Depends(get_db)):
    use = CreateLocale(_locales_repo(db))
    created = use.execute(_locales_in_from_create(data))
    return _locales_schema(created)


@router.put("/locale/{code}")
def update_locale(code: str, data: dict, db: Session = Depends(get_db)):
    repo = _locales_repo(db)
    try:
        current = GetLocale(repo).execute(code)
        payload = _locales_in_from_update(data, current)
        updated = UpdateLocale(repo).execute(code, payload)
        return _locales_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Locale no encontrado")


@router.delete("/locale/{code}")
def delete_locale(code: str, db: Session = Depends(get_db)):
    repo = _locales_repo(db)
    try:
        DeleteLocale(repo).execute(code)
    except ValueError:
        raise HTTPException(status_code=404, detail="Locale no encontrado")
    return {"ok": True}


# Weekdays
@router.get("/weekday", response_model=list[DiaSemanaRead])
def list_weekdays(db: Session = Depends(get_db)):
    use = ListWeekDays(_weekday_repo(db))
    items = use.execute()
    return [_weekday_schema(item) for item in items]


@router.post("/weekday", response_model=DiaSemanaRead)
def create_weekday(data: DiaSemanaCreate, db: Session = Depends(get_db)):
    use = CreateWeekDay(_weekday_repo(db))
    created = use.execute(_weekday_in_from_create(data))
    return _weekday_schema(created)


@router.put("/weekday/{id}", response_model=DiaSemanaRead)
def update_weekday(id: int, data: DiaSemanaUpdate, db: Session = Depends(get_db)):
    repo = _weekday_repo(db)
    try:
        current = GetWeekDay(repo).execute(id)
        payload = _weekday_in_from_update(data, current)
        updated = UpdateWeekDay(repo).execute(id, payload)
        return _weekday_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Weekday not found")


@router.delete("/weekday/{id}")
def delete_weekday(id: int, db: Session = Depends(get_db)):
    repo = _weekday_repo(db)
    try:
        DeleteWeekDay(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Weekday not found")
    return {"ok": True}


# Attention Schedules
@router.get("/attention-schedule", response_model=list[HorarioAtencionRead])
def list_attention_schedules(db: Session = Depends(get_db)):
    use = ListAttentionSchedules(_attention_schedule_repo(db))
    items = use.execute()
    return [_attention_schedule_schema(item) for item in items]


@router.post("/attention-schedule", response_model=HorarioAtencionRead)
def create_attention_schedule(data: HorarioAtencionCreate, db: Session = Depends(get_db)):
    use = CreateAttentionSchedule(_attention_schedule_repo(db))
    created = use.execute(_attention_schedule_in_from_create(data))
    return _attention_schedule_schema(created)


@router.put("/attention-schedule/{id}", response_model=HorarioAtencionRead)
def update_attention_schedule(id: int, data: HorarioAtencionUpdate, db: Session = Depends(get_db)):
    repo = _attention_schedule_repo(db)
    try:
        current = GetAttentionSchedule(repo).execute(id)
        payload = _attention_schedule_in_from_update(data, current)
        updated = UpdateAttentionSchedule(repo).execute(id, payload)
        return _attention_schedule_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Attention schedule not found")


@router.delete("/attention-schedule/{id}")
def delete_attention_schedule(id: int, db: Session = Depends(get_db)):
    repo = _attention_schedule_repo(db)
    try:
        DeleteAttentionSchedule(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Attention schedule not found")
    return {"ok": True}


# Template Sectors
@router.get("/template-sector", response_model=list[SectorPlantillaRead])
def list_template_sectors(db: Session = Depends(get_db)):
    use = ListTemplateSectors(_template_sector_repo(db))
    items = use.execute()
    return [_template_sector_schema(item) for item in items]


@router.post("/template-sector", response_model=SectorPlantillaRead)
def create_template_sector(data: SectorPlantillaCreate, db: Session = Depends(get_db)):
    use = CreateTemplateSector(_template_sector_repo(db))
    created = use.execute(_template_sector_in_from_create(data))
    return _template_sector_schema(created)


@router.get("/template-sector/{id}", response_model=SectorPlantillaRead)
def get_template_sector(id: UUID, db: Session = Depends(get_db)):
    use = GetTemplateSector(_template_sector_repo(db))
    try:
        sector = use.execute(id)
        return _template_sector_schema(sector)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template sector not found")


@router.put("/template-sector/{id}", response_model=SectorPlantillaRead)
def update_template_sector(id: UUID, data: SectorPlantillaUpdate, db: Session = Depends(get_db)):
    repo = _template_sector_repo(db)
    try:
        current = GetTemplateSector(repo).execute(id)
        payload = _template_sector_in_from_update(data, current)
        updated = UpdateTemplateSector(repo).execute(id, payload)
        return _template_sector_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template sector not found")


@router.delete("/template-sector/{id}")
def delete_template_sector(id: UUID, db: Session = Depends(get_db)):
    repo = _template_sector_repo(db)
    try:
        DeleteTemplateSector(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template sector not found")
    return {"ok": True}


# Business Types (Company)
@router.get("/business-type", response_model=list[TipoEmpresaRead])
def list_business_types(db: Session = Depends(get_db)):
    use = ListCompanyTypes(_business_type_repo(db))
    items = use.execute()
    return [_business_type_schema(item) for item in items]


@router.post("/business-type", response_model=TipoEmpresaRead)
def create_business_type(data: TipoEmpresaCreate, db: Session = Depends(get_db)):
    use = CreateCompanyType(_business_type_repo(db))
    created = use.execute(_business_type_in_from_create(data))
    return _business_type_schema(created)


@router.put("/business-type/{id}", response_model=TipoEmpresaRead)
def update_business_type(id: str, data: TipoEmpresaUpdate, db: Session = Depends(get_db)):
    from uuid import UUID as _UUID

    try:
        uid = _UUID(id)
    except ValueError:
        uid = id
    repo = _business_type_repo(db)
    try:
        current = GetCompanyType(repo).execute(uid)
        payload = _business_type_in_from_update(data, current)
        updated = UpdateCompanyType(repo).execute(uid, payload)
        return _business_type_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Business type not found")


@router.delete("/business-type/{id}")
def delete_business_type(id: str, db: Session = Depends(get_db)):
    from uuid import UUID as _UUID

    try:
        uid = _UUID(id)
    except ValueError:
        uid = id
    repo = _business_type_repo(db)
    try:
        DeleteCompanyType(repo).execute(uid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Business type not found")
    return {"ok": True}


# Business Categories
@router.get("/business-category", response_model=list[TipoNegocioRead])
def list_business_categories(db: Session = Depends(get_db)):
    use = ListBusinessTypes(_business_category_repo(db))
    items = use.execute()
    return [_business_category_schema(item) for item in items]

# --------------------------------------------------------------------
# Spanish aliases (compat) for frontend expecting legacy paths
# --------------------------------------------------------------------


@router.get("/tipo-empresa", response_model=list[TipoEmpresaRead])
def list_business_types_es(db: Session = Depends(get_db)):
    return list_business_types(db)


@router.get("/tipo-negocio", response_model=list[TipoNegocioRead])
def list_business_categories_es(db: Session = Depends(get_db)):
    return list_business_categories(db)


@router.get("/sectores", response_model=list[SectorPlantillaRead])
def list_template_sectors_es(db: Session = Depends(get_db)):
    return list_template_sectors(db)


@router.post("/business-category", response_model=TipoNegocioRead)
def create_business_category(data: TipoNegocioCreate, db: Session = Depends(get_db)):
    use = CreateBusinessType(_business_category_repo(db))
    created = use.execute(_business_category_in_from_create(data))
    return _business_category_schema(created)


@router.put("/business-category/{id}", response_model=TipoNegocioRead)
def update_business_category(id: UUID, data: TipoNegocioUpdate, db: Session = Depends(get_db)):
    repo = _business_category_repo(db)
    try:
        current = GetBusinessType(repo).execute(id)
        payload = _business_category_in_from_update(data, current)
        updated = UpdateBusinessType(repo).execute(id, payload)
        return _business_category_schema(updated)
    except ValueError:
        raise HTTPException(status_code=404, detail="Business category not found")


@router.delete("/business-category/{id}")
def delete_business_category(id: UUID, db: Session = Depends(get_db)):
    repo = _business_category_repo(db)
    try:
        DeleteBusinessType(repo).execute(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Business category not found")
    return {"ok": True}
