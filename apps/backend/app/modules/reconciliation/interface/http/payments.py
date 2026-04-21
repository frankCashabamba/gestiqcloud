"""
Payments Router - Payment links and webhooks
"""

import json
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.auth_dependencies import ensure_tenant, get_current_user
from app.modules.shared.services.statuses import PaymentLinkStatus
from app.modules.shared.services.tax import resolve_tenant_default_tax_rate
from app.services.payments import get_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


# ============================================================================
# Schemas
# ============================================================================


class PaymentLinkRequest(BaseModel):
    """Create payment link"""

    invoice_id: UUID
    provider: str = Field(..., pattern="^(stripe|kushki|payphone)$")
    success_url: str | None = None
    cancel_url: str | None = None
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class PaymentLinkResponse(BaseModel):
    """Response with payment URL"""

    url: str
    session_id: str
    payment_id: str | None = None
    expires_at: str | None = None


# ============================================================================
# Helpers
# ============================================================================


def get_provider_config(provider: str, tenant_id: str, db: Session) -> dict[str, Any]:
    """Get provider configuration from DB"""

    query = text(
        """
        SELECT config
        FROM payment_providers
        WHERE tenant_id = :tenant_id
          AND provider = :provider
          AND active = true
        LIMIT 1
    """
    )

    result = db.execute(query, {"tenant_id": tenant_id, "provider": provider}).first()

    if not result:
        import os

        if provider == "stripe":
            config = {
                "secret_key": os.getenv("STRIPE_SECRET_KEY"),
                "webhook_secret": os.getenv("STRIPE_WEBHOOK_SECRET"),
            }
        elif provider == "kushki":
            config = {
                "merchant_id": os.getenv("KUSHKI_MERCHANT_ID"),
                "public_key": os.getenv("KUSHKI_PUBLIC_KEY"),
                "private_key": os.getenv("KUSHKI_PRIVATE_KEY"),
                "webhook_secret": os.getenv("KUSHKI_WEBHOOK_SECRET"),
                "env": os.getenv("KUSHKI_ENV", "sandbox"),
            }
        elif provider == "payphone":
            config = {
                "token": os.getenv("PAYPHONE_TOKEN"),
                "store_id": os.getenv("PAYPHONE_STORE_ID"),
                "webhook_secret": os.getenv("PAYPHONE_WEBHOOK_SECRET"),
                "env": os.getenv("PAYPHONE_ENV", "sandbox"),
            }
        else:
            raise ValueError(f"Provider not configured: {provider}")
    else:
        config = dict(result[0])

    config.setdefault("tenant_id", tenant_id)
    config.setdefault("tax_rate", float(resolve_tenant_default_tax_rate(db, tenant_id)))
    return config


def get_invoice_data(invoice_id: UUID, tenant_id: str, db: Session) -> dict[str, Any]:
    """Get invoice data"""

    query = text(
        """
        SELECT
            i.id, i.numero, i.total, i.estado,
            c.name as customer_name,
            c.email as customer_email
        FROM invoices i
        LEFT JOIN clientes c ON c.id = i.cliente_id
        WHERE i.id = :invoice_id
          AND i.tenant_id = :tenant_id
    """
    )

    result = db.execute(
        query,
        {"invoice_id": str(invoice_id), "tenant_id": tenant_id},
    ).first()

    if not result:
        raise HTTPException(404, "Invoice not found")

    return {
        "id": result[0],
        "numero": result[1],
        "total": result[2],
        "estado": result[3],
        "customer_name": result[4],
        "customer_email": result[5],
    }


def _safe_json_loads(payload: bytes) -> dict[str, Any]:
    try:
        data = json.loads(payload.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _coerce_uuid_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _extract_webhook_hints(provider: str, payload: bytes) -> dict[str, str | None]:
    data = _safe_json_loads(payload)
    hints: dict[str, str | None] = {
        "tenant_id": None,
        "invoice_id": None,
        "session_id": None,
        "payment_id": None,
    }

    if provider == "stripe":
        event_data = (data.get("data") or {}).get("object") or {}
        metadata = event_data.get("metadata") or {}
        hints["tenant_id"] = _coerce_uuid_str(metadata.get("tenant_id"))
        hints["invoice_id"] = _coerce_uuid_str(metadata.get("invoice_id"))
        hints["session_id"] = str(event_data.get("id")) if event_data.get("id") else None
        payment_intent = event_data.get("payment_intent")
        hints["payment_id"] = str(payment_intent) if payment_intent else hints["session_id"]
        return hints

    transaction = data.get("transaction") or {}
    metadata = transaction.get("metadata") or data.get("metadata") or {}
    hints["tenant_id"] = _coerce_uuid_str(metadata.get("tenant_id"))
    hints["invoice_id"] = _coerce_uuid_str(
        metadata.get("invoice_id")
        or transaction.get("invoice_id")
        or transaction.get("clientTransactionId")
        or transaction.get("reference")
    )
    session_id = (
        transaction.get("token")
        or transaction.get("ticketNumber")
        or transaction.get("transactionId")
    )
    payment_id = (
        transaction.get("id") or transaction.get("transactionId") or transaction.get("ticketNumber")
    )
    hints["session_id"] = str(session_id) if session_id else None
    hints["payment_id"] = str(payment_id) if payment_id else hints["session_id"]
    return hints


def _find_tenant_id_from_payment_links(
    db: Session,
    *,
    invoice_id: str | None = None,
    session_id: str | None = None,
    payment_id: str | None = None,
) -> str | None:
    if invoice_id:
        tenant_id = db.execute(
            text(
                """
                SELECT tenant_id
                FROM payment_links
                WHERE invoice_id = :invoice_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"invoice_id": invoice_id},
        ).scalar()
        if tenant_id:
            return str(tenant_id)

        tenant_id = db.execute(
            text("SELECT tenant_id FROM invoices WHERE id = :invoice_id LIMIT 1"),
            {"invoice_id": invoice_id},
        ).scalar()
        if tenant_id:
            return str(tenant_id)

    for candidate in (session_id, payment_id):
        if not candidate:
            continue
        tenant_id = db.execute(
            text(
                """
                SELECT tenant_id
                FROM payment_links
                WHERE session_id = :candidate
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"candidate": candidate},
        ).scalar()
        if tenant_id:
            return str(tenant_id)

    return None


def _resolve_webhook_tenant_id(provider: str, payload: bytes, db: Session) -> str:
    hints = _extract_webhook_hints(provider, payload)
    tenant_id = hints.get("tenant_id")
    if tenant_id:
        return tenant_id

    linked_tenant_id = _find_tenant_id_from_payment_links(
        db,
        invoice_id=hints.get("invoice_id"),
        session_id=hints.get("session_id"),
        payment_id=hints.get("payment_id"),
    )
    normalized = _coerce_uuid_str(linked_tenant_id)
    if normalized:
        return normalized

    raise ValueError("tenant_not_resolved")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/link", response_model=PaymentLinkResponse)
def create_payment_link(
    request: Request,
    data: PaymentLinkRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Create payment link"""

    invoice = get_invoice_data(data.invoice_id, tenant_id, db)

    if invoice["estado"] == "paid":
        raise HTTPException(400, "Invoice already paid")

    config = get_provider_config(data.provider, tenant_id, db)

    provider = get_provider(data.provider, config)

    tenant_currency = db.execute(
        text(
            """
            SELECT COALESCE(
                NULLIF(UPPER(TRIM(cs.currency)), ''),
                NULLIF(UPPER(TRIM(cur.code)), '')
            )
            FROM company_settings cs
            LEFT JOIN currencies cur ON cur.id = cs.currency_id
            WHERE cs.tenant_id = :tid
            LIMIT 1
            """
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_id},
    ).scalar()
    payment_currency = tenant_currency or "USD"

    base_url = str(request.base_url).rstrip("/") if request else ""
    success_url = data.success_url or f"{base_url}/payments/success?invoice_id={invoice['id']}"
    cancel_url = data.cancel_url or f"{base_url}/payments/cancel?invoice_id={invoice['id']}"

    try:
        result = provider.create_payment_link(
            amount=Decimal(str(invoice["total"])),
            currency=payment_currency,
            invoice_id=str(invoice["id"]),
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": tenant_id,
                "invoice_numero": invoice["numero"],
                **data.metadata,
            },
        )

        insert_query = text(
            """
            INSERT INTO payment_links (
                id, tenant_id, invoice_id, provider,
                session_id, payment_url, status, created_by
            )
            VALUES (
                gen_random_uuid(), :tenant_id, :invoice_id, :provider,
                :session_id, :payment_url, :status_pending, :created_by
            )
        """
        )

        db.execute(
            insert_query,
            {
                "tenant_id": tenant_id,
                "invoice_id": str(invoice["id"]),
                "provider": data.provider,
                "session_id": result["session_id"],
                "payment_url": result["url"],
                "status_pending": PaymentLinkStatus.PENDING.value,
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
        raise HTTPException(500, f"Error creating payment link: {str(e)}")


@router.post("/webhook/{provider}")
async def handle_webhook(provider: str, request: Request, db: Session = Depends(get_db)):
    """Process payment provider webhooks"""

    try:
        payload = await request.body()
        headers = dict(request.headers)

        logger.info(f"Webhook received from {provider}")

        tenant_id = _resolve_webhook_tenant_id(provider, payload, db)
        config = get_provider_config(provider, tenant_id, db)

        payment_provider = get_provider(provider, config)

        result = payment_provider.handle_webhook(payload, headers)
        resolved_tenant_id = _coerce_uuid_str(result.get("tenant_id")) or tenant_id

        logger.info(f"Webhook processed: {result}")

        if result.get("status") == "paid":
            invoice_id = result.get("invoice_id")

            if invoice_id:
                update_query = text(
                    """
                    UPDATE invoices
                    SET estado = 'paid'
                    WHERE id = :invoice_id
                      AND tenant_id = :tenant_id
                      AND estado != 'paid'
                """
                )

                db.execute(
                    update_query,
                    {"invoice_id": invoice_id, "tenant_id": resolved_tenant_id},
                )

                update_link = text(
                    """
                    UPDATE payment_links
                    SET status = :status_completed, completed_at = NOW()
                    WHERE invoice_id = :invoice_id
                      AND tenant_id = :tenant_id
                      AND status = :status_pending
                """
                )

                db.execute(
                    update_link,
                    {
                        "invoice_id": invoice_id,
                        "tenant_id": resolved_tenant_id,
                        "status_completed": PaymentLinkStatus.COMPLETED.value,
                        "status_pending": PaymentLinkStatus.PENDING.value,
                    },
                )

                db.commit()

                logger.info(f"Invoice marked as paid: {invoice_id}")

                # Trigger payment.received webhook
                try:
                    from uuid import UUID

                    from app.modules.reconciliation.webhooks import PaymentWebhookService

                    tenant_id_uuid = UUID(str(resolved_tenant_id))
                    webhook_service = PaymentWebhookService(db)
                    webhook_service.trigger_payment_received(
                        tenant_id=tenant_id_uuid,
                        payment_id=result.get("payment_id", ""),
                        invoice_id=invoice_id,
                        amount=result.get("amount", 0),
                        currency=result.get("currency", "USD"),
                        payment_method=result.get("method"),
                        reference_number=result.get("reference"),
                    )
                except Exception as e:
                    logger.error(f"Error triggering payment.received webhook: {e}")

        elif result.get("status") == "failed":
            invoice_id = result.get("invoice_id")

            if invoice_id:
                update_link = text(
                    """
                    UPDATE payment_links
                    SET status = :status_failed,
                        error_message = :error
                    WHERE invoice_id = :invoice_id
                      AND tenant_id = :tenant_id
                      AND status = :status_pending
                """
                )

                db.execute(
                    update_link,
                    {
                        "invoice_id": invoice_id,
                        "tenant_id": resolved_tenant_id,
                        "error": result.get("error", "Payment failed"),
                        "status_failed": PaymentLinkStatus.FAILED.value,
                        "status_pending": PaymentLinkStatus.PENDING.value,
                    },
                )

                db.commit()

                # Trigger payment.failed webhook
                try:
                    from uuid import UUID

                    from app.modules.reconciliation.webhooks import PaymentWebhookService

                    tenant_id_uuid = UUID(str(resolved_tenant_id))
                    webhook_service = PaymentWebhookService(db)
                    webhook_service.trigger_payment_failed(
                        tenant_id=tenant_id_uuid,
                        payment_id=result.get("payment_id", ""),
                        invoice_id=invoice_id,
                        amount=result.get("amount", 0),
                        currency=result.get("currency", "USD"),
                        reason=result.get("error", "Payment failed"),
                        error_code=result.get("error_code"),
                    )
                except Exception as e:
                    logger.error(f"Error triggering payment.failed webhook: {e}")

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
    """Get payment status"""

    query = text(
        """
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
    """
    )

    result = db.execute(query, {"invoice_id": str(invoice_id), "tenant_id": tenant_id}).first()

    if not result:
        raise HTTPException(404, "Payment information not found")

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
    amount: Decimal | None = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
    current_user: dict = Depends(get_current_user),
):
    """Refund payment"""

    query = text(
        """
        SELECT pl.provider, pl.session_id, i.total
        FROM payment_links pl
        JOIN invoices i ON i.id = pl.invoice_id
        WHERE pl.session_id = :payment_id
          AND pl.tenant_id = :tenant_id
          AND pl.status = 'completed'
    """
    )

    payment = db.execute(query, {"payment_id": payment_id, "tenant_id": tenant_id}).first()

    if not payment:
        raise HTTPException(404, "Payment not found or not completed")

    config = get_provider_config(payment[0], tenant_id, db)
    provider = get_provider(payment[0], config)

    try:
        refund_amount = amount or Decimal(str(payment[2]))

        result = provider.refund(payment_id, refund_amount)

        insert_refund = text(
            """
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
        """
        )

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
        raise HTTPException(500, f"Error processing refund: {str(e)}")
