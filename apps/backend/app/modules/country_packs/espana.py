"""EspanaPack — country pack for Spain (ES)."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from app.modules.documents.domain.models import BuyerInfo, TaxLine, _q2
from app.modules.documents.domain.validation import ValidationError

_NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
_CIF_CONTROL = "JABCDEFGHI"


def _normalize_id(value: str) -> str:
    cleaned = "".join(
        ch for ch in unicodedata.normalize("NFD", value or "") if not unicodedata.combining(ch)
    )
    return "".join(ch for ch in cleaned if ch.isalnum()).upper()


def _validate_dni(value: str) -> bool:
    if not re.fullmatch(r"\d{8}[A-Z]", value):
        return False
    return _NIF_LETTERS[int(value[:8]) % 23] == value[8]


def _validate_nie(value: str) -> bool:
    if not re.fullmatch(r"[XYZ]\d{7}[A-Z]", value):
        return False
    prefix = {"X": "0", "Y": "1", "Z": "2"}[value[0]]
    return _NIF_LETTERS[int(prefix + value[1:8]) % 23] == value[8]


def _validate_cif(value: str) -> bool:
    if not re.fullmatch(r"[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]", value):
        return False
    digits = value[1:8]
    even_sum = sum(int(d) for d in digits[1::2])
    odd_sum = 0
    for d in digits[0::2]:
        n = int(d) * 2
        odd_sum += (n // 10) + (n % 10)
    control_digit = (10 - ((even_sum + odd_sum) % 10)) % 10
    org_letter = value[0]
    control_char = value[8]
    if org_letter in "PQRSNW":
        return _CIF_CONTROL[control_digit] == control_char
    if org_letter in "ABEH":
        return str(control_digit) == control_char
    return str(control_digit) == control_char or _CIF_CONTROL[control_digit] == control_char


def validate_tax_id(value):
    """Validate a Spanish NIF / NIE / CIF."""
    if not value:
        return False
    norm = _normalize_id(value)
    if len(norm) != 9:
        return False
    if norm[0].isdigit():
        return _validate_dni(norm)
    if norm[0] in "XYZ":
        return _validate_nie(norm)
    return _validate_cif(norm)


def default_tax_rates():
    return {
        "GENERAL": Decimal("0.21"),
        "REDUCED": Decimal("0.10"),
        "SUPER_REDUCED": Decimal("0.04"),
        "EXEMPT": Decimal("0"),
    }


class EspanaPack:
    countryCode = "ES"
    version = "1.0.0"
    currency = "EUR"

    def validate_tax_id(self, value):
        return validate_tax_id(value)

    def default_tax_rates(self):
        return default_tax_rates()

    def validate_invoice(self, invoice):
        errs = []

        def _g(key, default=None):
            return (
                invoice.get(key, default)
                if isinstance(invoice, dict)
                else getattr(invoice, key, default)
            )

        currency = (_g("currency") or "").upper()
        if currency and currency != "EUR":
            errs.append(
                ValidationError(
                    code="invalid_currency",
                    message="Spanish invoices must be in EUR",
                    field="currency",
                )
            )
        try:
            if Decimal(str(_g("total") or _g("grandTotal") or 0)) <= 0:
                errs.append(
                    ValidationError(
                        code="invalid_total",
                        message="Invoice total must be positive",
                        field="total",
                    )
                )
        except Exception:
            errs.append(
                ValidationError(
                    code="invalid_total", message="Invoice total is not numeric", field="total"
                )
            )

        buyer = _g("buyer") or {}
        mode = (
            buyer.get("mode") if isinstance(buyer, dict) else getattr(buyer, "mode", None)
        ) or ""
        if mode == "IDENTIFIED":
            tax_id = (
                buyer.get("idNumber")
                if isinstance(buyer, dict)
                else getattr(buyer, "idNumber", None)
            )
            if not validate_tax_id(tax_id):
                errs.append(
                    ValidationError(
                        code="invalid_tax_id",
                        message="Invalid Spanish NIF/NIE/CIF",
                        field="buyer.idNumber",
                    )
                )
        return errs

    # --- Interfaz CountryPack (compatible con DocumentOrchestrator) ---
    def decide_document_type(self, input, cfg):
        allowed = {"FACTURA_SIMPLIFICADA", "FACTURA", "TICKET_NO_FISCAL"}
        desired = (cfg.document_mode_default or "").strip().upper()
        if desired not in allowed:
            desired = ""
        if input.buyer.mode == "IDENTIFIED":
            return desired or "FACTURA"
        return desired or "FACTURA_SIMPLIFICADA"

    def validate(self, input, cfg):
        errs = []
        if (input.currency or "").upper() != "EUR":
            errs.append(
                ValidationError(
                    code="invalid_currency",
                    message="Spanish documents must be in EUR",
                    field="currency",
                )
            )
        if input.buyer.mode == "IDENTIFIED" and not validate_tax_id(input.buyer.idNumber):
            errs.append(
                ValidationError(
                    code="invalid_tax_id",
                    message="Invalid Spanish NIF/NIE/CIF",
                    field="buyer.idNumber",
                )
            )
        return errs

    def build_buyer(self, input, cfg):
        if input.buyer.mode == "CONSUMER_FINAL":
            return BuyerInfo(
                mode="CONSUMER_FINAL",
                idType="NONE",
                idNumber=None,
                name=input.buyer.name or "CONSUMIDOR FINAL",
            )
        return BuyerInfo(
            mode="IDENTIFIED",
            idType=input.buyer.idType or "NIF",
            idNumber=_normalize_id(input.buyer.idNumber or ""),
            name=input.buyer.name,
        )

    def calculate_line_taxes(self, *, line_subtotal, tax_category, cfg):
        profile = cfg.tax_profile or {}
        rule = profile.get(tax_category) or profile.get("DEFAULT") or {}
        rate_raw = rule.get("rate") if isinstance(rule, dict) else None
        if rate_raw is None:
            rate = default_tax_rates()["GENERAL"]
        else:
            rate = Decimal(str(rate_raw))
            if rate > 1:
                rate = rate / Decimal("100")
            if rate < 0:
                rate = Decimal("0")
        amount = _q2(line_subtotal * rate)
        code = str(rule.get("code") if isinstance(rule, dict) else "") or ""
        return [TaxLine(tax="IVA", rate=rate, amount=amount, code=code)]
