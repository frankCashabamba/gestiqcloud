"""
Router: Daily Inventory - Inventario diario por producto
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from uuid import UUID
from datetime import date
from typing import List, Optional
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.models.spec1.daily_inventory import DailyInventory
from app.schemas.spec1.daily_inventory import (
    DailyInventoryCreate,
    DailyInventoryUpdate,
    DailyInventoryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/daily-inventory", tags=["daily-inventory"])


@router.get("/", response_model=List[DailyInventoryResponse])
def list_daily_inventory(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    product_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Listar inventario diario con filtros"""
    query = db.query(DailyInventory).filter(DailyInventory.tenant_id == tenant_id)
    
    if fecha_desde:
        query = query.filter(DailyInventory.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(DailyInventory.fecha <= fecha_hasta)
    if product_id:
        query = query.filter(DailyInventory.product_id == product_id)
    
    query = query.order_by(DailyInventory.fecha.desc(), DailyInventory.created_at.desc())
    results = query.offset(skip).limit(limit).all()
    
    return results


@router.get("/{inventory_id}", response_model=DailyInventoryResponse)
def get_daily_inventory(
    inventory_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Obtener inventario diario por ID"""
    inventory = (
        db.query(DailyInventory)
        .filter(
            and_(
                DailyInventory.id == inventory_id,
                DailyInventory.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventario no encontrado")
    
    return inventory


@router.post("/", response_model=DailyInventoryResponse, status_code=201)
def create_daily_inventory(
    data: DailyInventoryCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Crear inventario diario (upsert por fecha+producto)"""
    # Verificar si ya existe para ese producto y fecha
    existing = (
        db.query(DailyInventory)
        .filter(
            and_(
                DailyInventory.tenant_id == tenant_id,
                DailyInventory.product_id == data.product_id,
                DailyInventory.fecha == data.fecha,
            )
        )
        .first()
    )
    
    if existing:
        # Actualizar existente
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        
        db.commit()
        db.refresh(existing)
        logger.info(f"Inventario actualizado: {existing.id}")
        return existing
    
    # Crear nuevo
    inventory = DailyInventory(
        tenant_id=tenant_id,
        **data.model_dump(exclude_unset=True),
        created_at=date.today(),
    )
    
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    
    logger.info(f"Inventario creado: {inventory.id}")
    return inventory


@router.put("/{inventory_id}", response_model=DailyInventoryResponse)
def update_daily_inventory(
    inventory_id: UUID,
    data: DailyInventoryUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Actualizar inventario diario"""
    inventory = (
        db.query(DailyInventory)
        .filter(
            and_(
                DailyInventory.id == inventory_id,
                DailyInventory.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventario no encontrado")
    
    # Actualizar campos
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(inventory, key, value)
    
    db.commit()
    db.refresh(inventory)
    
    logger.info(f"Inventario actualizado: {inventory.id}")
    return inventory


@router.delete("/{inventory_id}", status_code=204)
def delete_daily_inventory(
    inventory_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Eliminar inventario diario"""
    inventory = (
        db.query(DailyInventory)
        .filter(
            and_(
                DailyInventory.id == inventory_id,
                DailyInventory.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventario no encontrado")
    
    db.delete(inventory)
    db.commit()
    
    logger.info(f"Inventario eliminado: {inventory_id}")
    return None


@router.get("/stats/summary")
def get_inventory_summary(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Resumen de inventario (KPIs)"""
    query = db.query(
        text("""
            SELECT 
                COUNT(*) as total_registros,
                SUM(venta_unidades) as total_ventas_unidades,
                SUM(importe_total) as total_ingresos,
                SUM(CASE WHEN ajuste != 0 THEN 1 ELSE 0 END) as registros_con_ajuste,
                AVG(CASE WHEN precio_unitario_venta > 0 THEN precio_unitario_venta END) as precio_promedio
            FROM daily_inventory
            WHERE tenant_id::text = :tenant_id
        """)
    ).params(tenant_id=str(tenant_id))
    
    if fecha_desde:
        query = query.filter(text("fecha >= :fecha_desde")).params(fecha_desde=fecha_desde)
    if fecha_hasta:
        query = query.filter(text("fecha <= :fecha_hasta")).params(fecha_hasta=fecha_hasta)
    
    result = db.execute(query).first()
    
    return {
        "total_registros": result[0] or 0,
        "total_ventas_unidades": float(result[1] or 0),
        "total_ingresos": float(result[2] or 0),
        "registros_con_ajuste": result[3] or 0,
        "precio_promedio": float(result[4] or 0),
    }
