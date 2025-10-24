"""
Purchase Router - Compras
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
    PurchaseCreate,
    PurchaseUpdate,
    PurchaseResponse
)
from app.models.spec1.purchase import Purchase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/purchases", tags=["spec1-purchases"])


@router.get("/", response_model=List[PurchaseResponse])
def list_purchases(
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    supplier_name: Optional[str] = Query(None, description="Filtrar por proveedor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Listar compras con filtros opcionales"""
    
    try:
        query = db.query(Purchase).filter(
            Purchase.tenant_id == UUID(tenant_id)
        )
        
        if fecha_desde:
            query = query.filter(Purchase.fecha >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(Purchase.fecha <= fecha_hasta)
        
        if supplier_name:
            query = query.filter(
                Purchase.supplier_name.ilike(f"%{supplier_name}%")
            )
        
        query = query.order_by(Purchase.fecha.desc())
        
        items = query.offset(skip).limit(limit).all()
        
        logger.info(f"Listado de compras: {len(items)} items (tenant={tenant_id})")
        
        return items
    
    except Exception as e:
        logger.error(f"Error listando compras: {str(e)}")
        raise HTTPException(500, f"Error al listar compras: {str(e)}")


@router.get("/{id}", response_model=PurchaseResponse)
def get_purchase(
    id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Obtener una compra por ID"""
    
    try:
        item = db.query(Purchase).filter(
            and_(
                Purchase.id == id,
                Purchase.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Compra {id} no encontrada")
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo compra {id}: {str(e)}")
        raise HTTPException(500, f"Error al obtener compra: {str(e)}")


@router.post("/", response_model=PurchaseResponse, status_code=201)
def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva compra"""
    
    try:
        # Calcular total si no viene
        total = data.total
        if total is None:
            total = data.cantidad * data.costo_unitario
        
        new_item = Purchase(
            tenant_id=UUID(tenant_id),
            fecha=data.fecha,
            supplier_name=data.supplier_name,
            product_id=data.product_id,
            cantidad=data.cantidad,
            costo_unitario=data.costo_unitario,
            total=total,
            notas=data.notas,
            created_at=date.today(),
            created_by=UUID(current_user["id"])
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        logger.info(f"Compra creada: {new_item.id} (tenant={tenant_id})")
        
        return new_item
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando compra: {str(e)}")
        raise HTTPException(500, f"Error al crear compra: {str(e)}")


@router.put("/{id}", response_model=PurchaseResponse)
def update_purchase(
    id: UUID,
    data: PurchaseUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Actualizar compra"""
    
    try:
        item = db.query(Purchase).filter(
            and_(
                Purchase.id == id,
                Purchase.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Compra {id} no encontrada")
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(item, field, value)
        
        # Recalcular total si cambiaron cantidad o costo
        if 'cantidad' in update_data or 'costo_unitario' in update_data:
            if 'total' not in update_data or update_data['total'] is None:
                item.total = item.cantidad * item.costo_unitario
        
        db.commit()
        db.refresh(item)
        
        logger.info(f"Compra actualizada: {id} (tenant={tenant_id})")
        
        return item
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando compra {id}: {str(e)}")
        raise HTTPException(500, f"Error al actualizar compra: {str(e)}")


@router.delete("/{id}", status_code=204)
def delete_purchase(
    id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant)
):
    """Eliminar compra"""
    
    try:
        item = db.query(Purchase).filter(
            and_(
                Purchase.id == id,
                Purchase.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not item:
            raise HTTPException(404, f"Compra {id} no encontrada")
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Compra eliminada: {id} (tenant={tenant_id})")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando compra {id}: {str(e)}")
        raise HTTPException(500, f"Error al eliminar compra: {str(e)}")
