"""
Country-specific validation rules plugin system.
Activates fiscal/accounting rules by country and tenant.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Country(str, Enum):
    """Supported countries."""

    PE = "PE"  # Peru
    CO = "CO"  # Colombia
    CL = "CL"  # Chile
    AR = "AR"  # Argentina
    MX = "MX"  # Mexico
    ES = "ES"  # Spain
    US = "US"  # United States


class TaxType(str, Enum):
    """Tax types by country."""

    IGV = "igv"  # Peru: Impuesto General a las Ventas
    VAT = "vat"  # Standard VAT
    IVA = "iva"  # Spanish/Latin American VAT
    GST = "gst"  # Canadian GST
    SALES_TAX = "sales_tax"  # US Sales Tax


@dataclass
class CountryRule:
    """Single validation rule for a country."""

    rule_id: str
    name: str
    description: str
    countries: list[Country]
    doc_types: list[str]  # "sales_invoice", "expense", etc.

    def validate(self, data: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate data against rule.

        Returns: (is_valid, error_message)
        """
        raise NotImplementedError


@dataclass
class PeruRules:
    """Peru-specific rules."""

    # Tax rules
    TAX_TYPE = TaxType.IGV
    TAX_RATE = 0.18  # 18% IGV

    # Document rules
    REQUIRED_TAX_ID_FORMATS = [
        r"^\d{11}$",  # RUC: 11 digits
        r"^\d{8}$",  # DNI: 8 digits
    ]

    # Invoice rules
    INVOICE_SERIES_FORMAT = r"^[A-Z]{1,3}-\d{1,8}$"  # e.g., "F-001", "FA-1000"

    # Fiscal dates
    FISCAL_YEAR_START = 1  # January
    FISCAL_YEAR_END = 12  # December


@dataclass
class ColombiaRules:
    """Colombia-specific rules."""

    TAX_TYPE = TaxType.IVA
    TAX_RATE = 0.19  # 19% IVA

    # NIT format: 10-12 digits, sometimes with '-' separators
    REQUIRED_TAX_ID_FORMATS = [
        r"^\d{10,12}(-\d)?$",
    ]

    # Invoice format
    INVOICE_SERIES_FORMAT = r"^[A-Z]{1,3}-\d{1,10}$"


@dataclass
class ChileRules:
    """Chile-specific rules."""

    TAX_TYPE = TaxType.IVA
    TAX_RATE = 0.19  # 19% IVA

    # RUT format: XX.XXX.XXX-X (with dashes and check digit)
    REQUIRED_TAX_ID_FORMATS = [
        r"^\d{1,2}\.\d{3}\.\d{3}-[0-9kK]$",
    ]


class CountryRuleSet(ABC):
    """Base class for country-specific rule sets."""

    @abstractmethod
    def get_tax_type(self) -> TaxType:
        """Get tax type for country."""
        pass

    @abstractmethod
    def get_tax_rate(self, doc_type: str) -> float:
        """Get tax rate for document type."""
        pass

    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> tuple[bool, str | None]:
        """Validate tax ID format for country."""
        pass

    @abstractmethod
    def validate_invoice_number(self, invoice_number: str) -> tuple[bool, str | None]:
        """Validate invoice number format."""
        pass

    @abstractmethod
    def validate_fiscal_date(self, date: str) -> tuple[bool, str | None]:
        """Validate fiscal date rules."""
        pass


class PeruRuleSet(CountryRuleSet):
    """Peru-specific rule implementation."""

    def get_tax_type(self) -> TaxType:
        return PeruRules.TAX_TYPE

    def get_tax_rate(self, doc_type: str) -> float:
        # Peru IGV is flat 18%
        if doc_type in ["sales_invoice", "purchase_invoice"]:
            return PeruRules.TAX_RATE
        return 0.0

    def validate_tax_id(self, tax_id: str) -> tuple[bool, str | None]:
        import re

        for pattern in PeruRules.REQUIRED_TAX_ID_FORMATS:
            if re.match(pattern, str(tax_id)):
                return True, None
        return False, "Peru: RUC (11 digits) or DNI (8 digits) required"

    def validate_invoice_number(self, invoice_number: str) -> tuple[bool, str | None]:
        import re

        if re.match(PeruRules.INVOICE_SERIES_FORMAT, str(invoice_number)):
            return True, None
        return False, "Peru: Invoice format should be like F-001, FA-1000"

    def validate_fiscal_date(self, date: str) -> tuple[bool, str | None]:
        # Peru fiscal year is Jan-Dec
        return True, None


class ColombiaRuleSet(CountryRuleSet):
    """Colombia-specific rule implementation."""

    def get_tax_type(self) -> TaxType:
        return ColombiaRules.TAX_TYPE

    def get_tax_rate(self, doc_type: str) -> float:
        if doc_type in ["sales_invoice", "purchase_invoice"]:
            return ColombiaRules.TAX_RATE
        return 0.0

    def validate_tax_id(self, tax_id: str) -> tuple[bool, str | None]:
        import re

        for pattern in ColombiaRules.REQUIRED_TAX_ID_FORMATS:
            if re.match(pattern, str(tax_id)):
                return True, None
        return False, "Colombia: NIT (10-12 digits) required"

    def validate_invoice_number(self, invoice_number: str) -> tuple[bool, str | None]:
        import re

        if re.match(ColombiaRules.INVOICE_SERIES_FORMAT, str(invoice_number)):
            return True, None
        return False, "Colombia: Invoice format should be like F-001, FA-1000"

    def validate_fiscal_date(self, date: str) -> tuple[bool, str | None]:
        return True, None


class CountryRulesRegistry:
    """Registry of country-specific rule sets."""

    def __init__(self):
        self.rule_sets = {
            Country.PE: PeruRuleSet(),
            Country.CO: ColombiaRuleSet(),
        }

    def get_rules(self, country: Country) -> CountryRuleSet | None:
        """Get rule set for country."""
        return self.rule_sets.get(country)

    def validate_document(
        self,
        country: Country,
        doc_type: str,
        data: dict[str, Any],
    ) -> dict[str, str]:
        """
        Validate document against country rules.

        Returns:
            {field: error_message, ...}
        """
        rules = self.get_rules(country)
        if not rules:
            return {}  # No rules for country

        errors = {}

        # Validate tax ID
        if "customer_tax_id" in data:
            is_valid, error = rules.validate_tax_id(data["customer_tax_id"])
            if not is_valid:
                errors["customer_tax_id"] = error

        if "vendor_tax_id" in data:
            is_valid, error = rules.validate_tax_id(data["vendor_tax_id"])
            if not is_valid:
                errors["vendor_tax_id"] = error

        # Validate invoice number
        if "invoice_number" in data and doc_type in ["sales_invoice", "purchase_invoice"]:
            is_valid, error = rules.validate_invoice_number(data["invoice_number"])
            if not is_valid:
                errors["invoice_number"] = error

        # Validate fiscal date
        if "invoice_date" in data:
            is_valid, error = rules.validate_fiscal_date(data["invoice_date"])
            if not is_valid:
                errors["invoice_date"] = error

        # Validate tax amounts
        tax_rate = rules.get_tax_rate(doc_type)
        if tax_rate > 0 and "amount_subtotal" in data and "amount_tax" in data:
            try:
                subtotal = float(data["amount_subtotal"])
                tax = float(data["amount_tax"])
                expected_tax = subtotal * tax_rate
                # Allow 5% variance for rounding
                if abs(tax - expected_tax) > (expected_tax * 0.05):
                    errors["amount_tax"] = (
                        f"Tax amount mismatch. Expected ~{expected_tax:.2f} for {tax_rate:.0%} rate"
                    )
            except (ValueError, TypeError):
                pass

        return errors


# Global registry
country_rules_registry = CountryRulesRegistry()
