"""
Payments Service - Payment providers integration
"""

from decimal import Decimal
from typing import Any, Dict, Protocol


class PaymentProvider(Protocol):
    """Interface para proveedores de pago"""

    def create_payment_link(
        self,
        amount: Decimal,
        currency: str,
        invoice_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, Any] = None,
    ) -> dict[str, str]:
        """
        Crear enlace de pago.

        Returns:
            Dict con 'url' y 'session_id' o 'payment_id'
        """
        ...

    def handle_webhook(self, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        """
        Procesar webhook del proveedor.

        Returns:
            Dict con 'status', 'invoice_id', 'amount', etc.
        """
        ...

    def refund(self, payment_id: str, amount: Decimal = None) -> dict[str, Any]:
        """
        Reembolsar pago.

        Args:
            payment_id: ID del pago original
            amount: Monto a reembolsar (None = total)
        """
        ...


def get_provider(name: str, config: dict[str, Any]) -> PaymentProvider:
    """Factory para obtener proveedor de pago"""

    if name == "stripe":
        from .stripe_provider import StripeProvider

        return StripeProvider(config)

    elif name == "kushki":
        from .kushki_provider import KushkiProvider

        return KushkiProvider(config)

    elif name == "payphone":
        from .payphone_provider import PayPhoneProvider

        return PayPhoneProvider(config)

    else:
        raise ValueError(f"Proveedor de pago no soportado: {name}")
