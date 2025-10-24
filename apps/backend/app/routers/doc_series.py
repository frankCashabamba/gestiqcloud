"""
Router: Doc Series - Numeración documental
Gestión de series de documentos (recibos, facturas, abonos)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from uuid import UUID
from typing import List, Optional
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/doc-series", tags=["doc-series"])


# ============================================================================
# Schemas
# ============================================================================

class DocSeriesCreate(BaseModel):
    register_id: Optional[int] = None
    doc_type: str
    name: str
    current_no: int = 0
    reset_policy: str = "yearly"
    active: bool = True


class DocSeriesUpdate(BaseModel):
    name: Optional[str] = None
    current_no: Optional[int] = None
    reset_policy: Optional[str] = None
    active: Optional[bool] = None


class DocSeriesResponse(BaseModel):
    id: str
    tenant_id: str
    register_id: Optional[int]
    doc_type: str
    name: str
    current_no: int
    reset_policy: str
    active: bool
    created_at: str

    model_config = {"from_attributes": True}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[DocSeriesResponse])
def list_doc_series(
    doc_type: Optional[str] = Query(None),
    register_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Listar series de documentos"""
    query = text("""
        SELECT id, tenant_id, register_id, doc_type, name, current_no, 
               reset_policy, active, created_at
        FROM doc_series
        WHERE tenant_id::text = :tenant_id
    """)
    
    filters = {"tenant_id": str(tenant_id)}
    
    if doc_type:
        query = text(str(query) + " AND doc_type = :doc_type")
        filters["doc_type"] = doc_type
    
    if register_id is not None:
        query = text(str(query) + " AND register_id = :register_id")
        filters["register_id"] = register_id
    
    if active_only:
        query = text(str(query) + " AND active = true")
    
    query = text(str(query) + " ORDER BY doc_type, name")
    
    result = db.execute(query, filters).fetchall()
    
    return [
        DocSeriesResponse(
            id=str(row[0]),
            tenant_id=str(row[1]),
            register_id=row[2],
            doc_type=row[3],
            name=row[4],
            current_no=row[5],
            reset_policy=row[6],
            active=row[7],
            created_at=str(row[8]),
        )
        for row in result
    ]


@router.get("/{series_id}", response_model=DocSeriesResponse)
def get_doc_series(
    series_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Obtener serie por ID"""
    query = text("""
        SELECT id, tenant_id, register_id, doc_type, name, current_no,
               reset_policy, active, created_at
        FROM doc_series
        WHERE id = :series_id AND tenant_id::text = :tenant_id
    """)
    
    row = db.execute(query, {"series_id": str(series_id), "tenant_id": str(tenant_id)}).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    return DocSeriesResponse(
        id=str(row[0]),
        tenant_id=str(row[1]),
        register_id=row[2],
        doc_type=row[3],
        name=row[4],
        current_no=row[5],
        reset_policy=row[6],
        active=row[7],
        created_at=str(row[8]),
    )


@router.post("/", response_model=DocSeriesResponse, status_code=201)
def create_doc_series(
    data: DocSeriesCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Crear nueva serie de documentos"""
    # Verificar que no existe duplicado
    check_query = text("""
        SELECT COUNT(*) FROM doc_series
        WHERE tenant_id::text = :tenant_id
          AND COALESCE(register_id::text, '') = :register_id
          AND doc_type = :doc_type
          AND name = :name
    """)
    
    count = db.execute(
        check_query,
        {
            "tenant_id": str(tenant_id),
            "register_id": str(data.register_id) if data.register_id else "",
            "doc_type": data.doc_type,
            "name": data.name,
        }
    ).scalar()
    
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una serie {data.name} para {data.doc_type}"
        )
    
    # Crear
    insert_query = text("""
        INSERT INTO doc_series (
            tenant_id, register_id, doc_type, name, current_no, reset_policy, active
        )
        VALUES (
            :tenant_id::uuid, :register_id, :doc_type, :name, :current_no, :reset_policy, :active
        )
        RETURNING id, tenant_id, register_id, doc_type, name, current_no, reset_policy, active, created_at
    """)
    
    result = db.execute(
        insert_query,
        {
            "tenant_id": str(tenant_id),
            "register_id": data.register_id,
            "doc_type": data.doc_type,
            "name": data.name,
            "current_no": data.current_no,
            "reset_policy": data.reset_policy,
            "active": data.active,
        }
    ).fetchone()
    
    db.commit()
    
    logger.info(f"Serie creada: {result[0]} - {data.name}")
    
    return DocSeriesResponse(
        id=str(result[0]),
        tenant_id=str(result[1]),
        register_id=result[2],
        doc_type=result[3],
        name=result[4],
        current_no=result[5],
        reset_policy=result[6],
        active=result[7],
        created_at=str(result[8]),
    )


@router.put("/{series_id}", response_model=DocSeriesResponse)
def update_doc_series(
    series_id: UUID,
    data: DocSeriesUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Actualizar serie de documentos"""
    # Construir UPDATE dinámico
    updates = []
    params = {"series_id": str(series_id), "tenant_id": str(tenant_id)}
    
    if data.name is not None:
        updates.append("name = :name")
        params["name"] = data.name
    
    if data.current_no is not None:
        updates.append("current_no = :current_no")
        params["current_no"] = data.current_no
    
    if data.reset_policy is not None:
        updates.append("reset_policy = :reset_policy")
        params["reset_policy"] = data.reset_policy
    
    if data.active is not None:
        updates.append("active = :active")
        params["active"] = data.active
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    update_query = text(f"""
        UPDATE doc_series
        SET {', '.join(updates)}
        WHERE id = :series_id::uuid AND tenant_id::text = :tenant_id
        RETURNING id, tenant_id, register_id, doc_type, name, current_no, reset_policy, active, created_at
    """)
    
    result = db.execute(update_query, params).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    db.commit()
    
    logger.info(f"Serie actualizada: {series_id}")
    
    return DocSeriesResponse(
        id=str(result[0]),
        tenant_id=str(result[1]),
        register_id=result[2],
        doc_type=result[3],
        name=result[4],
        current_no=result[5],
        reset_policy=result[6],
        active=result[7],
        created_at=str(result[8]),
    )


@router.delete("/{series_id}", status_code=204)
def delete_doc_series(
    series_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Eliminar serie de documentos"""
    delete_query = text("""
        DELETE FROM doc_series
        WHERE id = :series_id::uuid AND tenant_id::text = :tenant_id
    """)
    
    result = db.execute(
        delete_query,
        {"series_id": str(series_id), "tenant_id": str(tenant_id)}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    db.commit()
    
    logger.info(f"Serie eliminada: {series_id}")
    return None


@router.post("/{series_id}/reset", response_model=DocSeriesResponse)
def reset_doc_series(
    series_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Resetear contador de serie"""
    update_query = text("""
        UPDATE doc_series
        SET current_no = 0
        WHERE id = :series_id::uuid AND tenant_id::text = :tenant_id
        RETURNING id, tenant_id, register_id, doc_type, name, current_no, reset_policy, active, created_at
    """)
    
    result = db.execute(
        update_query,
        {"series_id": str(series_id), "tenant_id": str(tenant_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    db.commit()
    
    logger.info(f"Serie reseteada: {series_id}")
    
    return DocSeriesResponse(
        id=str(result[0]),
        tenant_id=str(result[1]),
        register_id=result[2],
        doc_type=result[3],
        name=result[4],
        current_no=result[5],
        reset_policy=result[6],
        active=result[7],
        created_at=str(result[8]),
    )
