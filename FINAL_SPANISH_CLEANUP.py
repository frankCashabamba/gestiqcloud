#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script final para traducir términos españoles restantes en código.
Proceso seguro:
1. Identifica archivos con términos en español
2. Traduce en contextos seguros (strings, comentarios, variable names)
3. Evita romper imports
"""

import re
from pathlib import Path

BACKEND_PATH = Path(
    r"c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app"
)

# Traducciones seguras por archivo/contexto
CONTEXT_TRANSLATIONS = {
    # Proveedor -> Provider
    "proveedor": {
        "old": "proveedor",
        "new": "provider",
        "files_exact": [
            "services/payments/__init__.py",
            "services/payments/stripe_provider.py",
            "services/payments/payphone_provider.py",
            "services/payments/kushki_provider.py",
            "services/recipe_calculator.py",
            "routers/payments.py",
        ],
    },
    # Factura -> Invoice
    "factura": {
        "old": "factura",
        "new": "invoice",
        "files_exact": [
            "modules/imports/infrastructure/extractors/extractor_factura.py",
            "modules/imports/infrastructure/parsers/xml_invoice.py",
        ],
    },
    # Recibo -> Receipt
    "recibo": {
        "old": "recibo",
        "new": "receipt",
        "files_exact": [
            "modules/imports/infrastructure/extractors/extractor_recibo.py",
        ],
    },
    # Gasto -> Expense
    "gasto": {
        "old": "gasto",
        "new": "expense",
        "files_exact": [
            "models/finance/cash_management.py",
        ],
    },
}


def translate_file(
    filepath: Path, old_term: str, new_term: str, careful: bool = True
) -> int:
    """Traduce un archivo de manera cuidadosa"""
    if not filepath.exists():
        return 0

    try:
        content = filepath.read_text(encoding="utf-8")
        original = content
        changes = 0

        if careful:
            # Solo reemplazar en contextos seguros (no en imports de las primeras líneas)
            lines = content.split("\n")
            new_lines = []
            in_imports = True

            for i, line in enumerate(lines):
                # Después de los imports, está seguro traducir
                if (
                    in_imports
                    and not line.startswith(("import ", "from ", "#", " ", "\t"))
                    and line.strip()
                ):
                    in_imports = False

                if in_imports and ("import " in line or "from " in line):
                    new_lines.append(line)
                else:
                    # Traducir con word boundaries
                    old_line = line
                    pattern = r"\b" + re.escape(old_term) + r"\b"
                    line = re.sub(pattern, new_term, line, flags=re.IGNORECASE)

                    if old_line != line:
                        changes += 1
                    new_lines.append(line)

            content = "\n".join(new_lines)
        else:
            # Traducir globalmente
            pattern = r"\b" + re.escape(old_term) + r"\b"
            matches = len(re.findall(pattern, content))
            content = re.sub(pattern, new_term, content, flags=re.IGNORECASE)
            changes = matches

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            return changes
        return 0
    except Exception as e:
        print(f"[ERROR] {filepath.name}: {e}")
        return 0


def main():
    print("\n" + "=" * 70)
    print("LIMPIAR TERMINOS ESPANOLES FINALES EN CODIGO")
    print("=" * 70)

    total_changes = 0
    total_files = 0

    for term, config in CONTEXT_TRANSLATIONS.items():
        print(f"\n[TRADUCIENDO] {config['old']} -> {config['new']}")
        print("-" * 70)

        for file_path in config["files_exact"]:
            filepath = BACKEND_PATH / file_path
            if filepath.exists():
                changes = translate_file(
                    filepath, config["old"], config["new"], careful=True
                )
                if changes > 0:
                    print(f"  [OK] {file_path}: {changes} cambios")
                    total_changes += changes
                    total_files += 1
            else:
                print(f"  [-] {file_path}: no encontrado")

    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    print(f"Archivos modificados: {total_files}")
    print(f"Cambios totales: {total_changes}")
    print("\n[OK] Limpieza completada")
    print("\nProximos pasos:")
    print("  1. git diff (revisar cambios)")
    print("  2. pytest tests/ -v (validar funcionalidad)")
    print("  3. git add -A && git commit")


if __name__ == "__main__":
    main()
