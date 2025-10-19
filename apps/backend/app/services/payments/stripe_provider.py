"""
Stripe Payment Provider
"""
import stripe
from typing import Dict, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class StripeProvider:
    """Proveedor de pagos Stripe (España principalmente)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("secret_key")
        self.webhook_secret = config.get("webhook_secret")
        
        if not self.api_key:
            raise ValueError("Stripe secret_key requerido")
        
        stripe.api_key = self.api_key
    
    def create_payment_link(
        self,
        amount: Decimal,
        currency: str,
        invoice_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Crear sesión de pago Stripe Checkout"""
        
        try:
            # Convertir a centavos
            amount_cents = int(amount * 100)
            
            session = stripe.checkout.Session.create(
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': f'Factura #{invoice_id[:8]}...',
                            'description': f'Pago de factura'
                        },
                        'unit_amount': amount_cents
                    },
                    'quantity': 1
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'invoice_id': invoice_id,
                    **(metadata or {})
                },
                payment_intent_data={
                    'metadata': {
                        'invoice_id': invoice_id
                    }
                }
            )
            
            logger.info(f"Stripe session creada: {session.id} (invoice={invoice_id})")
            
            return {
                'url': session.url,
                'session_id': session.id,
                'payment_id': session.payment_intent
            }
        
        except stripe.error.StripeError as e:
            logger.error(f"Error Stripe: {e}")
            raise ValueError(f"Error creando sesión de pago: {str(e)}")
    
    def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Procesar webhook de Stripe"""
        
        sig_header = headers.get('stripe-signature') or headers.get('Stripe-Signature')
        
        if not sig_header:
            raise ValueError("Firma de webhook no encontrada")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            logger.info(f"Webhook Stripe recibido: {event.type}")
            
            if event.type == 'checkout.session.completed':
                session = event.data.object
                invoice_id = session.metadata.get('invoice_id')
                amount = Decimal(session.amount_total) / 100
                
                return {
                    'status': 'paid',
                    'invoice_id': invoice_id,
                    'amount': amount,
                    'currency': session.currency.upper(),
                    'payment_id': session.payment_intent,
                    'customer_email': session.customer_details.email if session.customer_details else None
                }
            
            elif event.type == 'payment_intent.succeeded':
                payment_intent = event.data.object
                invoice_id = payment_intent.metadata.get('invoice_id')
                amount = Decimal(payment_intent.amount) / 100
                
                return {
                    'status': 'paid',
                    'invoice_id': invoice_id,
                    'amount': amount,
                    'currency': payment_intent.currency.upper(),
                    'payment_id': payment_intent.id
                }
            
            elif event.type == 'payment_intent.payment_failed':
                payment_intent = event.data.object
                
                return {
                    'status': 'failed',
                    'invoice_id': payment_intent.metadata.get('invoice_id'),
                    'error': payment_intent.last_payment_error.message if payment_intent.last_payment_error else 'Unknown error'
                }
            
            else:
                logger.warning(f"Evento Stripe no manejado: {event.type}")
                return {'status': 'ignored', 'event_type': event.type}
        
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Error verificando firma Stripe: {e}")
            raise ValueError("Firma inválida")
        
        except Exception as e:
            logger.error(f"Error procesando webhook Stripe: {e}")
            raise
    
    def refund(self, payment_id: str, amount: Decimal = None) -> Dict[str, Any]:
        """Reembolsar pago via Stripe"""
        
        try:
            refund_params = {'payment_intent': payment_id}
            
            if amount:
                refund_params['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_params)
            
            logger.info(f"Reembolso Stripe creado: {refund.id} (payment={payment_id})")
            
            return {
                'status': refund.status,
                'refund_id': refund.id,
                'amount': Decimal(refund.amount) / 100,
                'currency': refund.currency.upper()
            }
        
        except stripe.error.StripeError as e:
            logger.error(f"Error Stripe refund: {e}")
            raise ValueError(f"Error procesando reembolso: {str(e)}")
