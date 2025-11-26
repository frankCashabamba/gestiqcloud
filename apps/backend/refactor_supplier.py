"""Refactor Proveedor -> Supplier en codigo Python"""

import re
from pathlib import Path

FILES_TO_REFACTOR = [
    "app/modules/imports/domain/handlers.py",
    "app/modules/imports/domain/handlers_complete.py",
    "app/modules/imports/application/use_cases.py",
    "app/modules/imports/domain/canonical_schema.py",
    "app/modules/invoicing/schemas.py",
    "app/services/sector_defaults.py",
    "app/services/recipe_calculator.py",
    "app/services/payments/__init__.py",
    "app/modules/invoicing/crud.py",
    "app/modules/shared/services/document_converter.py",
    "app/services/excel_analyzer.py",
    "app/modules/imports/extractores/extractor_banco.py",
    "app/modules/copilot/services.py",
]

REPLACEMENTS = [
    (r"\bproveedor_nombre\b", "supplier_name"),
    (r"\bproveedor_id\b", "supplier_id"),
    (r"\bproveedor\b(?=\s*=)", "supplier"),
    (r"\bproveedor\b(?=\s*:)", "supplier"),
    (r'"proveedor"', '"supplier"'),
    (r"'proveedor'", "'supplier'"),
    (r"# Proveedor", "# Supplier"),
    (r"Proveedor \(", "Supplier ("),
]


def refactor_file(filepath: str) -> bool:
    """Refactoriza un archivo y muestra cambios."""
    full_path = Path(filepath)

    if not full_path.exists():
        print("[SKIP] No existe: " + filepath)
        return False

    try:
        content = full_path.read_text("utf-8")
        original = content

        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        if content == original:
            print("[SKIP] Sin cambios: " + filepath)
            return True

        changes = 0
        for pattern, replacement in REPLACEMENTS:
            matches = len(re.findall(pattern, original, flags=re.IGNORECASE))
            changes += matches

        print("\n[REFACTOR] " + filepath)
        print("[CHANGES] ~" + str(changes))

        confirm = input("[APPLY?] (s/n): ").strip().lower()
        if confirm == "s":
            full_path.write_text(content, "utf-8")
            print("[OK] Guardado")
            return True
        else:
            print("[SKIPPED]")
            return False

    except Exception as e:
        print("[ERROR] " + filepath + ": " + str(e))
        return False


def main():
    print("=" * 70)
    print("REFACTOR: Proveedor -> Supplier (Codigo Python)")
    print("=" * 70)

    success = 0
    skipped = 0

    for filepath in FILES_TO_REFACTOR:
        if refactor_file(filepath):
            success += 1
        else:
            skipped += 1

    print("\n" + "=" * 70)
    print("[DONE] Completado: " + str(success))
    print("[SKIP] Saltados: " + str(skipped))
    print("=" * 70)


if __name__ == "__main__":
    main()
