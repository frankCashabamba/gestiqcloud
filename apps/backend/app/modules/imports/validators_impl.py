import re
from datetime import date, datetime
from typing import Any

_MONTHS_MAP = {
    "january": 1,
    "jan": 1,
    "enero": 1,
    "ene": 1,
    "february": 2,
    "feb": 2,
    "febrero": 2,
    "march": 3,
    "mar": 3,
    "marzo": 3,
    "april": 4,
    "apr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "june": 6,
    "jun": 6,
    "junio": 6,
    "july": 7,
    "jul": 7,
    "julio": 7,
    "august": 8,
    "aug": 8,
    "agosto": 8,
    "ago": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "septiembre": 9,
    "setiembre": 9,
    "october": 10,
    "oct": 10,
    "octubre": 10,
    "november": 11,
    "nov": 11,
    "noviembre": 11,
    "december": 12,
    "dec": 12,
    "diciembre": 12,
    "dic": 12,
}


def _parse_month_name_date(s: str) -> bool:
    txt = str(s or "").strip().lower()
    if not txt:
        return False
    txt = re.sub(r"[,\.\s]+", " ", txt).strip()
    pats = (
        r"^([a-zA-Z\u00C0-\u017F]+)\s+(\d{1,2})\s+(\d{4})$",
        r"^(\d{1,2})\s+([a-zA-Z\u00C0-\u017F]+)\s+(\d{4})$",
        r"^([a-zA-Z\u00C0-\u017F]+)\s+(\d{4})$",
    )
    for idx, pat in enumerate(pats):
        m = re.match(pat, txt)
        if not m:
            continue
        try:
            if idx == 0:
                month = _MONTHS_MAP.get(m.group(1))
                d, y = int(m.group(2)), int(m.group(3))
            elif idx == 1:
                month = _MONTHS_MAP.get(m.group(2))
                d, y = int(m.group(1)), int(m.group(3))
            else:
                month = _MONTHS_MAP.get(m.group(1))
                d, y = 1, int(m.group(2))
            if not month:
                return False
            _ = date(y, int(month), d)
            return True
        except Exception:
            return False
    return False


try:
    from .validators.country_validators import get_validator_for_country
    from .validators.error_catalog import ERROR_CATALOG
except ImportError:

    def get_validator_for_country(country_code: str):
        raise ValueError(f"Validadores de país no disponibles: {country_code}")

    ERROR_CATALOG = {}


def _is_date_like(v: Any) -> bool:
    s = str(v or "").strip()
    if not s:
        return False
    # Accept common ISO variants produced by Excel/serializers:
    # - YYYY-MM-DD
    # - YYYY-MM-DD HH:MM:SS
    # - YYYY-MM-DDTHH:MM:SS
    # - YYYY-MM-DDTHH:MM:SSZ
    candidates = [s]
    if "T" in s:
        candidates.append(s.split("T", 1)[0])
    if " " in s:
        candidates.append(s.split(" ", 1)[0])
    if s.endswith("Z"):
        candidates.append(s[:-1] + "+00:00")
        if "T" in s:
            candidates.append(s.split("T", 1)[0])

    for candidate in candidates:
        c = str(candidate).strip()
        if not c:
            continue
        try:
            date.fromisoformat(c)
            return True
        except Exception:
            pass
        try:
            _ = datetime.fromisoformat(c)
            return True
        except Exception:
            pass

    m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", s)
    if m:
        d, mth, y = m.groups()
        try:
            _ = datetime(int(y), int(mth), int(d)).date()
            return True
        except Exception:
            return False
    return _parse_month_name_date(s)


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
# Validadores para schema canonico (SPEC-1)
# ============================================================================


def validate_canonical(n: dict[str, Any]) -> list[dict]:
    """
    Validador principal para schema canonico.

    Delega a validadores especificos segun doc_type y usa validacion completa.

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
    Valida bloque totals del schema canonico.

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

    Verifica que cada item tenga code, amount y rate.

    Args:
        tax_breakdown: Lista de items de desglose fiscal

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
