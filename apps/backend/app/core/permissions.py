"""Module: permissions.py

Constantes de permisos granulares y helpers legacy.
"""

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Accounting — permisos granulares (usados por require_permission)
# ---------------------------------------------------------------------------
PERM_ACCOUNTING_ENTRY_CREATE = "accounting.entry.create"
PERM_ACCOUNTING_ENTRY_POST = "accounting.entry.post"
PERM_ACCOUNTING_ENTRY_CANCEL = "accounting.entry.cancel"
PERM_ACCOUNTING_ACCOUNT_MANAGE = "accounting.account.manage"
PERM_ACCOUNTING_REPORTS_READ = "accounting.reports.read"
PERM_ACCOUNTING_PERIOD_MANAGE = "accounting.period.manage"

ACCOUNTING_PERMISSIONS: tuple[str, ...] = (
    PERM_ACCOUNTING_ENTRY_CREATE,
    PERM_ACCOUNTING_ENTRY_POST,
    PERM_ACCOUNTING_ENTRY_CANCEL,
    PERM_ACCOUNTING_ACCOUNT_MANAGE,
    PERM_ACCOUNTING_REPORTS_READ,
    PERM_ACCOUNTING_PERIOD_MANAGE,
)


def validar_acceso_empresa(tenant_id: int, current_user):
    """Function validar_acceso_empresa - auto-generated docstring."""
    if not current_user.is_superadmin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
