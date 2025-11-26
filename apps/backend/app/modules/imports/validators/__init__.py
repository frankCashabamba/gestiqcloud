"""Validators for imports module"""

import re
from datetime import date, datetime
from typing import Any

try:
    from .country_validators import ECValidator, ESValidator
    from .error_catalog import ERROR_CATALOG

    def get_validator_for_country(country_code: str):
        """Get country-specific validator by country code."""
        validators = {
            "EC": ECValidator,
            "ES": ESValidator,
        }
        validator_class = validators.get(country_code.upper())
        if validator_class is None:
            raise ValueError(f"No validator available for country: {country_code}")
        return validator_class()

except ImportError:

    def get_validator_for_country(country_code: str):
        raise ValueError(f"Validadores de país no disponibles: {country_code}")

    ERROR_CATALOG = {}


def _is_date_like(v: Any) -> bool:
    s = str(v or "").strip()
    if not s:
        return False
    try:
        date.fromisoformat(s)
        return True
    except Exception:
        m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", s)
        if m:
            d, mth, y = m.groups()
            try:
                _ = datetime(int(y), int(mth), int(d)).date()
                return True
            except Exception:
                return False
    return False


def _is_currency(v: Any) -> bool:
    s = str(v or "").strip().upper()
    return bool(re.match(r"^[A-Z]{3}$", s))


def validate_invoices(
    n: dict[str, Any],
    *,
    enable_currency_rule: bool = True,
    country: str | None = None,
) -> list[dict]:
    errors: list[dict] = []

    if not n.get("invoice_number"):
        errors.append({"field": "invoice_number", "msg": "obligatorio"})
    else:
        if country:
            try:
                validator = get_validator_for_country(country)
                country_errors = validator.validate_invoice_number(n["invoice_number"])
                errors.extend(_convert_validation_errors(country_errors))
            except ValueError:
                pass

    if not n.get("invoice_date"):
        errors.append({"field": "invoice_date", "msg": "obligatorio"})
    else:
        if not _is_date_like(n.get("invoice_date")):
            errors.append({"field": "invoice_date", "msg": "fecha invalida"})

    net, tax, total = n.get("net_amount"), n.get("tax_amount"), n.get("total_amount")
    if all(x is not None for x in (net, tax, total)):
        diff = round((net + tax) - total, 2)
        if diff != 0:
            errors.append(
                {
                    "field": "total_amount",
                    "msg": f"no cuadra con base+iva (diferencia: {diff})",
                }
            )

    iti = n.get("issuer_tax_id") or n.get("supplier_tax_id")
    if iti is not None:
        if not str(iti).strip():
            errors.append({"field": "issuer_tax_id", "msg": "valor vacio"})
        elif country:
            try:
                validator = get_validator_for_country(country)
                country_errors = validator.validate_tax_id(str(iti))
                errors.extend(_convert_validation_errors(country_errors))
            except ValueError:
                pass

    tax_rate = n.get("tax_rate")
    if tax_rate is not None and country:
        try:
            validator = get_validator_for_country(country)
            country_errors = validator.validate_tax_rates([float(tax_rate)])
            errors.extend(_convert_validation_errors(country_errors))
        except (ValueError, TypeError):
            pass

    if enable_currency_rule:
        curr = n.get("currency")
        if curr is not None and not _is_currency(curr):
            errors.append({"field": "currency", "msg": "moneda invalida (ISO 4217)"})

    return errors


def _convert_validation_errors(validation_errors: list[dict]) -> list[dict]:
    """Convierte errores del catálogo al formato legacy."""
    return [{"field": err["field"], "msg": err["message"]} for err in validation_errors]


def validate_bank(n: dict[str, Any]) -> list[dict]:
    errors: list[dict] = []
    if not n.get("transaction_date"):
        errors.append({"field": "transaction_date", "msg": "obligatorio"})
    if n.get("amount") is None:
        errors.append({"field": "amount", "msg": "obligatorio"})
    # Optional statement/entry references: if present must be non-empty
    for f in ("statement_id", "entry_ref"):
        if f in n and not str(n.get(f) or "").strip():
            errors.append({"field": f, "msg": "valor vacio"})
    return errors


def validate_expenses(n: dict[str, Any], *, require_categories: bool | str = False) -> list[dict]:
    errors: list[dict] = []
    if not n.get("expense_date"):
        errors.append({"field": "expense_date", "msg": "obligatorio"})
    if n.get("amount") is None:
        errors.append({"field": "amount", "msg": "obligatorio"})
    if require_categories:
        cat = n.get("category") or n.get("categoria")
        if not str(cat or "").strip():
            errors.append({"field": "category", "msg": "categoria requerida por politica"})
    return errors


# ============================================================================
# Validadores para schema canónico (SPEC-1)
# ============================================================================


def validate_canonical(n: dict[str, Any]) -> list[dict]:
    """
    Validador principal para schema canónico.

    Delega a validadores específicos según doc_type y usa validación completa.

    Args:
        n: Documento normalizado (CanonicalDocument)

    Returns:
        Lista de errores con formato {"field": str, "msg": str}
    """
    from app.modules.imports.domain.canonical_schema import validate_canonical as full_validate

    is_valid, error_messages = full_validate(n)

    if is_valid:
        return []

    # Convertir mensajes de string a formato dict
    return [{"field": "general", "msg": msg} for msg in error_messages]


def validate_totals(totals: dict[str, Any] | None) -> list[dict]:
    """
    Valida bloque totals del schema canónico.

    Verifica que subtotal + tax = total con tolerancia de redondeo (0.01).

    Args:
        totals: Diccionario con subtotal, tax, total

    Returns:
        Lista de errores
    """
    errors: list[dict] = []

    if not totals:
        return errors

    subtotal = totals.get("subtotal", 0.0)
    tax = totals.get("tax", 0.0)
    total = totals.get("total", 0.0)

    expected_total = subtotal + tax
    if abs(expected_total - total) > 0.01:
        errors.append(
            {
                "field": "totals.total",
                "msg": f"no cuadra: esperado {expected_total:.2f}, recibido {total:.2f}",
            }
        )

    return errors


def validate_tax_breakdown(tax_breakdown: list[dict[str, Any]] | None) -> list[dict]:
    """
    Valida desglose de impuestos (tax_breakdown).

    Verifica que cada ítem tenga code, amount y rate.

    Args:
        tax_breakdown: Lista de ítems de desglose fiscal

    Returns:
        Lista de errores
    """
    errors: list[dict] = []

    if not tax_breakdown:
        return errors

    for idx, item in enumerate(tax_breakdown):
        if not item.get("code"):
            errors.append({"field": f"tax_breakdown[{idx}].code", "msg": "obligatorio"})
        if item.get("amount") is None:
            errors.append({"field": f"tax_breakdown[{idx}].amount", "msg": "obligatorio"})
        if item.get("rate") is None:
            errors.append({"field": f"tax_breakdown[{idx}].rate", "msg": "obligatorio"})

    return errors


# Import products validator
from .products import validate_product  # noqa: E402

__all__ = [
    "validate_invoices",
    "validate_bank",
    "validate_expenses",
    "validate_canonical",
    "validate_totals",
    "validate_tax_breakdown",
    "validate_product",
    "get_validator_for_country",
    "ERROR_CATALOG",
]
