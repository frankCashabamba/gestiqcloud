"""
Router/mapper to dispatch canonical documents to handlers according to doc_type.

Maps doc_type (invoice, bank_tx, expense_receipt, products)
to corresponding handlers (InvoiceHandler, BankHandler, ExpenseHandler, ProductHandler).
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .handlers import BankHandler, ExpenseHandler, InvoiceHandler, ProductHandler, PromoteResult


class HandlersRouter:
    """Router to dispatch documents to handlers according to their type."""

    # Mapping: doc_type -> Handler class
    HANDLER_MAP: dict[str, type] = {
        "invoice": InvoiceHandler,
        "expense_receipt": ExpenseHandler,
        "bank_tx": BankHandler,
        "product": ProductHandler,
        "products": ProductHandler,
        "expense": ExpenseHandler,
        # Aliases for flexibility
        "factura": InvoiceHandler,
        "recibo": ExpenseHandler,
        "transferencia": BankHandler,
        "transaccion_bancaria": BankHandler,
        "expense_old": ExpenseHandler,
    }

    # Mapping: doc_type -> target destination table
    ROUTING_TARGET_MAP: dict[str, str] = {
        "invoice": "invoices",
        "expense_receipt": "expenses",
        "bank_tx": "bank_movements",
        "product": "inventory",
        "products": "inventory",
        "expense": "expenses",
        # Aliases
        "factura": "invoices",
        "recibo": "expenses",
        "transferencia": "bank_movements",
        "transaccion_bancaria": "bank_movements",
        "expense_old": "expenses",
    }

    @classmethod
    def get_handler_for_type(cls, doc_type: str) -> type | None:
        """Get handler class for a doc_type."""
        return cls.HANDLER_MAP.get(doc_type.lower())

    @classmethod
    def get_target_for_type(cls, doc_type: str) -> str | None:
        """Get destination table for a doc_type."""
        return cls.ROUTING_TARGET_MAP.get(doc_type.lower())

    @classmethod
    def promote_canonical(
        cls,
        db: Session,
        tenant_id: UUID,
        canonical_doc: dict[str, Any],
        promoted_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Promote canonical document into its destination table based on doc_type.

        Returns a dict with:
            domain_id: created/updated domain object id
            target: destination table name
            skipped: True if no handler/target was found
        """
        doc_type = canonical_doc.get("doc_type", "other")
        handler_class = cls.get_handler_for_type(doc_type)
        target = cls.get_target_for_type(doc_type)

        if not handler_class:
            return {
                "domain_id": None,
                "target": target or "unknown",
                "skipped": False,
            }

        # Convert canonical_doc to the normalized format expected by handlers
        normalized = _canonical_to_normalized(canonical_doc)

        # Call handler
        try:
            result: PromoteResult = handler_class.promote(
                db=db,
                tenant_id=tenant_id,
                normalized=normalized,
                promoted_id=promoted_id,
                **kwargs,
            )
            return {
                "domain_id": result.domain_id,
                "target": target or "unknown",
                "skipped": result.skipped,
            }
        except Exception:
            return {
                "domain_id": None,
                "target": target or "unknown",
                "skipped": False,
            }


def _canonical_to_normalized(canonical: dict[str, Any]) -> dict[str, Any]:
    """
    Convertir CanonicalDocument a formato compatible con handlers.

    Los handlers esperan un diccionario "normalized" con campos como:
    - invoice_number, fecha_emision, vendor_name, subtotal, iva, total, etc.

    Esta función mapea la estructura canónica a ese formato.
    """
    result = dict(canonical)  # Copia base

    # Expandir vendor/buyer info al nivel raíz
    if "vendor" in canonical:
        vendor = canonical.get("vendor", {})
        result.update(
            {
                "vendor": vendor.get("name"),
                "vendor_name": vendor.get("name"),
                "vendor_tax_id": vendor.get("tax_id"),
                "proveedor": vendor.get("name"),
            }
        )

    if "buyer" in canonical:
        buyer = canonical.get("buyer", {})
        result.update(
            {
                "buyer": buyer.get("name"),
                "buyer_name": buyer.get("name"),
                "buyer_tax_id": buyer.get("tax_id"),
                "cliente": buyer.get("name"),
            }
        )

    # Expandir totals
    if "totals" in canonical:
        totals = canonical.get("totals", {})
        result.update(
            {
                "subtotal": totals.get("subtotal"),
                "tax": totals.get("tax"),
                "iva": totals.get("tax"),
                "total": totals.get("total"),
                "amount": totals.get("total"),
            }
        )

    # Expandir bank_tx
    if "bank_tx" in canonical:
        bank_tx = canonical.get("bank_tx", {})
        result.update(
            {
                "bank_tx": bank_tx,
                "amount": bank_tx.get("amount"),
                "importe": bank_tx.get("amount"),
                "direction": bank_tx.get("direction"),
                "narrative": bank_tx.get("narrative"),
                "description": bank_tx.get("narrative"),
                "concepto": bank_tx.get("narrative"),
                "counterparty": bank_tx.get("counterparty"),
                "counterparty_name": bank_tx.get("counterparty"),
            }
        )

    # Expandir payment
    if "payment" in canonical:
        payment = canonical.get("payment", {})
        result.update(
            {
                "payment_method": payment.get("method"),
                "forma_pago": payment.get("method"),
                "payment": payment,
                "iban": payment.get("iban"),
            }
        )

    # Expandir líneas
    if "lines" in canonical:
        result["lines"] = canonical.get("lines")
        result["lineas"] = canonical.get("lines")

    # Expandir product info (Fase C)
    if "product" in canonical:
        product = canonical.get("product", {})
        result.update(
            {
                "product": product,
                "name": product.get("name"),
                "nombre": product.get("name"),
                "price": product.get("price"),
                "precio": product.get("price"),
                "stock": product.get("stock"),
                "cantidad": product.get("stock"),
                "sku": product.get("sku"),
                "codigo": product.get("sku"),
                "category": product.get("category"),
                "categoria": product.get("category"),
                "unit": product.get("unit"),
                "unidad": product.get("unit"),
                "barcode": product.get("barcode"),
                "description": product.get("description"),
                "descripcion": product.get("description"),
            }
        )

    # Expandir expense info (Fase C)
    if "expense" in canonical:
        expense = canonical.get("expense", {})
        result.update(
            {
                "expense": expense,
                "description": expense.get("description") or result.get("description"),
                "descripcion": expense.get("description") or result.get("descripcion"),
                "amount": expense.get("amount") or result.get("amount"),
                "importe": expense.get("amount") or result.get("importe"),
                "expense_date": expense.get("expense_date"),
                "fecha": expense.get("expense_date") or result.get("fecha"),
                "category": expense.get("category") or result.get("category"),
                "categoria": expense.get("category") or result.get("categoria"),
                "subcategory": expense.get("subcategory"),
                "subcategoria": expense.get("subcategory"),
                "payment_method": expense.get("payment_method") or result.get("payment_method"),
                "forma_pago": expense.get("payment_method") or result.get("forma_pago"),
                "vendor": expense.get("vendor"),
                "receipt_number": expense.get("receipt_number"),
            }
        )

    return result


# Global router instance
handlers_router = HandlersRouter()
