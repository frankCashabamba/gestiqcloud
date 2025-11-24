#!/usr/bin/env python3
"""
Update imports across the codebase after renaming files.
"""

import re
from pathlib import Path
from typing import List, Tuple

# Define import replacements
IMPORT_REPLACEMENTS = [
    # Formato: (old_import_pattern, new_import, description)
    # From empresa
    (
        r"from\s+app\.models\.empresa\s+import",
        "from app.models.company import",
        "Empresa -> Company",
    ),
    # From core.facturacion
    (
        r"from\s+app\.models\.core\.facturacion\s+import",
        "from app.models.core.billing import",  # O donde vaya facturacion
        "core.facturacion -> core.billing",
    ),
    # From core.modulo
    (
        r"from\s+app\.models\.core\.modulo\s+import",
        "from app.models.platform.module import",  # O donde vaya modulo
        "core.modulo -> platform.module",
    ),
    # From accounting.plan_cuentas
    (
        r"from\s+app\.models\.accounting\.plan_cuentas\s+import",
        "from app.models.accounting.chart_of_accounts import",
        "accounting.plan_cuentas -> accounting.chart_of_accounts",
    ),
    # From finance.caja
    (
        r"from\s+app\.models\.finance\.caja\s+import",
        "from app.models.finance.cash_management import",
        "finance.caja -> finance.cash_management",
    ),
    # From hr.nomina
    (
        r"from\s+app\.models\.hr\.nomina\s+import",
        "from app.models.hr.payroll import",
        "hr.nomina -> hr.payroll",
    ),
    # From hr.empleado
    (
        r"from\s+app\.models\.hr\.empleado\s+import",
        "from app.models.hr.employee import",
        "hr.empleado -> hr.employee",
    ),
    # From core.auditoria_importacion
    (
        r"from\s+app\.models\.core\.auditoria_importacion\s+import",
        "from app.models.core.import_audit import",
        "core.auditoria_importacion -> core.import_audit",
    ),
]

# Class name replacements
CLASS_REPLACEMENTS = [
    (r"\bPlanCuentas\b", "ChartOfAccounts", "PlanCuentas -> ChartOfAccounts"),
    (r"\bCaja\b", "CashManagement", "Caja -> CashManagement"),
    (r"\bNomina\b", "Payroll", "Nomina -> Payroll"),
    (r"\bEmpleado\b", "Employee", "Empleado -> Employee"),
    (r"\bEmpresa\b", "Company", "Empresa -> Company"),
    (r"\bFacturacion\b", "Billing", "Facturacion -> Billing"),
    (r"\bModulo\b", "Module", "Modulo -> Module"),
    (r"\bAuditoriaImportacion\b", "ImportAudit", "AuditoriaImportacion -> ImportAudit"),
]

# Enum replacements
ENUM_REPLACEMENTS = [
    (
        r"caja_movimiento_tipo",
        "cash_movement_type",
        "caja_movimiento_tipo -> cash_movement_type",
    ),
    (
        r"caja_movimiento_categoria",
        "cash_movement_category",
        "caja_movimiento_categoria -> cash_movement_category",
    ),
    (
        r"cierre_caja_status",
        "cash_closing_status",
        "cierre_caja_status -> cash_closing_status",
    ),
    (r"nomina_status", "payroll_status", "nomina_status -> payroll_status"),
    (r"nomina_tipo", "payroll_type", "nomina_tipo -> payroll_type"),
    (r"movimiento_tipo", "movement_type", "movimiento_tipo -> movement_type"),
    (r"movimiento_estado", "movement_status", "movimiento_estado -> movement_status"),
]


def should_process_file(filepath: str) -> bool:
    """Check if file should be processed."""
    if not filepath.endswith(".py"):
        return False
    if "__pycache__" in filepath:
        return False
    if ".pyc" in filepath:
        return False
    return True


def process_file(
    filepath: str, replacements: List[Tuple[str, str, str]], dry_run: bool = True
) -> Tuple[bool, str]:
    """
    Process a file with replacements.
    Returns: (modified, message)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            original_content = f.read()

        modified_content = original_content
        changes_made = []

        for pattern, replacement, description in replacements:
            new_content = re.sub(pattern, replacement, modified_content)
            if new_content != modified_content:
                changes_made.append(description)
                modified_content = new_content

        if not changes_made:
            return False, "No changes"

        if not dry_run:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(modified_content)

        return True, f"Modified: {', '.join(changes_made)}"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    import sys

    # Parse arguments
    dry_run = "--apply" not in sys.argv
    mode = "DRY RUN" if dry_run else "APPLY CHANGES"

    app_root = Path("apps/backend/app")

    if not app_root.exists():
        print(f"Error: {app_root} not found")
        sys.exit(1)

    print(f"{'='*70}")
    print(f"Update Imports - {mode}")
    print(f"{'='*70}")
    print()

    # Process files
    modified_files = []
    total_files = 0

    for filepath in app_root.rglob("*.py"):
        if not should_process_file(str(filepath)):
            continue

        total_files += 1

        # Try import replacements
        modified, message = process_file(str(filepath), IMPORT_REPLACEMENTS, dry_run)

        if modified:
            rel_path = filepath.relative_to(app_root.parent)
            print(f"✓ {rel_path}")
            print(f"  {message}")
            modified_files.append(str(filepath))

    print()
    print(f"{'='*70}")
    print(f"Results: {len(modified_files)} modified out of {total_files} files")
    print(f"{'='*70}")

    if dry_run:
        print()
        print("To apply changes, run: python scripts/update_imports.py --apply")
    else:
        print()
        print("Changes applied successfully!")


if __name__ == "__main__":
    main()
