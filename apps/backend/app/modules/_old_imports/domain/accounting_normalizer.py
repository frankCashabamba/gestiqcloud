"""
Accounting field normalizer.
Maps source fields to proper accounting semantics per document type.
Prevents expense_date/amount from being left empty due to wrong mapping.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any


class AmountType(str, Enum):
    """Type of amount field."""

    SUBTOTAL = "subtotal"  # Pre-tax amount
    TAX = "tax"  # Tax only
    TOTAL = "total"  # Final amount including tax
    UNIT_PRICE = "unit_price"  # Price per unit
    QUANTITY = "quantity"  # Quantity (for lines)


@dataclass
class AccountingFieldMapping:
    """Mapping of source field to accounting field."""

    source_field: str  # What we got from source
    target_field: str  # Where it should go (canonical)
    field_type: str  # "date", "amount", "text", "reference"
    amount_type: AmountType | None = None  # If amount, which type?
    required: bool = False  # Is it mandatory?
    priority: int = 100  # Higher = more important (for fallbacks)


class AccountingNormalizer:
    """
    Normalizes extracted fields to accounting semantics.
    Ensures mandatory fields like expense_date, amount are never empty.
    """

    # Priority rules for fallback field selection
    DATE_FIELD_PRIORITIES = [
        "invoice_date",
        "expense_date",
        "transaction_date",
        "posting_date",
        "document_date",
        "date_created",
        "fecha",
        "fecha_emisión",
        "fecha_operacion",
    ]

    AMOUNT_FIELD_PRIORITIES = [
        "amount_total",
        "amount",
        "total",
        "monto",
        "importe",
        "total_amount",
        "grand_total",
    ]

    DESCRIPTION_FIELD_PRIORITIES = [
        "description",
        "concepto",
        "detail",
        "detalle",
        "customer_name",
        "vendor_name",
        "reason",
    ]

    def __init__(self):
        # Mapping rules per document type
        self.mappings_by_type = {
            "expense": self._get_expense_mappings(),
            "sales_invoice": self._get_sales_invoice_mappings(),
            "purchase_invoice": self._get_purchase_invoice_mappings(),
            "bank_tx": self._get_bank_tx_mappings(),
        }

    def _get_expense_mappings(self) -> dict[str, AccountingFieldMapping]:
        """Mandatory mappings for expense."""
        return {
            "expense_date": AccountingFieldMapping(
                source_field="",
                target_field="expense_date",
                field_type="date",
                required=True,
                priority=100,
            ),
            "amount": AccountingFieldMapping(
                source_field="",
                target_field="amount",
                field_type="amount",
                amount_type=AmountType.TOTAL,
                required=True,
                priority=100,
            ),
            "description": AccountingFieldMapping(
                source_field="",
                target_field="description",
                field_type="text",
                required=False,
                priority=80,
            ),
        }

    def _get_sales_invoice_mappings(self) -> dict[str, AccountingFieldMapping]:
        """Mandatory mappings for sales invoice."""
        return {
            "invoice_date": AccountingFieldMapping(
                source_field="",
                target_field="invoice_date",
                field_type="date",
                required=True,
                priority=100,
            ),
            "amount_total": AccountingFieldMapping(
                source_field="",
                target_field="amount_total",
                field_type="amount",
                amount_type=AmountType.TOTAL,
                required=True,
                priority=100,
            ),
            "customer_name": AccountingFieldMapping(
                source_field="",
                target_field="customer_name",
                field_type="text",
                required=True,
                priority=90,
            ),
        }

    def _get_purchase_invoice_mappings(self) -> dict[str, AccountingFieldMapping]:
        """Mandatory mappings for purchase invoice."""
        return {
            "invoice_date": AccountingFieldMapping(
                source_field="",
                target_field="invoice_date",
                field_type="date",
                required=True,
                priority=100,
            ),
            "amount_total": AccountingFieldMapping(
                source_field="",
                target_field="amount_total",
                field_type="amount",
                amount_type=AmountType.TOTAL,
                required=True,
                priority=100,
            ),
            "vendor_name": AccountingFieldMapping(
                source_field="",
                target_field="vendor_name",
                field_type="text",
                required=True,
                priority=90,
            ),
        }

    def _get_bank_tx_mappings(self) -> dict[str, AccountingFieldMapping]:
        """Mandatory mappings for bank transaction."""
        return {
            "transaction_date": AccountingFieldMapping(
                source_field="",
                target_field="transaction_date",
                field_type="date",
                required=True,
                priority=100,
            ),
            "amount": AccountingFieldMapping(
                source_field="",
                target_field="amount",
                field_type="amount",
                amount_type=AmountType.TOTAL,
                required=True,
                priority=100,
            ),
        }

    def normalize(
        self,
        data: dict[str, Any],
        doc_type: str,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """
        Normalize extracted data to accounting semantics.

        Args:
            data: Extracted data (mixed source fields and normalized fields)
            doc_type: Document type

        Returns:
            (normalized_data, mapping_used)
            mapping_used: dict of {target_field: source_field_used}
        """
        normalized = data.copy()
        mapping_used = {}

        mappings = self.mappings_by_type.get(doc_type, {})

        for target_field, field_mapping in mappings.items():
            # Check if target already has a value
            if target_field in normalized and normalized[target_field]:
                mapping_used[target_field] = target_field
                continue

            # Try to find a fallback from available fields
            fallback_value = self._find_fallback(
                normalized,
                field_type=field_mapping.field_type,
                target_field=target_field,
            )

            if fallback_value is not None:
                normalized[target_field] = fallback_value
                # Track which field we used for auditing
                mapping_used[target_field] = f"_fallback_{target_field}"
            elif field_mapping.required:
                # Required field is empty - this is an error that validators will catch
                mapping_used[target_field] = "_missing"

        return normalized, mapping_used

    def _find_fallback(
        self,
        data: dict[str, Any],
        field_type: str,
        target_field: str,
    ) -> Any | None:
        """
        Try to find a suitable fallback field for mandatory fields.

        Logic:
        1. For dates: look for any date-looking field
        2. For amounts: look for numeric fields
        3. For text: look for non-empty strings
        """
        if field_type == "date":
            return self._find_date_fallback(data, target_field)
        elif field_type == "amount":
            return self._find_amount_fallback(data)
        elif field_type == "text":
            return self._find_text_fallback(data, target_field)

        return None

    def _find_date_fallback(
        self,
        data: dict[str, Any],
        target_field: str,
    ) -> Any | None:
        """Find a fallback date field."""
        # Use priority list
        for candidate in self.DATE_FIELD_PRIORITIES:
            if candidate in data and data[candidate]:
                return data[candidate]

        # Scan all fields for date-like values
        for key, value in data.items():
            if value and self._looks_like_date(value):
                return value

        return None

    def _find_amount_fallback(self, data: dict[str, Any]) -> Any | None:
        """Find a fallback amount field."""
        # Use priority list
        for candidate in self.AMOUNT_FIELD_PRIORITIES:
            if candidate in data and data[candidate]:
                try:
                    amount = Decimal(str(data[candidate]))
                    if amount > 0:
                        return amount
                except (ValueError, TypeError):
                    continue

        # Scan all fields for numeric values
        for key, value in data.items():
            if value:
                try:
                    amount = Decimal(str(value))
                    if amount > 0:
                        return amount
                except (ValueError, TypeError):
                    continue

        return None

    def _find_text_fallback(
        self,
        data: dict[str, Any],
        target_field: str,
    ) -> str | None:
        """Find a fallback text field."""
        # Use priority list based on target field
        if "date" not in target_field.lower():
            # For descriptions
            for candidate in self.DESCRIPTION_FIELD_PRIORITIES:
                if candidate in data and data[candidate]:
                    return str(data[candidate])

        # Scan all string fields
        for key, value in data.items():
            if isinstance(value, str) and value.strip():
                return value

        return None

    def _looks_like_date(self, value: Any) -> bool:
        """Check if a value looks like a date."""
        if hasattr(value, "year"):  # datetime/date object
            return True

        if not isinstance(value, str):
            return False

        s = value.strip()
        if not s:
            return False

        # Check for common date patterns
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
            r"^\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY or MM/DD/YYYY
            r"^\d{1,2}/\d{1,2}/\d{4}",  # M/D/YYYY
            r"^\d{1,2}-\d{1,2}-\d{4}",  # M-D-YYYY
        ]

        import re

        for pattern in date_patterns:
            if re.match(pattern, s):
                return True

        return False

    def validate_normalization(
        self,
        normalized: dict[str, Any],
        doc_type: str,
    ) -> dict[str, str]:
        """
        Validate that mandatory accounting fields are present.

        Returns:
            Dict of {field: error_message} for missing mandatory fields
        """
        errors = {}

        mappings = self.mappings_by_type.get(doc_type, {})

        for target_field, field_mapping in mappings.items():
            if field_mapping.required:
                value = normalized.get(target_field)
                if value is None or value == "":
                    errors[target_field] = f"Mandatory accounting field '{target_field}' is missing"

        return errors


# Global normalizer instance
accounting_normalizer = AccountingNormalizer()
