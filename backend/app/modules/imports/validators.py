from datetime import date
from typing import Dict, Any, List

def validate_invoices(n: Dict[str, Any]) -> List[dict]:
    errors = []
    if not n.get("invoice_number"):
        errors.append({"field":"invoice_number","msg":"obligatorio"})
    if not n.get("invoice_date"):
        errors.append({"field":"invoice_date","msg":"obligatorio"})
    else:
        try: date.fromisoformat(str(n["invoice_date"]))
        except: errors.append({"field":"invoice_date","msg":"fecha inválida"})
    net, tax, total = n.get("net_amount"), n.get("tax_amount"), n.get("total_amount")
    if all(x is not None for x in (net, tax, total)) and round((net + tax) - total, 2) != 0:
        errors.append({"field":"total_amount","msg":"no cuadra con base+iva"})
    return errors

def validate_bank(n: Dict[str, Any]) -> List[dict]:
    errors = []
    if not n.get("transaction_date"): errors.append({"field":"transaction_date","msg":"obligatorio"})
    if n.get("amount") is None: errors.append({"field":"amount","msg":"obligatorio"})
    return errors

def validate_expenses(n: Dict[str, Any]) -> List[dict]:
    errors = []
    if not n.get("expense_date"): errors.append({"field":"expense_date","msg":"obligatorio"})
    if n.get("amount") is None: errors.append({"field":"amount","msg":"obligatorio"})
    return errors
