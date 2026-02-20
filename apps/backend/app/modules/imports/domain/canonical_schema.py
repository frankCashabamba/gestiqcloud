"""
Canonical schema definition for all document types.
Defines required fields, validators, and domain rules for each doc type.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any


class DocumentType(str, Enum):
    """Supported document types."""

    SALES_INVOICE = "sales_invoice"
    PURCHASE_INVOICE = "purchase_invoice"
    EXPENSE = "expense"
    BANK_TX = "bank_tx"
    PRODUCT = "product"
    RECIPE = "recipe"


# Backward-compatible runtime alias used by legacy extractors/CLI.
# NOTE: keep it callable (CanonicalDocument(**payload)) by aliasing built-in dict.
CanonicalDocument = dict[str, Any]


@dataclass
class FieldRule:
    """Single validation rule for a field."""

    name: str
    validator: Callable[[Any], tuple[bool, str | None]]  # (is_valid, error_msg)
    required: bool = False

    def validate(self, value: Any) -> tuple[bool, str | None]:
        """Apply validator, handling None for optional fields."""
        if value is None or value == "":
            if self.required:
                return False, f"{self.name} is required"
            return True, None
        return self.validator(value)


@dataclass
class CanonicalField:
    """Schema field definition."""

    name: str
    canonical_name: str  # Standardized name (e.g., 'invoice_date', 'amount_total')
    required: bool = False
    rules: list[FieldRule] = None
    aliases: list[str] = None  # Alternative header names (case-insensitive)
    data_type: str = "string"  # string, number, date, decimal

    def __post_init__(self):
        if self.rules is None:
            self.rules = []
        if self.aliases is None:
            self.aliases = []

    def validate(self, value: Any) -> tuple[bool, list[str]]:
        """Validate value against all rules."""
        errors = []

        # Check required
        if self.required and (value is None or value == ""):
            errors.append(f"{self.canonical_name} is required")
            return False, errors

        if value is None or value == "":
            return True, []

        # Check each rule
        for rule in self.rules:
            is_valid, error_msg = rule.validate(value)
            if not is_valid:
                errors.append(error_msg)

        return len(errors) == 0, errors


@dataclass
class CanonicalSchema:
    """Schema for a document type."""

    doc_type: DocumentType
    fields: dict[str, CanonicalField]
    required_fields: list[str]  # List of field names that must be present

    def validate(self, data: dict[str, Any]) -> tuple[bool, dict[str, list[str]]]:
        """
        Validate document against schema.
        Returns (is_valid, errors_by_field)
        """
        errors_by_field = {}

        # Check required fields
        for field_name in self.required_fields:
            if field_name not in self.fields:
                continue
            value = data.get(field_name)
            if value is None or value == "":
                if field_name not in errors_by_field:
                    errors_by_field[field_name] = []
                errors_by_field[field_name].append(f"{field_name} is required")

        # Validate each field
        for field_name, field_def in self.fields.items():
            value = data.get(field_name)
            is_valid, field_errors = field_def.validate(value)
            if not is_valid:
                if field_name not in errors_by_field:
                    errors_by_field[field_name] = []
                errors_by_field[field_name].extend(field_errors)

        return len(errors_by_field) == 0, errors_by_field


# Validators
def _is_not_empty(val: Any) -> tuple[bool, str | None]:
    """Check value is not empty."""
    s = str(val).strip()
    return len(s) > 0, None if len(s) > 0 else "Cannot be empty"


def _is_number(val: Any) -> tuple[bool, str | None]:
    """Check if value is a valid number."""
    try:
        float(val)
        return True, None
    except (ValueError, TypeError):
        return False, "Must be a valid number"


def _is_positive(val: Any) -> tuple[bool, str | None]:
    """Check if value is positive."""
    try:
        num = float(val)
        return num > 0, None if num > 0 else "Must be positive"
    except (ValueError, TypeError):
        return False, "Must be a valid positive number"


def _is_date(val: Any) -> tuple[bool, str | None]:
    """Check if value is a valid date (flexible parsing)."""
    from datetime import datetime

    if isinstance(val, str):
        sval = val.strip()
        if not sval:
            return False, "Date format not recognized (try YYYY-MM-DD)"
        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%Y.%m.%d",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%B %Y",
            "%b %Y",
        ]
        for candidate in (sval.replace(",", ""), sval.split()[0]):
            for fmt in formats:
                try:
                    datetime.strptime(candidate, fmt)
                    return True, None
                except ValueError:
                    continue
        return False, "Date format not recognized (try YYYY-MM-DD)"

    # datetime or date object is OK
    return hasattr(val, "year"), "Must be a valid date"


def _is_tax_id(val: Any) -> tuple[bool, str | None]:
    """Check if value looks like a tax ID (RUC, NIT, CIF, etc)."""
    s = str(val).strip()
    # At least 5 chars, alphanumeric
    return (
        len(s) >= 5 and s.replace("-", "").replace(" ", "").isalnum(),
        "Tax ID must be at least 5 characters",
    )


# Schemas for each document type

SALES_INVOICE_SCHEMA = CanonicalSchema(
    doc_type=DocumentType.SALES_INVOICE,
    fields={
        "invoice_number": CanonicalField(
            name="invoice_number",
            canonical_name="invoice_number",
            required=True,
            aliases=["factura", "invoice", "numero", "number", "inv_no"],
            rules=[FieldRule("not_empty", _is_not_empty)],
        ),
        "invoice_date": CanonicalField(
            name="invoice_date",
            canonical_name="invoice_date",
            required=True,
            aliases=["fecha", "date", "invoice_date"],
            data_type="date",
            rules=[FieldRule("is_date", _is_date)],
        ),
        "customer_name": CanonicalField(
            name="customer_name",
            canonical_name="customer_name",
            required=True,
            aliases=["cliente", "customer", "buyer", "comprador"],
            rules=[FieldRule("not_empty", _is_not_empty)],
        ),
        "customer_tax_id": CanonicalField(
            name="customer_tax_id",
            canonical_name="customer_tax_id",
            aliases=["customer_ruc", "customer_nit", "ruc_cliente", "customer_id"],
            rules=[FieldRule("is_tax_id", _is_tax_id)],
        ),
        "amount_subtotal": CanonicalField(
            name="amount_subtotal",
            canonical_name="amount_subtotal",
            required=True,
            aliases=["subtotal", "subtotal_amount"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number), FieldRule("is_positive", _is_positive)],
        ),
        "amount_tax": CanonicalField(
            name="amount_tax",
            canonical_name="amount_tax",
            aliases=["iva", "tax", "impuesto", "igv"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number)],
        ),
        "amount_total": CanonicalField(
            name="amount_total",
            canonical_name="amount_total",
            required=True,
            aliases=["total", "grand_total", "monto_total"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number), FieldRule("is_positive", _is_positive)],
        ),
        "description": CanonicalField(
            name="description",
            canonical_name="description",
            aliases=["concepto", "detail", "descripcion"],
        ),
    },
    required_fields=[
        "invoice_number",
        "invoice_date",
        "customer_name",
        "amount_subtotal",
        "amount_total",
    ],
)

PURCHASE_INVOICE_SCHEMA = CanonicalSchema(
    doc_type=DocumentType.PURCHASE_INVOICE,
    fields={
        "invoice_number": CanonicalField(
            name="invoice_number",
            canonical_name="invoice_number",
            required=True,
            aliases=["factura", "invoice", "numero", "number"],
            rules=[FieldRule("not_empty", _is_not_empty)],
        ),
        "invoice_date": CanonicalField(
            name="invoice_date",
            canonical_name="invoice_date",
            required=True,
            aliases=["fecha", "date"],
            data_type="date",
            rules=[FieldRule("is_date", _is_date)],
        ),
        "vendor_name": CanonicalField(
            name="vendor_name",
            canonical_name="vendor_name",
            required=True,
            aliases=["proveedor", "vendor", "supplier"],
            rules=[FieldRule("not_empty", _is_not_empty)],
        ),
        "vendor_tax_id": CanonicalField(
            name="vendor_tax_id",
            canonical_name="vendor_tax_id",
            aliases=["vendor_ruc", "vendor_nit", "ruc_proveedor", "supplier_id"],
            rules=[FieldRule("is_tax_id", _is_tax_id)],
        ),
        "amount_subtotal": CanonicalField(
            name="amount_subtotal",
            canonical_name="amount_subtotal",
            required=True,
            aliases=["subtotal"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number), FieldRule("is_positive", _is_positive)],
        ),
        "amount_tax": CanonicalField(
            name="amount_tax",
            canonical_name="amount_tax",
            aliases=["iva", "tax", "impuesto"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number)],
        ),
        "amount_total": CanonicalField(
            name="amount_total",
            canonical_name="amount_total",
            required=True,
            aliases=["total"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number), FieldRule("is_positive", _is_positive)],
        ),
    },
    required_fields=[
        "invoice_number",
        "invoice_date",
        "vendor_name",
        "amount_subtotal",
        "amount_total",
    ],
)

EXPENSE_SCHEMA = CanonicalSchema(
    doc_type=DocumentType.EXPENSE,
    fields={
        "expense_date": CanonicalField(
            name="expense_date",
            canonical_name="expense_date",
            required=True,
            aliases=["fecha", "date", "expense_date"],
            data_type="date",
            rules=[FieldRule("is_date", _is_date)],
        ),
        "description": CanonicalField(
            name="description",
            canonical_name="description",
            required=True,
            aliases=["concepto", "detail", "gasto", "expense", "descripcion"],
            rules=[FieldRule("not_empty", _is_not_empty)],
        ),
        "amount": CanonicalField(
            name="amount",
            canonical_name="amount",
            required=True,
            aliases=["monto", "amount", "importe"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number), FieldRule("is_positive", _is_positive)],
        ),
        "category": CanonicalField(
            name="category",
            canonical_name="category",
            aliases=["categoria", "expense_category", "tipo"],
        ),
        "receipt_number": CanonicalField(
            name="receipt_number",
            canonical_name="receipt_number",
            aliases=["recibo", "receipt", "receipt_no"],
        ),
        "vendor_name": CanonicalField(
            name="vendor_name",
            canonical_name="vendor_name",
            aliases=["proveedor", "vendor"],
        ),
    },
    required_fields=["expense_date", "description", "amount"],
)

BANK_TX_SCHEMA = CanonicalSchema(
    doc_type=DocumentType.BANK_TX,
    fields={
        "transaction_date": CanonicalField(
            name="transaction_date",
            canonical_name="transaction_date",
            required=True,
            aliases=["fecha", "date", "tx_date"],
            data_type="date",
            rules=[FieldRule("is_date", _is_date)],
        ),
        "amount": CanonicalField(
            name="amount",
            canonical_name="amount",
            required=True,
            aliases=["monto", "importe", "amount"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number)],
        ),
        "description": CanonicalField(
            name="description",
            canonical_name="description",
            aliases=["concepto", "detail", "descripcion"],
        ),
        "account_number": CanonicalField(
            name="account_number",
            canonical_name="account_number",
            aliases=["cuenta", "account", "account_no"],
        ),
        "balance": CanonicalField(
            name="balance",
            canonical_name="balance",
            aliases=["saldo", "balance"],
            data_type="decimal",
            rules=[FieldRule("is_number", _is_number)],
        ),
        "reference": CanonicalField(
            name="reference",
            canonical_name="reference",
            aliases=["referencia", "reference", "ref"],
        ),
        "direction": CanonicalField(
            name="direction",
            canonical_name="direction",
            aliases=["tipo", "direction", "debit_credit"],
        ),
    },
    required_fields=["transaction_date", "amount"],
)

# Mapping of document type to schema
SCHEMAS_BY_TYPE: dict[str, CanonicalSchema] = {
    DocumentType.SALES_INVOICE.value: SALES_INVOICE_SCHEMA,
    DocumentType.PURCHASE_INVOICE.value: PURCHASE_INVOICE_SCHEMA,
    DocumentType.EXPENSE.value: EXPENSE_SCHEMA,
    DocumentType.BANK_TX.value: BANK_TX_SCHEMA,
}


def get_schema(doc_type: str) -> CanonicalSchema | None:
    """Get schema for a document type."""
    return SCHEMAS_BY_TYPE.get(doc_type.lower())


def _normalize_doc_type_for_schema(doc_type: Any) -> str:
    """Map runtime doc_type aliases to schema keys."""
    value = str(doc_type or "").strip().lower()
    if value in ("invoice", "invoices", "sales_invoice"):
        return DocumentType.SALES_INVOICE.value
    if value in ("purchase_invoice", "supplier_invoice"):
        return DocumentType.PURCHASE_INVOICE.value
    if value in ("expense", "expenses", "expense_receipt"):
        return DocumentType.EXPENSE.value
    if value in ("bank", "bank_tx", "bank_transactions", "transaction"):
        return DocumentType.BANK_TX.value
    if value in ("product", "products"):
        return DocumentType.PRODUCT.value
    return value


def validate_canonical(data: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    """
    Validate canonical document payload used by import tasks.

    Returns:
        (is_valid, errors) where errors are dicts: {"field": str, "msg": str}
    """
    if not isinstance(data, dict):
        return False, [{"field": "document", "msg": "invalid payload type"}]

    normalized_doc_type = _normalize_doc_type_for_schema(data.get("doc_type"))

    # Product docs in this codebase are often nested under "product".
    if normalized_doc_type == DocumentType.PRODUCT.value:
        product = data.get("product") if isinstance(data.get("product"), dict) else data
        name = str((product or {}).get("name") or "").strip()
        if not name:
            return False, [{"field": "product.name", "msg": "name is required"}]
        return True, []

    schema = get_schema(normalized_doc_type)
    if not schema:
        # Unknown/other docs are allowed to pass through pipeline.
        return True, []

    payload = data
    # Optional compatibility mapping for invoice-like payloads.
    if normalized_doc_type in (
        DocumentType.SALES_INVOICE.value,
        DocumentType.PURCHASE_INVOICE.value,
    ):
        payload = dict(data)
        # Common aliases from OCR/legacy extractors for invoice id.
        if not payload.get("invoice_number"):
            payload["invoice_number"] = (
                data.get("invoice_number")
                or data.get("invoice")
                or data.get("numero")
                or data.get("numero_factura")
                or data.get("document_number")
                or data.get("doc_number")
                or data.get("nro")
                or data.get("nro_factura")
                or data.get("comprobante")
                or data.get("folio")
                or data.get("reference")
                or data.get("receipt_number")
                or data.get("payment_reference")
            )
        if not payload.get("invoice_date") and data.get("issue_date"):
            payload["invoice_date"] = data.get("issue_date")
        if not payload.get("invoice_date"):
            payload["invoice_date"] = (
                data.get("invoice_date")
                or data.get("fecha")
                or data.get("date")
                or data.get("issueDate")
            )
        if "customer_name" not in payload and data.get("customer"):
            customer = data.get("customer")
            payload["customer_name"] = (
                customer.get("name") if isinstance(customer, dict) else customer
            )
        if "vendor_name" not in payload and data.get("vendor"):
            vendor = data.get("vendor")
            payload["vendor_name"] = vendor.get("name") if isinstance(vendor, dict) else vendor
        totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}
        if payload.get("amount_subtotal") is None and totals.get("subtotal") is not None:
            payload["amount_subtotal"] = totals.get("subtotal")
        if payload.get("amount_tax") is None and totals.get("tax") is not None:
            payload["amount_tax"] = totals.get("tax")
        if payload.get("amount_total") is None and totals.get("total") is not None:
            payload["amount_total"] = totals.get("total")
        if "amount_total" not in payload and data.get("amount") is not None:
            payload["amount_total"] = data.get("amount")
        if "amount_total" not in payload and data.get("total") is not None:
            payload["amount_total"] = data.get("total")
        if "amount_total" not in payload and data.get("importe") is not None:
            payload["amount_total"] = data.get("importe")
        if "amount_subtotal" not in payload and data.get("subtotal") is not None:
            payload["amount_subtotal"] = data.get("subtotal")
        if "amount_subtotal" not in payload and payload.get("amount_total") is not None:
            payload["amount_subtotal"] = payload.get("amount_total")
        if "amount_tax" not in payload:
            payload["amount_tax"] = data.get("tax") or data.get("iva") or totals.get("tax") or 0
        if "invoice_date" not in payload and data.get("date"):
            payload["invoice_date"] = data.get("date")
        if "invoice_date" not in payload and totals.get("date"):
            payload["invoice_date"] = totals.get("date")
        if "customer_name" not in payload:
            payload["customer_name"] = (
                data.get("customer_name")
                or data.get("cliente")
                or data.get("buyer")
                or data.get("vendor_name")
                or data.get("proveedor")
            )
        if "vendor_name" not in payload:
            payload["vendor_name"] = (
                data.get("vendor_name")
                or data.get("proveedor")
                or data.get("supplier")
                or data.get("customer_name")
                or data.get("cliente")
            )
        # Last-resort deterministic fallback for noisy OCR invoices.
        # Keeps idempotency across retries and avoids hard-failing complete batches.
        if not payload.get("invoice_number"):
            base = "|".join(
                [
                    str(payload.get("invoice_date") or ""),
                    str(payload.get("amount_total") or ""),
                    str(payload.get("customer_name") or payload.get("vendor_name") or ""),
                ]
            )
            if base.strip("|"):
                payload["invoice_number"] = (
                    f"AUTO-{sha256(base.encode('utf-8')).hexdigest()[:10].upper()}"
                )

    # Compatibility mapping for bank tx payloads produced by parsers in this module.
    if normalized_doc_type == DocumentType.BANK_TX.value:
        payload = dict(data)
        bank_tx = data.get("bank_tx") if isinstance(data.get("bank_tx"), dict) else {}
        if not payload.get("transaction_date"):
            payload["transaction_date"] = (
                data.get("transaction_date")
                or data.get("issue_date")
                or data.get("value_date")
                or data.get("date")
                or data.get("fecha")
                or data.get("fecha_valor")
                or data.get("fecha_operacion")
                or data.get("fecha de la operacion")
                or data.get("fecha de operación")
                or data.get("fecha de envio")
                or data.get("fecha de envío")
                or data.get("fecha_envio")
                or bank_tx.get("value_date")
                or bank_tx.get("transaction_date")
                or bank_tx.get("date")
            )
        if payload.get("amount") is None:
            payload["amount"] = (
                data.get("amount")
                or data.get("importe")
                or bank_tx.get("amount")
                or bank_tx.get("importe")
            )
        if not payload.get("description"):
            payload["description"] = (
                data.get("description")
                or data.get("concepto")
                or bank_tx.get("narrative")
                or bank_tx.get("description")
            )

    is_valid, errors_by_field = schema.validate(payload)
    if is_valid:
        return True, []

    errors: list[dict[str, str]] = []
    for field, messages in errors_by_field.items():
        for msg in messages:
            errors.append({"field": str(field), "msg": str(msg)})
    return False, errors


def build_routing_proposal(
    canonical_doc: dict[str, Any],
    *,
    category_code: str | None = None,
    account: str | None = None,
    confidence: float | None = None,
    reason: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """
    Build a lightweight routing proposal for legacy OCR extractors.

    This keeps compatibility with old extractors that attach:
    canonical["routing_proposal"] = build_routing_proposal(...)
    """
    doc_type = str(canonical_doc.get("doc_type") or "other")
    out: dict[str, Any] = {
        "doc_type": doc_type,
        "category_code": category_code or "OTROS",
        "account": account or "6290",
        "confidence": float(confidence if confidence is not None else 0.5),
        "reason": reason or "auto-routing",
    }
    if extra:
        out.update(extra)
    return out
