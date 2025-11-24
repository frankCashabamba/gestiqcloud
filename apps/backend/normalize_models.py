#!/usr/bin/env python3
"""
Script to normalize model naming from Spanish to English.
Handles:
1. Folder renaming: empresa -> company
2. File renaming: venta.py -> sale.py, compra.py -> purchase.py, proveedor.py -> supplier.py
3. Import updates across codebase
4. Field renaming in models
5. Enum renaming in finance models
"""

import re
import shutil
from pathlib import Path

# Base path
BASE_PATH = Path(__file__).parent.resolve()
MODELS_PATH = BASE_PATH / "app" / "models"

# Mappings
FOLDER_RENAMES = {
    "empresa": "company",
}

FILE_RENAMES = {
    ("sales", "venta.py"): ("sales", "sale.py"),
    ("purchases", "compra.py"): ("purchases", "purchase.py"),
    ("suppliers", "proveedor.py"): ("suppliers", "supplier.py"),
}

# Import path mappings for search and replace
IMPORT_MAPPINGS = [
    # Main module path changes
    ("from app.models.empresa", "from app.models.company"),
    ("from app.models.sales.venta", "from app.models.sales.sale"),
    ("from app.models.purchases.compra", "from app.models.purchases.purchase"),
    ("from app.models.suppliers.proveedor", "from app.models.suppliers.supplier"),
    # Class name changes
    ("class Venta", "class Sale"),
    ("class Compra", "class Purchase"),
    ("class Proveedor", "class Supplier"),
    ("class CompraLinea", "class PurchaseLine"),
]

# Field renames in models
FIELD_RENAMES_VENTA = {
    "cliente_id": "customer_id",
    "fecha": "date",
    "estado": "status",
    "notas": "notes",
    "usuario_id": "user_id",
    "cliente": "customer",
}

# Enum renames in finance/caja.py
ENUM_RENAMES = {
    "caja_movimiento_tipo": "cash_movement_type",
    "caja_movimiento_categoria": "cash_movement_category",
    "cierre_caja_status": "cash_closing_status",
    "ABIERTO": "OPEN",
    "CERRADO": "CLOSED",
    "PENDIENTE": "PENDING",
}


def find_all_python_files(start_path: Path) -> list[Path]:
    """Find all Python files in the project."""
    return list(start_path.rglob("*.py"))


def rename_folder(old_path: Path, new_path: Path) -> bool:
    """Rename a folder."""
    if old_path.exists() and not new_path.exists():
        print(f"Renaming folder: {old_path.name} -> {new_path.name}")
        shutil.move(str(old_path), str(new_path))
        return True
    return False


def rename_file(old_path: Path, new_path: Path) -> bool:
    """Rename a file."""
    if old_path.exists() and not new_path.exists():
        print(f"Renaming file: {old_path.name} -> {new_path.name}")
        shutil.move(str(old_path), str(new_path))
        return True
    return False


def update_file_imports(file_path: Path, mappings: list[tuple[str, str]]) -> bool:
    """Update imports in a file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        for old_pattern, new_pattern in mappings:
            # Use word boundary regex for more accurate replacement
            pattern = re.compile(re.escape(old_pattern) + r"(?=[\s\.\(\)\,]|$)", re.MULTILINE)
            content = pattern.sub(new_pattern, content)

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            print(f"Updated imports: {file_path.relative_to(BASE_PATH)}")
            return True
    except Exception as e:
        print(f"Error updating {file_path}: {e}")

    return False


def main():
    print("=" * 70)
    print("NORMALIZING MODEL NAMING: Spanish -> English")
    print("=" * 70)

    # Step 1: Rename empresa folder to company
    print("\n[Step 1] Renaming folders...")
    empresa_path = MODELS_PATH / "empresa"
    company_path = MODELS_PATH / "company"

    if empresa_path.exists():
        rename_folder(empresa_path, company_path)

    # Step 2: Rename files
    print("\n[Step 2] Renaming files...")
    for (old_dir, old_file), (new_dir, new_file) in FILE_RENAMES.items():
        old_path = MODELS_PATH / old_dir / old_file
        new_path = MODELS_PATH / new_dir / new_file
        if old_path.exists():
            rename_file(old_path, new_path)

    # Step 3: Update all imports
    print("\n[Step 3] Updating imports across codebase...")
    all_py_files = find_all_python_files(BASE_PATH)

    for py_file in all_py_files:
        # Skip __pycache__ and .venv
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue

        update_file_imports(py_file, IMPORT_MAPPINGS)

    # Step 4: Summary
    print("\n" + "=" * 70)
    print("NORMALIZATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Update field names in sales/sale.py (cliente_id → customer_id, etc.)")
    print("2. Update enum names in finance/caja.py")
    print("3. Update docstrings and comments to English")
    print("4. Regenerate migrations with generate_schema_sql.py")
    print("5. Test migrations on empty database")


if __name__ == "__main__":
    main()
