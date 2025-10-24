"""
Router: Milk Record - Registro de leche
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from datetime import date
from typing import List, Optional
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.models.spec1.milk_record import MilkRecord
from app.schemas.spec1.milk_record import (
    MilkRecordCreate,
    MilkRecordUpdate,
    MilkRecordResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/milk-records", tags=["milk-records"])


@router.get("/", response_model=List[MilkRecordResponse])
def list_milk_records(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Listar registros de leche con filtros"""
    query = db.query(MilkRecord).filter(MilkRecord.tenant_id == tenant_id)
    
    if fecha_desde:
        query = query.filter(MilkRecord.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(MilkRecord.fecha <= fecha_hasta)
    
    query = query.order_by(MilkRecord.fecha.desc(), MilkRecord.created_at.desc())
    results = query.offset(skip).limit(limit).all()
    
    return results


@router.get("/{record_id}", response_model=MilkRecordResponse)
def get_milk_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Obtener registro de leche por ID"""
    record = (
        db.query(MilkRecord)
        .filter(
            and_(
                MilkRecord.id == record_id,
                MilkRecord.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    return record


@router.post("/", response_model=MilkRecordResponse, status_code=201)
def create_milk_record(
    data: MilkRecordCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Crear registro de leche"""
    record = MilkRecord(
        tenant_id=tenant_id,
        **data.model_dump(exclude_unset=True),
        created_at=date.today(),
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)
    
    logger.info(f"Registro de leche creado: {record.id} - {record.litros}L")
    return record


@router.put("/{record_id}", response_model=MilkRecordResponse)
def update_milk_record(
    record_id: UUID,
    data: MilkRecordUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Actualizar registro de leche"""
    record = (
        db.query(MilkRecord)
        .filter(
            and_(
                MilkRecord.id == record_id,
                MilkRecord.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    
    db.commit()
    db.refresh(record)
    
    logger.info(f"Registro de leche actualizado: {record.id}")
    return record


@router.delete("/{record_id}", status_code=204)
def delete_milk_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Eliminar registro de leche"""
    record = (
        db.query(MilkRecord)
        .filter(
            and_(
                MilkRecord.id == record_id,
                MilkRecord.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not record:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    db.delete(record)
    db.commit()
    
    logger.info(f"Registro de leche eliminado: {record_id}")
    return None


@router.get("/stats/summary")
def get_milk_summary(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Resumen de registros de leche (KPIs)"""
    from sqlalchemy import func
    
    query = db.query(
        func.count(MilkRecord.id).label("total_registros"),
        func.sum(MilkRecord.litros).label("total_litros"),
        func.avg(MilkRecord.litros).label("promedio_litros_dia"),
        func.avg(MilkRecord.grasa_pct).label("promedio_grasa"),
    ).filter(MilkRecord.tenant_id == tenant_id)
    
    if fecha_desde:
        query = query.filter(MilkRecord.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(MilkRecord.fecha <= fecha_hasta)
    
    result = query.first()
    
    return {
        "total_registros": result.total_registros or 0,
        "total_litros": float(result.total_litros or 0),
        "promedio_litros_dia": float(result.promedio_litros_dia or 0),
        "promedio_grasa": float(result.promedio_grasa or 0) if result.promedio_grasa else None,
    }
