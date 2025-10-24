"""
Daily Inventory Router - Inventario diario
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from uuid import UUID
from datetime import date, datetime
from typing import List, Optional
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant, get_current_user
from app.schemas.spec1 import (
    DailyInventoryCreate,
    DailyInventoryUpdate,
    DailyInventoryResponse
)
from app.models.spec1.daily_inventory import DailyInventory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/daily-inventory", tags=["spec1-daily-inventory"])


@router.get("/", response_model=List[DailyInventoryResponse])
def list_daily_inventory(
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    product_id: Optional[UUID] = Query(None, description="Filtrar por producto"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Listar inventario diario con filtros opcionales"""
    
    try:
        query = db.query(DailyInventory).filter(
            DailyInventory.tenant_id == UUID(tenant_id)
        )
        
        if fecha_desde:
            query = query.filter(DailyInventory.fecha >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(DailyInventory.fecha <= fecha_hasta)
        
        if product_id:
            query = query.filter(DailyInventory.product_id == product_id)
        
        query = query.order_by(DailyInventory.fecha.desc())
        
        items = query.offset(skip).limit(limit).all()
        
        logger.info(f"Listado de inventario diario: {len(items)} items (tenant={tenant_id})")
        
        return items
    
    except Exception as e:
        logger.error(f"Error listando inventario diario: {str(e)}")
        raise HTTPException(500, f"Error al listar inventario: {str(e)}")


@router.get("/{id}", response_model=DailyInventoryResponse)
def get_daily_inventory(
    id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Obtener un registro de inventario diario por ID"""
    
    try:
        item = db.query(DailyInventory).filter(
            and_(
                DailyInventory.id == id,
                DailyInventory.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Inventario diario {id} no encontrado")
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo inventario diario {id}: {str(e)}")
        raise HTTPException(500, f"Error al obtener inventario: {str(e)}")


@router.post("/", response_model=DailyInventoryResponse, status_code=201)
def create_daily_inventory(
    data: DailyInventoryCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo registro de inventario diario"""
    
    try:
        # Verificar duplicados (mismo tenant + producto + fecha)
        existing = db.query(DailyInventory).filter(
            and_(
                DailyInventory.tenant_id == UUID(tenant_id),
                DailyInventory.product_id == data.product_id,
                DailyInventory.fecha == data.fecha
            )
        ).first()
        
        if existing:
            raise HTTPException(
                400,
                f"Ya existe un registro de inventario para este producto en la fecha {data.fecha}"
            )
        
        new_item = DailyInventory(
            tenant_id=UUID(tenant_id),
            product_id=data.product_id,
            fecha=data.fecha,
            stock_inicial=data.stock_inicial,
            venta_unidades=data.venta_unidades,
            stock_final=data.stock_final,
            ajuste=data.ajuste,
            precio_unitario_venta=data.precio_unitario_venta,
            importe_total=data.importe_total,
            created_at=date.today(),
            created_by=UUID(current_user["id"])
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        logger.info(f"Inventario diario creado: {new_item.id} (tenant={tenant_id})")
        
        return new_item
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando inventario diario: {str(e)}")
        raise HTTPException(500, f"Error al crear inventario: {str(e)}")


@router.put("/{id}", response_model=DailyInventoryResponse)
def update_daily_inventory(
    id: UUID,
    data: DailyInventoryUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Actualizar registro de inventario diario"""
    
    try:
        item = db.query(DailyInventory).filter(
            and_(
                DailyInventory.id == id,
                DailyInventory.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Inventario diario {id} no encontrado")
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(item, field, value)
        
        db.commit()
        db.refresh(item)
        
        logger.info(f"Inventario diario actualizado: {id} (tenant={tenant_id})")
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando inventario diario {id}: {str(e)}")
        raise HTTPException(500, f"Error al actualizar inventario: {str(e)}")


@router.delete("/{id}", status_code=204)
def delete_daily_inventory(
    id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Eliminar registro de inventario diario"""
    
    try:
        item = db.query(DailyInventory).filter(
            and_(
                DailyInventory.id == id,
                DailyInventory.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Inventario diario {id} no encontrado")
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Inventario diario eliminado: {id} (tenant={tenant_id})")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando inventario diario {id}: {str(e)}")
        raise HTTPException(500, f"Error al eliminar inventario: {str(e)}")
