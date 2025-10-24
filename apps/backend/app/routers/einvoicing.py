"""
Router: E-invoicing - Facturación electrónica (ES + EC)
Endpoints REST completos para gestión de e-factura
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from typing import Optional
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/einvoicing", tags=["einvoicing"])


# ============================================================================
# Schemas
# ============================================================================

class EinvoicingSendRequest(BaseModel):
    invoice_id: UUID
    country: str  # 'ES' or 'EC'


class EinvoicingStatusResponse(BaseModel):
    invoice_id: str
    country: str
    status: str
    clave_acceso: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: Optional[str] = None


class CredentialsRequest(BaseModel):
    country: str
    cert_password: Optional[str] = None
    sandbox: bool = False


class CredentialsResponse(BaseModel):
    country: str
    has_certificate: bool
    sandbox: bool
    last_updated: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/send")
async def send_einvoice(
    request: EinvoicingSendRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """
    Enviar factura electrónica (ES SII o EC SRI)
    Inicia tarea Celery asíncrona
    """
    # Verificar que la factura existe
    check_query = text("""
        SELECT id FROM invoices
        WHERE id = :invoice_id::uuid AND tenant_id::text = :tenant_id
    """)
    
    invoice = db.execute(
        check_query,
        {"invoice_id": str(request.invoice_id), "tenant_id": str(tenant_id)}
    ).fetchone()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # Iniciar tarea Celery
    try:
        if request.country == "EC":
            from app.workers.einvoicing_tasks import sign_and_send_sri_task
            task = sign_and_send_sri_task.delay(str(request.invoice_id), str(tenant_id))
        elif request.country == "ES":
            from app.workers.einvoicing_tasks import sign_and_send_facturae_task
            task = sign_and_send_facturae_task.delay(str(request.invoice_id), str(tenant_id))
        else:
            raise HTTPException(status_code=400, detail="País no soportado. Use 'ES' o 'EC'")
        
        logger.info(f"E-factura encolada: {request.invoice_id} ({request.country}) - Task {task.id}")
        
        return {
            "message": "E-invoice processing initiated",
            "task_id": task.id,
            "invoice_id": str(request.invoice_id),
            "country": request.country,
        }
    
    except Exception as e:
        logger.error(f"Error al encolar e-factura: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al iniciar proceso de e-factura: {str(e)}"
        )


@router.get("/status/{invoice_id}", response_model=EinvoicingStatusResponse)
def get_einvoice_status(
    invoice_id: UUID,
    country: str = "EC",
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Obtener estado de e-factura"""
    if country == "EC":
        query = text("""
            SELECT invoice_id, status, clave_acceso, error_message, submitted_at
            FROM sri_submissions
            WHERE invoice_id = :invoice_id::uuid AND tenant_id::text = :tenant_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
    elif country == "ES":
        query = text("""
            SELECT id as invoice_id, status, NULL as clave_acceso, error_message, submitted_at
            FROM sii_batches
            WHERE id = :invoice_id::uuid AND tenant_id::text = :tenant_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
    else:
        raise HTTPException(status_code=400, detail="País no soportado")
    
    result = db.execute(
        query,
        {"invoice_id": str(invoice_id), "tenant_id": str(tenant_id)}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No se encontró estado de e-factura para esta factura"
        )
    
    return EinvoicingStatusResponse(
        invoice_id=str(result[0]),
        country=country,
        status=result[1],
        clave_acceso=result[2],
        error_message=result[3],
        submitted_at=str(result[4]) if result[4] else None,
    )


@router.post("/sri/retry")
async def retry_sri(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Reintentar envío SRI (Ecuador)"""
    from app.workers.einvoicing_tasks import sign_and_send_sri_task
    
    task = sign_and_send_sri_task.delay(str(invoice_id), str(tenant_id))
    
    logger.info(f"SRI retry: {invoice_id} - Task {task.id}")
    
    return {
        "message": "Retry initiated",
        "task_id": task.id,
        "invoice_id": str(invoice_id),
    }


@router.get("/facturae/{invoice_id}/export")
def export_facturae(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Exportar XML Facturae (España)"""
    # Buscar en sii_batches
    query = text("""
        SELECT xml_content
        FROM sii_batches
        WHERE id = :invoice_id::uuid AND tenant_id::text = :tenant_id
    """)
    
    result = db.execute(
        query,
        {"invoice_id": str(invoice_id), "tenant_id": str(tenant_id)}
    ).fetchone()
    
    if not result or not result[0]:
        raise HTTPException(
            status_code=404,
            detail="XML Facturae no encontrado"
        )
    
    return Response(
        content=result[0],
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=facturae_{invoice_id}.xml"
        }
    )


@router.get("/credentials", response_model=CredentialsResponse)
def get_credentials(
    country: str = "EC",
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """Obtener estado de credenciales e-factura"""
    query = text("""
        SELECT country, cert_data IS NOT NULL as has_certificate, sandbox, updated_at
        FROM einv_credentials
        WHERE tenant_id::text = :tenant_id AND country = :country
    """)
    
    result = db.execute(
        query,
        {"tenant_id": str(tenant_id), "country": country}
    ).fetchone()
    
    if not result:
        return CredentialsResponse(
            country=country,
            has_certificate=False,
            sandbox=True,
            last_updated=None,
        )
    
    return CredentialsResponse(
        country=result[0],
        has_certificate=result[1],
        sandbox=result[2],
        last_updated=str(result[3]) if result[3] else None,
    )


@router.put("/credentials")
async def update_credentials(
    request: CredentialsRequest,
    cert_file: Optional[bytes] = None,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """
    Actualizar credenciales e-factura
    TODO: Implementar cifrado de certificados
    """
    # Por ahora, solo actualiza el flag sandbox
    upsert_query = text("""
        INSERT INTO einv_credentials (tenant_id, country, sandbox)
        VALUES (:tenant_id::uuid, :country, :sandbox)
        ON CONFLICT (tenant_id, country)
        DO UPDATE SET sandbox = :sandbox, updated_at = NOW()
    """)
    
    db.execute(
        upsert_query,
        {
            "tenant_id": str(tenant_id),
            "country": request.country,
            "sandbox": request.sandbox,
        }
    )
    
    db.commit()
    
    logger.info(f"Credenciales actualizadas: {tenant_id} - {request.country}")
    
    return {
        "message": "Credentials updated",
        "country": request.country,
        "sandbox": request.sandbox,
    }
