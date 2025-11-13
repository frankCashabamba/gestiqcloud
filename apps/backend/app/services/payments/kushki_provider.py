"""
Kushki Payment Provider (Ecuador)
"""

import hashlib
import hmac
import logging
from decimal import Decimal
from typing import Any

import requests

logger = logging.getLogger(__name__)


class KushkiProvider:
    """Proveedor de pagos Kushki (Ecuador)"""

    def __init__(self, config: dict[str, Any]):
        self.merchant_id = config.get("merchant_id")
        self.public_key = config.get("public_key")
        self.private_key = config.get("private_key")
        self.webhook_secret = config.get("webhook_secret")
        self.env = config.get("env", "sandbox")  # sandbox | production

        if not all([self.merchant_id, self.public_key, self.private_key]):
            raise ValueError("Kushki credentials incompletas")

        self.base_url = (
            "https://api.kushkipagos.com"
            if self.env == "production"
            else "https://api-uat.kushkipagos.com"
        )

    def create_payment_link(
        self,
        amount: Decimal,
        currency: str,
        invoice_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, str]:
        """Crear enlace de pago Kushki"""

        try:
            # Kushki trabaja con centavos
            amount_cents = int(amount * 100)

            payload = {
                "amount": {
                    "subtotalIva": 0,
                    "subtotalIva0": amount_cents,
                    "iva": 0,
                    "currency": currency,
                },
                "callbackUrl": success_url,
                "cancelUrl": cancel_url,
                "metadata": {"invoice_id": invoice_id, **(metadata or {})},
            }

            headers = {
                "Public-Merchant-Id": self.merchant_id,
                "Private-Merchant-Id": self.private_key,
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.base_url}/payment/v1/card-async",
                json=payload,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            payment_id = data.get("token")
            payment_url = data.get("redirectUrl") or f"{self.base_url}/checkout?token={payment_id}"

            logger.info(f"Kushki payment creado: {payment_id} (invoice={invoice_id})")

            return {
                "url": payment_url,
                "session_id": payment_id,
                "payment_id": payment_id,
            }

        except requests.RequestException as e:
            logger.error(f"Error Kushki API: {e}")
            raise ValueError(f"Error creando pago: {str(e)}")

    def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        """Procesar webhook de Kushki"""

        # Verificar firma HMAC si está configurada
        if self.webhook_secret:
            signature = headers.get("x-kushki-signature")
            if signature:
                expected_sig = hmac.new(
                    self.webhook_secret.encode(), payload, hashlib.sha256
                ).hexdigest()

                if signature != expected_sig:
                    raise ValueError("Firma de webhook inválida")

        import json

        data = json.loads(payload.decode("utf-8"))

        event_type = data.get("eventType") or data.get("event")
        transaction = data.get("transaction", {})

        invoice_id = transaction.get("metadata", {}).get("invoice_id")

        if event_type in ["payment.success", "charge.success"]:
            return {
                "status": "paid",
                "invoice_id": invoice_id,
                "amount": Decimal(transaction.get("amount", 0)) / 100,
                "currency": transaction.get("currency", "USD"),
                "payment_id": transaction.get("ticketNumber") or transaction.get("token"),
            }

        elif event_type in ["payment.failed", "charge.failed"]:
            return {
                "status": "failed",
                "invoice_id": invoice_id,
                "error": transaction.get("responseText", "Error desconocido"),
            }

        else:
            logger.warning(f"Evento Kushki no manejado: {event_type}")
            return {"status": "ignored", "event_type": event_type}

    def refund(self, payment_id: str, amount: Decimal = None) -> dict[str, Any]:
        """Reembolsar pago via Kushki"""

        try:
            payload = {"ticketNumber": payment_id}

            if amount:
                payload["amount"] = int(amount * 100)

            headers = {
                "Private-Merchant-Id": self.private_key,
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.base_url}/card/v1/refund",
                json=payload,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Reembolso Kushki: {payment_id}")

            return {
                "status": "refunded",
                "refund_id": data.get("ticketNumber"),
                "amount": Decimal(data.get("amount", 0)) / 100,
            }

        except requests.RequestException as e:
            logger.error(f"Error Kushki refund: {e}")
            raise ValueError(f"Error procesando reembolso: {str(e)}")
