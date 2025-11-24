"""Accounting models."""

# Legacy contract modules per tenant:
# - modules: catalog of available modules
# - company_modules: modules a tenant has purchased
# - assigned_modules: which users can access them
from app.models.accounting.chart_of_accounts import (  # noqa: E402
    ChartOfAccounts,
    JournalEntry,
    JournalEntryLine,
)

# Backward compatibility aliases (Spanish names)
PlanCuentas = ChartOfAccounts
AsientoContable = JournalEntry
AsientoLinea = JournalEntryLine

__all__ = [
    "ChartOfAccounts",
    "JournalEntry",
    "JournalEntryLine",
    "PlanCuentas",
    "AsientoContable",
    "AsientoLinea",
]
