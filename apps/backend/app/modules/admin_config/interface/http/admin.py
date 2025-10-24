from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db

# Reuse legacy CRUD and schemas to avoid duplicating models while migrating
from app.modules.admin_config.crud import (
    idioma_crud,
    moneda_crud,
    diasemana_crud,
    horarioatencion_crud,
    sectorplantilla_crud,
    tipo_empresa_crud,
    tipo_negocio_crud,
)
from app.modules.admin_config.schemas import (
    HorarioAtencionCreate, HorarioAtencionUpdate, HorarioAtencionRead,
    MonedaCreate, MonedaUpdate, MonedaRead,
    DiaSemanaCreate, DiaSemanaUpdate, DiaSemanaRead,
    IdiomaCreate, IdiomaUpdate, IdiomaRead,
    SectorPlantillaCreate, SectorPlantillaUpdate, SectorPlantillaRead,
    TipoEmpresaRead, TipoEmpresaCreate, TipoEmpresaUpdate,
    TipoNegocioRead, TipoNegocioCreate, TipoNegocioUpdate,
)


router = APIRouter(prefix="/config", tags=["admin:config"])


# Idiomas
@router.get("/idioma", response_model=List[IdiomaRead])
def list_idiomas(db: Session = Depends(get_db)):
    return idioma_crud.get_multi(db)


@router.post("/idioma", response_model=IdiomaRead)
def create_idioma(data: IdiomaCreate, db: Session = Depends(get_db)):
    return idioma_crud.create(db, data)


@router.put("/idioma/{id}", response_model=IdiomaRead)
def update_idioma(id: int, data: IdiomaUpdate, db: Session = Depends(get_db)):
    obj = idioma_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Idioma no encontrado")
    return idioma_crud.update(db, obj, data)


@router.delete("/idioma/{id}")
def delete_idioma(id: int, db: Session = Depends(get_db)):
    obj = idioma_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Idioma no encontrado")
    idioma_crud.remove(db, id)
    return {"ok": True}


# Monedas
@router.get("/moneda", response_model=List[MonedaRead])
def list_monedas(db: Session = Depends(get_db)):
    return moneda_crud.get_multi(db)


@router.post("/moneda", response_model=MonedaRead)
def create_moneda(data: MonedaCreate, db: Session = Depends(get_db)):
    return moneda_crud.create(db, data)


@router.put("/moneda/{id}", response_model=MonedaRead)
def update_moneda(id: int, data: MonedaUpdate, db: Session = Depends(get_db)):
    obj = moneda_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Moneda no encontrada")
    return moneda_crud.update(db, obj, data)


@router.delete("/moneda/{id}")
def delete_moneda(id: int, db: Session = Depends(get_db)):
    obj = moneda_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Moneda no encontrada")
    moneda_crud.remove(db, id)
    return {"ok": True}


# Días de semana (ruta moderna `/dias`)
@router.get("/dias", response_model=List[DiaSemanaRead])
def list_dias(db: Session = Depends(get_db)):
    return diasemana_crud.get_multi(db)


@router.post("/dias", response_model=DiaSemanaRead)
def create_dia(data: DiaSemanaCreate, db: Session = Depends(get_db)):
    return diasemana_crud.create(db, data)


@router.put("/dias/{id}", response_model=DiaSemanaRead)
def update_dia(id: int, data: DiaSemanaUpdate, db: Session = Depends(get_db)):
    obj = diasemana_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Día no encontrado")
    return diasemana_crud.update(db, obj, data)


@router.delete("/dias/{id}")
def delete_dia(id: int, db: Session = Depends(get_db)):
    obj = diasemana_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Día no encontrado")
    diasemana_crud.remove(db, id)
    return {"ok": True}


# Horario de atención (ruta moderna `/horario_atencion`)
@router.get("/horario_atencion", response_model=List[HorarioAtencionRead])
def list_horarios(db: Session = Depends(get_db)):
    return horarioatencion_crud.get_multi(db)


@router.post("/horario_atencion", response_model=HorarioAtencionRead)
def create_horario(data: HorarioAtencionCreate, db: Session = Depends(get_db)):
    return horarioatencion_crud.create(db, data)


@router.put("/horario_atencion/{id}", response_model=HorarioAtencionRead)
def update_horario(id: int, data: HorarioAtencionUpdate, db: Session = Depends(get_db)):
    obj = horarioatencion_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    return horarioatencion_crud.update(db, obj, data)


@router.delete("/horario_atencion/{id}")
def delete_horario(id: int, db: Session = Depends(get_db)):
    obj = horarioatencion_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Horario no encontrado")
    horarioatencion_crud.remove(db, id)
    return {"ok": True}


# Sectores (plantillas)
@router.get("/sectores", response_model=List[SectorPlantillaRead])
def list_sectores(db: Session = Depends(get_db)):
    return sectorplantilla_crud.get_multi(db)


@router.post("/sectores", response_model=SectorPlantillaRead)
def create_sector(data: SectorPlantillaCreate, db: Session = Depends(get_db)):
    return sectorplantilla_crud.create(db, data)


@router.put("/sectores/{id}", response_model=SectorPlantillaRead)
def update_sector(id: int, data: SectorPlantillaUpdate, db: Session = Depends(get_db)):
    obj = sectorplantilla_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Sector no encontrado")
    return sectorplantilla_crud.update(db, obj, data)


@router.delete("/sectores/{id}")
def delete_sector(id: int, db: Session = Depends(get_db)):
    obj = sectorplantilla_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Sector no encontrado")
    sectorplantilla_crud.remove(db, id)
    return {"ok": True}


# Tipo empresa
@router.get("/tipo-empresa", response_model=List[TipoEmpresaRead])
def list_tipo_empresa(db: Session = Depends(get_db)):
    return tipo_empresa_crud.get_multi(db)


@router.post("/tipo-empresa", response_model=TipoEmpresaRead)
def create_tipo_empresa(data: TipoEmpresaCreate, db: Session = Depends(get_db)):
    return tipo_empresa_crud.create(db, data)


@router.put("/tipo-empresa/{id}", response_model=TipoEmpresaRead)
def update_tipo_empresa(id: int, data: TipoEmpresaUpdate, db: Session = Depends(get_db)):
    obj = tipo_empresa_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tipo de empresa no encontrado")
    return tipo_empresa_crud.update(db, obj, data)


@router.delete("/tipo-empresa/{id}")
def delete_tipo_empresa(id: int, db: Session = Depends(get_db)):
    obj = tipo_empresa_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="No encontrado")
    tipo_empresa_crud.remove(db, id)
    return {"ok": True}


# Tipo negocio
@router.get("/tipo-negocio", response_model=List[TipoNegocioRead])
def list_tipo_negocio(db: Session = Depends(get_db)):
    return tipo_negocio_crud.get_multi(db)


@router.post("/tipo-negocio", response_model=TipoNegocioRead)
def create_tipo_negocio(data: TipoNegocioCreate, db: Session = Depends(get_db)):
    return tipo_negocio_crud.create(db, data)


@router.put("/tipo-negocio/{id}", response_model=TipoNegocioRead)
def update_tipo_negocio(id: int, data: TipoNegocioUpdate, db: Session = Depends(get_db)):
    obj = tipo_negocio_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Tipo de negocio no encontrado")
    return tipo_negocio_crud.update(db, obj, data)


@router.delete("/tipo-negocio/{id}")
def delete_tipo_negocio(id: int, db: Session = Depends(get_db)):
    obj = tipo_negocio_crud.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="No encontrado")
    tipo_negocio_crud.remove(db, id)
    return {"ok": True}
