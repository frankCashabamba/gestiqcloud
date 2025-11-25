#!/usr/bin/env python3
"""
Refactoring Script - Spanish to English
Backend App Refactorization Assistant

Usage:
    python refactor_script.py --analyze    # Analyze changes needed
    python refactor_script.py --execute    # Apply changes
    python refactor_script.py --verify     # Verify changes
"""

import sys
from pathlib import Path
from typing import Dict, List

# Configuration
REPO_ROOT = Path(__file__).parent
APP_ROOT = REPO_ROOT / "apps" / "backend" / "app"

# Mapping of old imports -> new imports
IMPORT_MAPPINGS = {
    # Models
    "from app.models.company.empresa import": "from app.models.company.company import",
    "from app.models.company.usuarioempresa import UsuarioEmpresa": "from app.models.company.company_user import CompanyUser as UsuarioEmpresa",
    # Modules
    "from app.modules.proveedores": "from app.modules.suppliers",
    "from app.modules.gastos": "from app.modules.expenses",
    "from app.modules.empresa": "from app.modules.company",
    "from app.modules.usuarios": "from app.modules.users",
    "from app.modules.rrhh": "from app.modules.hr",
    # Schemas
    "from app.schemas.empresa import": "from app.schemas.company import",
    "from app.schemas.rol_empresa import": "from app.schemas.company_role import",
    "from app.schemas.hr_nomina import": "from app.schemas.payroll import",
}

# Alias mappings to remove
ALIAS_REMOVALS = {
    'alias="proveedor_id"': "",
    'alias="categoria_gasto_id"': "",
}

# Settings label replacements
LABEL_REPLACEMENTS = {
    '"proveedores"': '"suppliers"',
    '"gastos"': '"expenses"',
    '"rrhh"': '"hr"',
    '"label": "Proveedor"': '"label": "Supplier"',
    '"label": "Lote del proveedor"': '"label": "Supplier Batch"',
    '"label": "Lote Proveedor"': '"label": "Supplier Batch"',
    '"field": "proveedor"': '"field": "supplier"',
    '"field": "lote_proveedor"': '"field": "supplier_batch"',
}


def find_python_files(start_path: Path = APP_ROOT) -> List[Path]:
    """Find all Python files in app directory."""
    return list(start_path.rglob("*.py"))


def analyze_file(filepath: Path) -> Dict[str, List[str]]:
    """Analyze a file for required changes."""
    changes = {
        "imports": [],
        "aliases": [],
        "labels": [],
        "docstrings": [],
    }

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return changes

    # Check for imports to change
    for old, new in IMPORT_MAPPINGS.items():
        if old in content:
            changes["imports"].append(f"{old} -> {new}")

    # Check for aliases to remove
    for alias_pattern in ALIAS_REMOVALS:
        if alias_pattern in content:
            changes["aliases"].append(alias_pattern)

    # Check for labels to update
    for old_label, new_label in LABEL_REPLACEMENTS.items():
        if old_label in content:
            changes["labels"].append(f"{old_label} -> {new_label}")

    return changes


def analyze_project() -> Dict[Path, Dict]:
    """Analyze entire project for changes needed."""
    print("🔍 Analyzing project structure...\n")

    files = find_python_files()
    changes_needed = {}

    for filepath in files:
        changes = analyze_file(filepath)
        if any(changes.values()):
            rel_path = filepath.relative_to(REPO_ROOT)
            changes_needed[rel_path] = changes

    return changes_needed


def print_analysis(changes_needed: Dict[Path, Dict]):
    """Print analysis results."""
    print(f"\n📊 ANALYSIS RESULTS\n{'='*60}")

    import_count = sum(len(c["imports"]) for c in changes_needed.values())
    alias_count = sum(len(c["aliases"]) for c in changes_needed.values())
    label_count = sum(len(c["labels"]) for c in changes_needed.values())

    print(f"\nFiles needing changes: {len(changes_needed)}")
    print(f"Import changes needed: {import_count}")
    print(f"Alias removals needed: {alias_count}")
    print(f"Label updates needed: {label_count}")

    print(f"\n{'='*60}\nFILES TO UPDATE:\n")

    for filepath, changes in sorted(changes_needed.items()):
        print(f"\n📄 {filepath}")
        if changes["imports"]:
            print("  Imports:")
            for change in changes["imports"][:3]:  # Show first 3
                print(f"    • {change}")
            if len(changes["imports"]) > 3:
                print(f"    ... and {len(changes['imports'])-3} more")

        if changes["aliases"]:
            print("  Aliases to remove:")
            for alias in changes["aliases"]:
                print(f"    • {alias}")

        if changes["labels"]:
            print("  Labels to update:")
            for label in changes["labels"][:2]:
                print(f"    • {label}")
            if len(changes["labels"]) > 2:
                print(f"    ... and {len(changes['labels'])-2} more")


def apply_import_changes(filepath: Path):
    """Apply import changes to a file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        original = content

        for old, new in IMPORT_MAPPINGS.items():
            content = content.replace(old, new)

        for alias_pattern, replacement in ALIAS_REMOVALS.items():
            content = content.replace(alias_pattern, replacement)

        for old_label, new_label in LABEL_REPLACEMENTS.items():
            content = content.replace(old_label, new_label)

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

    return False


def execute_refactoring():
    """Execute refactoring changes."""
    print("🚀 Executing refactoring...\n")

    files = find_python_files()
    changed_files = []

    for filepath in files:
        if apply_import_changes(filepath):
            changed_files.append(filepath)
            print(f"✅ {filepath.relative_to(REPO_ROOT)}")

    print(f"\n✅ Updated {len(changed_files)} files")
    return changed_files


def verify_refactoring():
    """Verify refactoring completion."""
    print("✓ Verifying refactoring...\n")

    remaining = {}
    files = find_python_files()

    # Check for remaining old patterns
    old_patterns = [
        "from app.models.company.empresa",
        "from app.models.company.usuarioempresa",
        "from app.modules.proveedores",
        "from app.modules.gastos",
        'alias="proveedor_id"',
        'alias="categoria_gasto_id"',
    ]

    for filepath in files:
        try:
            content = filepath.read_text(encoding="utf-8")
            for pattern in old_patterns:
                if pattern in content:
                    rel_path = filepath.relative_to(REPO_ROOT)
                    if rel_path not in remaining:
                        remaining[rel_path] = []
                    remaining[rel_path].append(pattern)
        except Exception:
            pass

    if remaining:
        print(f"⚠️  Found {len(remaining)} files with remaining old patterns:\n")
        for filepath, patterns in sorted(remaining.items()):
            print(f"  {filepath}")
            for pattern in patterns:
                print(f"    • {pattern}")
    else:
        print("✅ No remaining old patterns found!")

    return remaining


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "--analyze":
        changes = analyze_project()
        print_analysis(changes)

    elif command == "--execute":
        response = input("\n⚠️  This will modify files. Continue? (y/N): ")
        if response.lower() == "y":
            changed = execute_refactoring()
            verify = verify_refactoring()
            if verify:
                print("\n⚠️  Some patterns still remain. Check manually.")
            else:
                print("\n✅ All patterns removed successfully!")
        else:
            print("Aborted.")

    elif command == "--verify":
        remaining = verify_refactoring()
        sys.exit(0 if not remaining else 1)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
