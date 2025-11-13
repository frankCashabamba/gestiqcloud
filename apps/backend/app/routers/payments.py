"""
Payments Router - Payment links and webhooks
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant, get_current_user
from app.services.payments import get_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


# ============================================================================
# Schemas
# ============================================================================


class PaymentLinkRequest(BaseModel):
    """Crear enlace de pago"""

    invoice_id: UUID
    provider: str = Field(..., pattern="^(stripe|kushki|payphone)$")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PaymentLinkResponse(BaseModel):
    """Respuesta con URL de pago"""

    url: str
    session_id: str
    payment_id: Optional[str] = None
    expires_at: Optional[str] = None


# ============================================================================
# Helpers
# ============================================================================


def get_provider_config(provider: str, tenant_id: str, db: Session) -> Dict[str, Any]:
    """Obtener configuración del proveedor desde DB"""

    query = text("""
        SELECT config
        FROM payment_providers
        WHERE tenant_id = :tenant_id
          AND provider = :provider
          AND active = true
        LIMIT 1
    """)

    result = db.execute(query, {"tenant_id": tenant_id, "provider": provider}).first()

    if not result:
        # Fallback: variables de entorno (desarrollo)
        import os

        if provider == "stripe":
            return {
                "secret_key": os.getenv("STRIPE_SECRET_KEY"),
                "webhook_secret": os.getenv("STRIPE_WEBHOOK_SECRET"),
            }
        elif provider == "kushki":
            return {
                "merchant_id": os.getenv("KUSHKI_MERCHANT_ID"),
                "public_key": os.getenv("KUSHKI_PUBLIC_KEY"),
                "private_key": os.getenv("KUSHKI_PRIVATE_KEY"),
                "webhook_secret": os.getenv("KUSHKI_WEBHOOK_SECRET"),
                "env": os.getenv("KUSHKI_ENV", "sandbox"),
            }
        elif provider == "payphone":
            return {
                "token": os.getenv("PAYPHONE_TOKEN"),
                "store_id": os.getenv("PAYPHONE_STORE_ID"),
                "webhook_secret": os.getenv("PAYPHONE_WEBHOOK_SECRET"),
                "env": os.getenv("PAYPHONE_ENV", "sandbox"),
            }
        else:
            raise ValueError(f"Proveedor no configurado: {provider}")

    return result[0]


def get_invoice_data(invoice_id: UUID, db: Session) -> Dict[str, Any]:
    """Obtener datos de factura"""

    query = text("""
        SELECT 
            i.id, i.numero, i.total, i.estado,
            c.name as cliente_nombre,
            c.email as cliente_email
        FROM invoices i
        LEFT JOIN clientes c ON c.id = i.cliente_id
        WHERE i.id = :invoice_id
    """)

    result = db.execute(query, {"invoice_id": str(invoice_id)}).first()

    if not result:
        raise HTTPException(404, "Factura no encontrada")

    return {
        "id": result[0],
        "numero": result[1],
        "total": result[2],
        "estado": result[3],
        "cliente_nombre": result[4],
        "cliente_email": result[5],
    }


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/link", response_model=PaymentLinkResponse)
def create_payment_link(
    data: PaymentLinkRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Crear enlace de pago"""

    # 1. Obtener datos de factura
    invoice = get_invoice_data(data.invoice_id, db)

    if invoice["estado"] == "paid":
        raise HTTPException(400, "Factura ya pagada")

    # 2. Obtener configuración del proveedor
    config = get_provider_config(data.provider, tenant_id, db)

    # 3. Crear provider
    provider = get_provider(data.provider, config)

    # 4. URLs de callback
    base_url = "https://tu-dominio.com"  # TODO: desde config
    success_url = (
        data.success_url or f"{base_url}/payments/success?invoice_id={invoice['id']}"
    )
    cancel_url = (
        data.cancel_url or f"{base_url}/payments/cancel?invoice_id={invoice['id']}"
    )

    # 5. Crear enlace
    try:
        result = provider.create_payment_link(
            amount=Decimal(str(invoice["total"])),
            currency="USD",  # TODO: desde invoice
            invoice_id=str(invoice["id"]),
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": tenant_id,
                "invoice_numero": invoice["numero"],
                **data.metadata,
            },
        )

        # 6. Guardar en DB
        insert_query = text("""
            INSERT INTO payment_links (
                id, tenant_id, invoice_id, provider,
                session_id, payment_url, status, created_by
            )
            VALUES (
                gen_random_uuid(), :tenant_id, :invoice_id, :provider,
                :session_id, :payment_url, 'pending', :created_by
            )
        """)

        db.execute(
            insert_query,
            {
                "tenant_id": tenant_id,
                "invoice_id": str(invoice["id"]),
                "provider": data.provider,
                "session_id": result["session_id"],
                "payment_url": result["url"],
                "created_by": current_user["id"],
            },
        )

        db.commit()

        logger.info(
            f"Payment link created: {data.provider} "
            f"(invoice={invoice['numero']}, session={result['session_id']})"
        )

        return PaymentLinkResponse(
            url=result["url"],
            session_id=result["session_id"],
            payment_id=result.get("payment_id"),
        )

    except Exception as e:
        logger.error(f"Error creating payment link: {e}")
        raise HTTPException(500, f"Error creando enlace de pago: {str(e)}")


@router.post("/webhook/{provider}")
async def handle_webhook(
    provider: str, request: Request, db: Session = Depends(get_db)
):
    """Procesar webhooks de proveedores de pago"""

    try:
        # 1. Leer payload
        payload = await request.body()
        headers = dict(request.headers)

        logger.info(f"Webhook received from {provider}")

        # 2. Obtener configuración (sin tenant_id por ahora, webhook público)
        # TODO: Identificar tenant desde payload o path
        config = get_provider_config(provider, "default", db)

        # 3. Crear provider
        payment_provider = get_provider(provider, config)

        # 4. Procesar webhook
        result = payment_provider.handle_webhook(payload, headers)

        logger.info(f"Webhook processed: {result}")

        # 5. Actualizar factura si pago exitoso
        if result.get("status") == "paid":
            invoice_id = result.get("invoice_id")

            if invoice_id:
                update_query = text("""
                    UPDATE invoices
                    SET estado = 'paid'
                    WHERE id = :invoice_id
                      AND estado != 'paid'
                """)

                db.execute(update_query, {"invoice_id": invoice_id})

                # Actualizar link
                update_link = text("""
                    UPDATE payment_links
                    SET status = 'completed', completed_at = NOW()
                    WHERE invoice_id = :invoice_id
                      AND status = 'pending'
                """)

                db.execute(update_link, {"invoice_id": invoice_id})

                db.commit()

                logger.info(f"Invoice marked as paid: {invoice_id}")

        elif result.get("status") == "failed":
            invoice_id = result.get("invoice_id")

            if invoice_id:
                update_link = text("""
                    UPDATE payment_links
                    SET status = 'failed', 
                        error_message = :error
                    WHERE invoice_id = :invoice_id
                      AND status = 'pending'
                """)

                db.execute(
                    update_link,
                    {
                        "invoice_id": invoice_id,
                        "error": result.get("error", "Payment failed"),
                    },
                )

                db.commit()

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except ValueError as e:
        logger.error(f"Webhook validation error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=400)

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return JSONResponse(content={"error": "Internal error"}, status_code=500)


@router.get("/status/{invoice_id}")
def get_payment_status(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Consultar estado de pago"""

    query = text("""
        SELECT 
            pl.id, pl.provider, pl.status, pl.payment_url,
            pl.created_at, pl.completed_at, pl.error_message,
            i.total, i.estado as invoice_status
        FROM payment_links pl
        JOIN invoices i ON i.id = pl.invoice_id
        WHERE pl.invoice_id = :invoice_id
          AND pl.tenant_id = :tenant_id
        ORDER BY pl.created_at DESC
        LIMIT 1
    """)

    result = db.execute(
        query, {"invoice_id": str(invoice_id), "tenant_id": tenant_id}
    ).first()

    if not result:
        raise HTTPException(404, "No se encontró información de pago")

    return {
        "id": result[0],
        "provider": result[1],
        "status": result[2],
        "payment_url": result[3],
        "created_at": result[4],
        "completed_at": result[5],
        "error_message": result[6],
        "amount": result[7],
        "invoice_status": result[8],
    }


@router.post("/refund/{payment_id}")
def refund_payment(
    payment_id: str,
    amount: Optional[Decimal] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Reembolsar pago"""

    # 1. Buscar payment
    query = text("""
        SELECT pl.provider, pl.session_id, i.total
        FROM payment_links pl
        JOIN invoices i ON i.id = pl.invoice_id
        WHERE pl.session_id = :payment_id
          AND pl.tenant_id = :tenant_id
          AND pl.status = 'completed'
    """)

    payment = db.execute(
        query, {"payment_id": payment_id, "tenant_id": tenant_id}
    ).first()

    if not payment:
        raise HTTPException(404, "Pago no encontrado o no completado")

    # 2. Obtener config y provider
    config = get_provider_config(payment[0], tenant_id, db)
    provider = get_provider(payment[0], config)

    # 3. Procesar reembolso
    try:
        refund_amount = amount or Decimal(str(payment[2]))

        result = provider.refund(payment_id, refund_amount)

        # 4. Registrar reembolso
        insert_refund = text("""
            INSERT INTO payment_refunds (
                id, payment_link_id, amount, status,
                refund_id, created_by
            )
            SELECT 
                gen_random_uuid(),
                pl.id,
                :amount,
                :status,
                :refund_id,
                :created_by
            FROM payment_links pl
            WHERE pl.session_id = :payment_id
        """)

        db.execute(
            insert_refund,
            {
                "amount": float(refund_amount),
                "status": result["status"],
                "refund_id": result.get("refund_id"),
                "created_by": current_user["id"],
                "payment_id": payment_id,
            },
        )

        db.commit()

        logger.info(f"Payment refunded: {payment_id} (amount={refund_amount})")

        return {
            "status": "ok",
            "refund_id": result.get("refund_id"),
            "amount": refund_amount,
        }

    except Exception as e:
        logger.error(f"Refund error: {e}")
        raise HTTPException(500, f"Error procesando reembolso: {str(e)}")
