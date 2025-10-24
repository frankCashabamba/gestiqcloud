"""
PayPhone Payment Provider (Ecuador)
"""
import requests
from typing import Dict, Any
from decimal import Decimal
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)


class PayPhoneProvider:
    """Proveedor de pagos PayPhone (Ecuador)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.token = config.get("token")
        self.store_id = config.get("store_id")
        self.webhook_secret = config.get("webhook_secret")
        self.env = config.get("env", "sandbox")
        
        if not all([self.token, self.store_id]):
            raise ValueError("PayPhone credentials incompletas")
        
        self.base_url = (
            "https://pay.payphonetodoesposible.com"
            if self.env == "production"
            else "https://sandbox-pay.payphonetodoesposible.com"
        )
    
    def create_payment_link(
        self,
        amount: Decimal,
        currency: str,
        invoice_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Crear enlace de pago PayPhone"""
        
        try:
            payload = {
                "amount": float(amount),
                "amountWithoutTax": float(amount * Decimal("0.88")),  # Aprox sin IVA
                "tax": float(amount * Decimal("0.12")),  # 12% IVA Ecuador
                "service": "0",  # Sin costo de servicio
                "tip": "0",
                "reference": invoice_id,
                "clientTransactionId": invoice_id,
                "currency": currency,
                "responseUrl": success_url,
                "cancellationUrl": cancel_url,
                "storeId": self.store_id,
                "metadata": {
                    "invoice_id": invoice_id,
                    **(metadata or {})
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/api/button/Prepare",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"PayPhone error: {data.get('message')}")
            
            payment_id = data.get("transactionId")
            payment_url = data.get("payWithCard") or data.get("paymentUrl")
            
            logger.info(f"PayPhone payment creado: {payment_id} (invoice={invoice_id})")
            
            return {
                'url': payment_url,
                'session_id': payment_id,
                'payment_id': payment_id
            }
        
        except requests.RequestException as e:
            logger.error(f"Error PayPhone API: {e}")
            raise ValueError(f"Error creando pago: {str(e)}")
    
    def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Procesar webhook de PayPhone"""
        
        # Verificar firma si está configurada
        if self.webhook_secret:
            signature = headers.get('x-payphone-signature')
            if signature:
                expected_sig = hmac.new(
                    self.webhook_secret.encode(),
                    payload,
                    hashlib.sha256
                ).hexdigest()
                
                if signature != expected_sig:
                    raise ValueError("Firma de webhook inválida")
        
        import json
        data = json.loads(payload.decode('utf-8'))
        
        status_code = data.get('statusCode')
        transaction = data.get('transaction', {})
        
        invoice_id = transaction.get('clientTransactionId') or transaction.get('reference')
        
        # StatusCode: 1=Pending, 2=Approved, 3=Cancelled, 4=Failed
        if status_code == 2 or status_code == '2':
            return {
                'status': 'paid',
                'invoice_id': invoice_id,
                'amount': Decimal(str(transaction.get('amount', 0))),
                'currency': transaction.get('currency', 'USD'),
                'payment_id': transaction.get('id') or transaction.get('transactionId'),
                'phone_number': transaction.get('phoneNumber')
            }
        
        elif status_code in [3, 4, '3', '4']:
            return {
                'status': 'failed',
                'invoice_id': invoice_id,
                'error': transaction.get('message', 'Pago cancelado o fallido')
            }
        
        else:
            logger.warning(f"StatusCode PayPhone no manejado: {status_code}")
            return {'status': 'pending', 'invoice_id': invoice_id}
    
    def refund(self, payment_id: str, amount: Decimal = None) -> Dict[str, Any]:
        """Reembolsar pago via PayPhone"""
        
        try:
            payload = {
                "transactionId": payment_id
            }
            
            if amount:
                payload["amount"] = float(amount)
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/api/button/Refund",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"PayPhone refund error: {data.get('message')}")
            
            logger.info(f"Reembolso PayPhone: {payment_id}")
            
            return {
                'status': 'refunded',
                'refund_id': data.get('refundId'),
                'amount': amount
            }
        
        except requests.RequestException as e:
            logger.error(f"Error PayPhone refund: {e}")
            raise ValueError(f"Error procesando reembolso: {str(e)}")
