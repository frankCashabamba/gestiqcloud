from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.core.clients import Cliente as ClienteModel
from app.models.tenant import Tenant as TenantModel
from app.middleware.tenant import ensure_tenant


router = APIRouter(prefix="/tenant/clientes", tags=["Clientes (tenant)"])


class ClienteCreate(BaseModel):
    nombre: str
    identificacion: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None


class ClienteOut(ClienteCreate):
    id: int


def _resolve_tenant_info(db: Session, tenant_uuid: str) -> tuple[str, int]:
    tid = tenant_uuid
    row = db.execute(select(TenantModel.empresa_id).where(TenantModel.id == tid)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant desconocido")
    return str(tid), int(row[0])


@router.get("", response_model=List[ClienteOut])
def list_clientes(tenant_uuid: str = Depends(ensure_tenant), db: Session = Depends(get_db)) -> List[ClienteOut]:
    tenant_id, empresa_id = _resolve_tenant_info(db, tenant_uuid)
    res = db.execute(
        select(ClienteModel)
        .where(ClienteModel.tenant_id == tenant_id)
        .order_by(ClienteModel.id.desc())
    )
    return [ClienteOut(**{
        "id": c.id,
        "nombre": c.nombre,
        "identificacion": c.identificacion,
        "email": c.email,
        "telefono": c.telefono,
        "direccion": c.direccion,
        "localidad": c.localidad,
        "provincia": c.provincia,
        "pais": c.pais,
        "codigo_postal": c.codigo_postal,
    }) for (c,) in res.all()]


@router.get("/{cid}", response_model=ClienteOut)
def get_cliente(cid: int, tenant_uuid: str = Depends(ensure_tenant), db: Session = Depends(get_db)) -> ClienteOut:
    tenant_id, empresa_id = _resolve_tenant_info(db, tenant_uuid)
    obj = db.execute(
        select(ClienteModel)
        .where(ClienteModel.id == cid, ClienteModel.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return ClienteOut(
        id=obj.id,
        nombre=obj.nombre,
        identificacion=obj.identificacion,
        email=obj.email,
        telefono=obj.telefono,
        direccion=obj.direccion,
        localidad=obj.localidad,
        provincia=obj.provincia,
        pais=obj.pais,
        codigo_postal=obj.codigo_postal,
    )


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def create_cliente(payload: ClienteCreate, tenant_uuid: str = Depends(ensure_tenant), db: Session = Depends(get_db)) -> ClienteOut:
    tenant_id, empresa_id = _resolve_tenant_info(db, tenant_uuid)
    obj = ClienteModel(
        nombre=payload.nombre,
        identificacion=payload.identificacion,
        email=payload.email,
        telefono=payload.telefono,
        direccion=payload.direccion,
        localidad=payload.localidad,
        provincia=payload.provincia,
        pais=payload.pais,
        codigo_postal=payload.codigo_postal,
        tenant_id=tenant_id,
        empresa_id=empresa_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ClienteOut(
        id=obj.id,
        nombre=obj.nombre,
        identificacion=obj.identificacion,
        email=obj.email,
        telefono=obj.telefono,
        direccion=obj.direccion,
        localidad=obj.localidad,
        provincia=obj.provincia,
        pais=obj.pais,
        codigo_postal=obj.codigo_postal,
    )


@router.put("/{cid}", response_model=ClienteOut)
def update_cliente(cid: int, payload: ClienteCreate, tenant_uuid: str = Depends(ensure_tenant), db: Session = Depends(get_db)) -> ClienteOut:
    tenant_id, empresa_id = _resolve_tenant_info(db, tenant_uuid)
    obj = db.execute(
        select(ClienteModel)
        .where(ClienteModel.id == cid, ClienteModel.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    for field, value in payload.model_dump().items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return ClienteOut(
        id=obj.id,
        nombre=obj.nombre,
        identificacion=obj.identificacion,
        email=obj.email,
        telefono=obj.telefono,
        direccion=obj.direccion,
        localidad=obj.localidad,
        provincia=obj.provincia,
        pais=obj.pais,
        codigo_postal=obj.codigo_postal,
    )


@router.delete("/{cid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(cid: int, tenant_uuid: str = Depends(ensure_tenant), db: Session = Depends(get_db)) -> None:
    tenant_id, _ = _resolve_tenant_info(db, tenant_uuid)
    obj = db.execute(
        select(ClienteModel)
        .where(ClienteModel.id == cid, ClienteModel.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    db.delete(obj)
    db.commit()
    return None
