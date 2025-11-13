"""Validators for expense/receipt imports."""

from datetime import datetime
from typing import Any


def validate_expense(data: dict[str, Any]) -> list[str]:
    """Validate expense import data.

    Args:
        data: Expense data dict with keys:
            - description/descripcion/concepto: Description (required)
            - amount/importe/monto: Amount (required, must be > 0)
            - expense_date/fecha: Date YYYY-MM-DD (required)
            - category/categoria: Category (optional)
            - payment_method/forma_pago: Payment method (optional)
            - vendor/proveedor: Vendor name (optional)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Required: description
    desc = str(
        data.get("description") or data.get("descripcion") or data.get("concepto") or ""
    ).strip()
    if not desc:
        errors.append("Falta descripción del gasto")
    elif len(desc) > 500:
        errors.append("Descripción demasiado larga (máx 500 caracteres)")

    # Required: amount (must be numeric and > 0)
    amount = data.get("amount") or data.get("importe") or data.get("monto")
    if amount is None or amount == "":
        errors.append("Falta monto del gasto")
    else:
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                errors.append("Monto debe ser mayor a 0")
        except (ValueError, TypeError):
            errors.append(f"Monto inválido: '{amount}'")

    # Required: expense_date (YYYY-MM-DD format)
    date_str = str(data.get("expense_date") or data.get("fecha") or "").strip()
    if not date_str:
        errors.append("Falta fecha del gasto")
    else:
        # Try multiple date formats
        valid_date = False
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
            try:
                datetime.strptime(date_str, fmt)
                valid_date = True
                break
            except ValueError:
                continue

        if not valid_date:
            errors.append(f"Fecha inválida: '{date_str}' (use YYYY-MM-DD o DD/MM/YYYY)")

    # Optional: category
    category = str(data.get("category") or data.get("categoria") or "").strip()
    if category and len(category) > 100:
        errors.append("Categoría demasiado larga (máx 100 caracteres)")

    # Optional: payment_method validation
    payment_method = str(data.get("payment_method") or data.get("forma_pago") or "").strip().lower()
    if payment_method:
        valid_methods = {"cash", "card", "transfer", "check", "other"}
        if payment_method not in valid_methods:
            errors.append(
                f"Método de pago inválido: '{payment_method}'. "
                f"Valores válidos: {', '.join(sorted(valid_methods))}"
            )

    # Optional: vendor name validation
    vendor = str(data.get("vendor") or data.get("proveedor") or "").strip()
    if vendor and len(vendor) > 255:
        errors.append("Nombre de proveedor demasiado largo (máx 255 caracteres)")

    # Optional: receipt number validation
    receipt_num = str(data.get("receipt_number") or "").strip()
    if receipt_num and len(receipt_num) > 50:
        errors.append("Número de recibo demasiado largo (máx 50 caracteres)")

    return errors


def validate_expenses_batch(items: list[dict[str, Any]]) -> dict[int, list[str]]:
    """Validate a batch of expenses.

    Args:
        items: List of expense data dicts

    Returns:
        Dict mapping item index to list of errors
    """
    errors_by_index = {}

    for idx, item in enumerate(items):
        item_errors = validate_expense(item)
        if item_errors:
            errors_by_index[idx] = item_errors

    return errors_by_index
