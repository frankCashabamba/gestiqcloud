from datetime import date, datetime
from typing import Dict, Any, List, Optional
import re


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


def validate_invoices(n: Dict[str, Any], *, enable_currency_rule: bool = True) -> List[dict]:
    errors: List[dict] = []
    if not n.get("invoice_number"):
        errors.append({"field": "invoice_number", "msg": "obligatorio"})
    if not n.get("invoice_date"):
        errors.append({"field": "invoice_date", "msg": "obligatorio"})
    else:
        if not _is_date_like(n.get("invoice_date")):
            errors.append({"field": "invoice_date", "msg": "fecha invalida"})
    net, tax, total = n.get("net_amount"), n.get("tax_amount"), n.get("total_amount")
    if all(x is not None for x in (net, tax, total)) and round((net + tax) - total, 2) != 0:
        errors.append({"field": "total_amount", "msg": "no cuadra con base+iva"})
    # Optional issuer tax id: no error if missing, but if provided, basic sanity
    iti = n.get("issuer_tax_id") or n.get("supplier_tax_id")
    if iti is not None and not str(iti).strip():
        errors.append({"field": "issuer_tax_id", "msg": "valor vacio"})
    # Currency validation if enabled
    if enable_currency_rule:
        curr = n.get("currency")
        if curr is not None and not _is_currency(curr):
            errors.append({"field": "currency", "msg": "moneda invalida (ISO 4217)"})
    return errors


def validate_bank(n: Dict[str, Any]) -> List[dict]:
    errors: List[dict] = []
    if not n.get("transaction_date"):
        errors.append({"field": "transaction_date", "msg": "obligatorio"})
    if n.get("amount") is None:
        errors.append({"field": "amount", "msg": "obligatorio"})
    # Optional statement/entry references: if present must be non-empty
    for f in ("statement_id", "entry_ref"):
        if f in n and not str(n.get(f) or "").strip():
            errors.append({"field": f, "msg": "valor vacio"})
    return errors


def validate_expenses(n: Dict[str, Any], *, require_categories: bool | str = False) -> List[dict]:
    errors: List[dict] = []
    if not n.get("expense_date"):
        errors.append({"field": "expense_date", "msg": "obligatorio"})
    if n.get("amount") is None:
        errors.append({"field": "amount", "msg": "obligatorio"})
    if require_categories:
        cat = n.get("category") or n.get("categoria")
        if not str(cat or "").strip():
            errors.append({"field": "category", "msg": "categoria requerida por politica"})
    return errors
