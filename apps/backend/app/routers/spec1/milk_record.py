"""
Milk Record Router - Registros de leche
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from datetime import date
from typing import List, Optional
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant, get_current_user
from app.schemas.spec1 import (
    MilkRecordCreate,
    MilkRecordUpdate,
    MilkRecordResponse
)
from app.models.spec1.milk_record import MilkRecord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/milk-records", tags=["spec1-milk-records"])


@router.get("/", response_model=List[MilkRecordResponse])
def list_milk_records(
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Listar registros de leche con filtros opcionales"""
    
    try:
        query = db.query(MilkRecord).filter(
            MilkRecord.tenant_id == UUID(tenant_id)
        )
        
        if fecha_desde:
            query = query.filter(MilkRecord.fecha >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(MilkRecord.fecha <= fecha_hasta)
        
        query = query.order_by(MilkRecord.fecha.desc())
        
        items = query.offset(skip).limit(limit).all()
        
        logger.info(f"Listado de registros de leche: {len(items)} items (tenant={tenant_id})")
        
        return items
    
    except Exception as e:
        logger.error(f"Error listando registros de leche: {str(e)}")
        raise HTTPException(500, f"Error al listar registros: {str(e)}")


@router.get("/{id}", response_model=MilkRecordResponse)
def get_milk_record(
    id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Obtener un registro de leche por ID"""
    
    try:
        item = db.query(MilkRecord).filter(
            and_(
                MilkRecord.id == id,
                MilkRecord.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Registro de leche {id} no encontrado")
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo registro de leche {id}: {str(e)}")
        raise HTTPException(500, f"Error al obtener registro: {str(e)}")


@router.post("/", response_model=MilkRecordResponse, status_code=201)
def create_milk_record(
    data: MilkRecordCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo registro de leche"""
    
    try:
        # Verificar duplicados (mismo tenant + fecha)
        existing = db.query(MilkRecord).filter(
            and_(
                MilkRecord.tenant_id == UUID(tenant_id),
                MilkRecord.fecha == data.fecha
            )
        ).first()
        
        if existing:
            raise HTTPException(
                400,
                f"Ya existe un registro de leche para la fecha {data.fecha}"
            )
        
        new_item = MilkRecord(
            tenant_id=UUID(tenant_id),
            fecha=data.fecha,
            litros=data.litros,
            grasa_pct=data.grasa_pct,
            notas=data.notas,
            created_at=date.today(),
            created_by=UUID(current_user["id"])
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        logger.info(f"Registro de leche creado: {new_item.id} (tenant={tenant_id})")
        
        return new_item
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando registro de leche: {str(e)}")
        raise HTTPException(500, f"Error al crear registro: {str(e)}")


@router.put("/{id}", response_model=MilkRecordResponse)
def update_milk_record(
    id: UUID,
    data: MilkRecordUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Actualizar registro de leche"""
    
    try:
        item = db.query(MilkRecord).filter(
            and_(
                MilkRecord.id == id,
                MilkRecord.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Registro de leche {id} no encontrado")
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(item, field, value)
        
        db.commit()
        db.refresh(item)
        
        logger.info(f"Registro de leche actualizado: {id} (tenant={tenant_id})")
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando registro de leche {id}: {str(e)}")
        raise HTTPException(500, f"Error al actualizar registro: {str(e)}")


@router.delete("/{id}", status_code=204)
def delete_milk_record(
    id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Eliminar registro de leche"""
    
    try:
        item = db.query(MilkRecord).filter(
            and_(
                MilkRecord.id == id,
                MilkRecord.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Registro de leche {id} no encontrado")
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Registro de leche eliminado: {id} (tenant={tenant_id})")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando registro de leche {id}: {str(e)}")
        raise HTTPException(500, f"Error al eliminar registro: {str(e)}")
