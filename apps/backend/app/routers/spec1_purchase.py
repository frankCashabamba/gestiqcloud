"""
Router: Purchase - Compras a proveedores
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
from app.models.spec1.purchase import Purchase
from app.schemas.spec1.purchase import (
    PurchaseCreate,
    PurchaseUpdate,
    PurchaseResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("/", response_model=List[PurchaseResponse])
def list_purchases(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    supplier_name: Optional[str] = Query(None),
    product_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Listar compras con filtros"""
    query = db.query(Purchase).filter(Purchase.tenant_id == tenant_id)
    
    if fecha_desde:
        query = query.filter(Purchase.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Purchase.fecha <= fecha_hasta)
    if supplier_name:
        query = query.filter(Purchase.supplier_name.ilike(f"%{supplier_name}%"))
    if product_id:
        query = query.filter(Purchase.product_id == product_id)
    
    query = query.order_by(Purchase.fecha.desc(), Purchase.created_at.desc())
    results = query.offset(skip).limit(limit).all()
    
    return results


@router.get("/{purchase_id}", response_model=PurchaseResponse)
def get_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Obtener compra por ID"""
    purchase = (
        db.query(Purchase)
        .filter(
            and_(
                Purchase.id == purchase_id,
                Purchase.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    return purchase


@router.post("/", response_model=PurchaseResponse, status_code=201)
def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Crear compra"""
    purchase = Purchase(
        tenant_id=tenant_id,
        **data.model_dump(exclude_unset=True),
        created_at=date.today(),
    )
    
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    
    logger.info(f"Compra creada: {purchase.id} - {purchase.supplier_name}")
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseResponse)
def update_purchase(
    purchase_id: UUID,
    data: PurchaseUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Actualizar compra"""
    purchase = (
        db.query(Purchase)
        .filter(
            and_(
                Purchase.id == purchase_id,
                Purchase.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(purchase, key, value)
    
    db.commit()
    db.refresh(purchase)
    
    logger.info(f"Compra actualizada: {purchase.id}")
    return purchase


@router.delete("/{purchase_id}", status_code=204)
def delete_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Eliminar compra"""
    purchase = (
        db.query(Purchase)
        .filter(
            and_(
                Purchase.id == purchase_id,
                Purchase.tenant_id == tenant_id,
            )
        )
        .first()
    )
    
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    db.delete(purchase)
    db.commit()
    
    logger.info(f"Compra eliminada: {purchase_id}")
    return None


@router.get("/stats/summary")
def get_purchases_summary(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    supplier_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Resumen de compras (KPIs)"""
    from sqlalchemy import func
    
    query = db.query(
        func.count(Purchase.id).label("total_compras"),
        func.sum(Purchase.cantidad).label("total_cantidad"),
        func.sum(Purchase.total).label("total_costo"),
        func.avg(Purchase.costo_unitario).label("costo_promedio"),
    ).filter(Purchase.tenant_id == tenant_id)
    
    if fecha_desde:
        query = query.filter(Purchase.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Purchase.fecha <= fecha_hasta)
    if supplier_name:
        query = query.filter(Purchase.supplier_name.ilike(f"%{supplier_name}%"))
    
    result = query.first()
    
    return {
        "total_compras": result.total_compras or 0,
        "total_cantidad": float(result.total_cantidad or 0),
        "total_costo": float(result.total_costo or 0),
        "costo_promedio": float(result.costo_promedio or 0),
    }
