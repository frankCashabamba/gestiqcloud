#!/usr/bin/env python3
"""
Complete Spanish to English migration for models.
"""

import shutil
from pathlib import Path
from typing import List, Tuple

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

# Define file renames: (old_path, new_name)
FILE_RENAMES = [
    ("apps/backend/app/models/accounting/plan_cuentas.py", "chart_of_accounts.py"),
    ("apps/backend/app/models/finance/caja.py", "cash_management.py"),
    ("apps/backend/app/models/hr/nomina.py", "payroll.py"),
    ("apps/backend/app/models/hr/empleado.py", "employee.py"),
    ("apps/backend/app/models/core/auditoria_importacion.py", "import_audit.py"),
]

# Define class name replacements in files
CLASS_REPLACEMENTS = {
    "apps/backend/app/models/accounting/chart_of_accounts.py": [
        ("class PlanCuentas", "class ChartOfAccounts"),
        ("class Cuenta", "class Account"),
    ],
    "apps/backend/app/models/finance/cash_management.py": [
        ("class Caja", "class CashManagement"),
        ("class CajaMovimiento", "class CashMovement"),
        ("class CierreCaja", "class CashClosing"),
        ("caja_movimiento_tipo", "cash_movement_type"),
        ("caja_movimiento_categoria", "cash_movement_category"),
        ("cierre_caja_status", "cash_closing_status"),
    ],
    "apps/backend/app/models/hr/payroll.py": [
        ("class Nomina", "class Payroll"),
        ("class NominaConcepto", "class PayrollItem"),
        ("class NominaPlantilla", "class PayrollTemplate"),
        ("nomina_status", "payroll_status"),
        ("nomina_tipo", "payroll_type"),
    ],
    "apps/backend/app/models/hr/employee.py": [
        ("class Empleado", "class Employee"),
    ],
    "apps/backend/app/models/core/import_audit.py": [
        ("class AuditoriaImportacion", "class ImportAudit"),
    ],
}

# Define init.py replacements: (file_path, [(old, new)])
INIT_REPLACEMENTS = {
    "apps/backend/app/models/accounting/__init__.py": [
        ("from .plan_cuentas import", "from .chart_of_accounts import"),
    ],
    "apps/backend/app/models/finance/__init__.py": [
        ("from .caja import", "from .cash_management import"),
    ],
    "apps/backend/app/models/hr/__init__.py": [
        ("from .nomina import", "from .payroll import"),
        ("from .empleado import", "from .employee import"),
    ],
    "apps/backend/app/models/core/__init__.py": [
        ("from .auditoria_importacion import", "from .import_audit import"),
    ],
}


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"{text}")
    print(f"{'='*60}")


def delete_folder(path: Path) -> bool:
    """Delete a folder and its contents."""
    if path.exists() and path.is_dir():
        try:
            shutil.rmtree(path)
            print(f"  ✓ Deleted: {path}")
            return True
        except Exception as e:
            print(f"  ✗ Error deleting {path}: {e}")
            return False
    else:
        print(f"  ✓ Already deleted or not found: {path}")
        return True


def rename_file(old_path: Path, new_name: str) -> bool:
    """Rename a file."""
    if old_path.exists():
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            print(f"  ✓ {old_path.name} → {new_name}")
            return True
        except Exception as e:
            print(f"  ✗ Error renaming {old_path}: {e}")
            return False
    else:
        print(f"  ⓘ Not found: {old_path}")
        return False


def replace_in_file(file_path: Path, replacements: List[Tuple[str, str]]) -> bool:
    """Replace text in a file."""
    if not file_path.exists():
        print(f"    ⓘ File not found: {file_path}")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        for old, new in replacements:
            content = content.replace(old, new)

        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    ✓ Updated: {file_path.name}")
            return True
        else:
            print(f"    ⓘ No replacements made in: {file_path.name}")
            return False

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


def main(execute: bool = False):
    mode = "EXECUTE" if execute else "DRY RUN"
    print_header(f"Spanish → English Migration ({mode})")

    # Step 1: Delete empresa/ folder
    print("\n[STEP 1] Delete empresa/ folder (duplicate)")
    empresa_path = PROJECT_ROOT / "apps/backend/app/models/empresa"
    if execute:
        delete_folder(empresa_path)
    else:
        print(f"  [DRY RUN] Would delete: {empresa_path}")

    # Step 2: Rename files
    print("\n[STEP 2] Rename files")
    for old_path, new_name in FILE_RENAMES:
        full_path = PROJECT_ROOT / old_path
        if execute:
            rename_file(full_path, new_name)
        else:
            if full_path.exists():
                print(f"  [DRY RUN] Would rename: {old_path}")
            else:
                print(f"  [DRY RUN] Not found (skip): {old_path}")

    # Step 3: Update class names in renamed files
    print("\n[STEP 3] Update class names in files")
    for file_path, replacements in CLASS_REPLACEMENTS.items():
        full_path = PROJECT_ROOT / file_path
        if execute:
            replace_in_file(full_path, replacements)
        else:
            if full_path.exists():
                print(f"  [DRY RUN] Would update: {file_path}")

    # Step 4: Update __init__.py files
    print("\n[STEP 4] Update __init__.py imports")
    for file_path, replacements in INIT_REPLACEMENTS.items():
        full_path = PROJECT_ROOT / file_path
        if execute:
            replace_in_file(full_path, replacements)
        else:
            if full_path.exists():
                print(f"  [DRY RUN] Would update: {file_path}")

    # Summary
    print_header("Summary")
    if execute:
        print("✓ Migration COMPLETED!")
        print("\nNext steps:")
        print("1. Update imports in app/ (use VS Code Find & Replace):")
        print("   - from app.models.empresa → from app.models.company")
        print("   - from app.models.accounting.plan_cuentas → .chart_of_accounts")
        print("   - from app.models.finance.caja → .cash_management")
        print("   - from app.models.hr.nomina → .payroll")
        print("   - from app.models.hr.empleado → .employee")
        print("\n2. Update docstrings/comments to English")
        print("\n3. Run tests: pytest tests/ -v")
    else:
        print("DRY RUN - No changes made")
        print("\nTo execute, run: python scripts/migrate.py --execute")

    print()


if __name__ == "__main__":
    import sys

    execute = "--execute" in sys.argv or "-e" in sys.argv

    try:
        main(execute=execute)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
