#!/usr/bin/env python3
"""
Count and categorize Spanish naming remnants in the codebase.
Helps quantify migration effort.
"""

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Define patterns to search for
PATTERNS = {
    "class_empresa": r"class\s+(?:Empresa|UsuarioEmpresa|RolEmpresa|UsuarioRolEmpresa)\b",
    "class_billing": r"class\s+(?:Facturacion|Factura|MovimientoFacturacion)\b",
    "class_modulo": r"class\s+(?:Modulo|ModuloEmpresa|ModuloAsignado)\b",
    "class_payroll": r"class\s+(?:Nomina|NominaConcepto|NominaPlantilla)\b",
    "class_cash": r"class\s+(?:Caja|CajaMovimiento|CierreCaja)\b",
    "enum_cash": r"(?:caja_movimiento_tipo|caja_movimiento_categoria|cierre_caja_status)",
    "enum_payroll": r"(?:nomina_status|nomina_tipo)",
    "enum_billing": r"(?:movimiento_tipo|movimiento_estado)",
    "import_empresa": r"from\s+app\.models\.empresa\s+import",
    "import_facturacion": r"from\s+app\.models\.(?:core\.)?facturacion\s+import",
    "import_modulo": r"from\s+app\.models\.(?:core\.)?modulo\s+import",
    "import_nomina": r"from\s+app\.models\.(?:hr\.)?nomina\s+import",
    "import_caja": r"from\s+app\.models\.(?:finance\.)?caja\s+import",
    "field_spanish": r"(?:nombre_empresa|razon_social|tipo_empresa|tipo_negocio|activo|descripcion|horas_extra|fecha_pago)",
    "docstring_spanish": r"\"\"\".*?[áéíóúñ].*?\"\"\"",
    "router_spanish": r"from\s+app\.routers\.(?:empresa|nomina|caja|facturacion)",
    "service_spanish": r"from\s+app\.services\.(?:.*empresa|.*nomina|.*caja|.*facturacion)",
}

# Files to exclude
EXCLUDE_PATTERNS = [
    r"__pycache__",
    r"\.pyc",
    r"\.pyo",
    r"\.git",
    r"\.venv",
    r"node_modules",
    r"\.pytest_cache",
    r"\.mypy_cache",
    r"\.qodo",
]


def should_skip_file(path: str) -> bool:
    """Check if file should be skipped."""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, path):
            return True
    return False


def count_occurrences(
    directory: str = "apps/backend/app",
) -> Dict[str, List[Tuple[str, int, str]]]:
    """Count Spanish naming remnants in codebase."""

    results = defaultdict(list)

    # Walk through directory
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not should_skip_file(os.path.join(root, d))]

        for file in files:
            if not file.endswith(".py"):
                continue

            filepath = os.path.join(root, file)

            if should_skip_file(filepath):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    lines = content.split("\n")

                    # Check each pattern
                    for pattern_name, pattern in PATTERNS.items():
                        matches = re.finditer(
                            pattern, content, re.IGNORECASE | re.DOTALL
                        )
                        for match in matches:
                            # Find line number
                            line_num = content[: match.start()].count("\n") + 1
                            line_content = (
                                lines[line_num - 1] if line_num <= len(lines) else ""
                            )
                            results[pattern_name].append(
                                (filepath, line_num, line_content.strip())
                            )

            except Exception as e:
                print(f"Error reading {filepath}: {e}")

    return results


def print_report(results: Dict[str, List[Tuple[str, int, str]]]):
    """Print formatted report."""

    print("\n" + "=" * 80)
    print("SPANISH NAMING REMNANTS - DETAILED REPORT")
    print("=" * 80)

    # Summary
    total_occurrences = sum(len(v) for v in results.values())
    print(f"\nTOTAL OCCURRENCES: {total_occurrences}\n")

    # Group by category
    categories = {
        "Class Definitions": [
            "class_empresa",
            "class_billing",
            "class_modulo",
            "class_payroll",
            "class_cash",
        ],
        "Enums": ["enum_cash", "enum_payroll", "enum_billing"],
        "Imports": [
            "import_empresa",
            "import_facturacion",
            "import_modulo",
            "import_nomina",
            "import_caja",
        ],
        "Field Names": ["field_spanish"],
        "Routers/Services": ["router_spanish", "service_spanish"],
        "Documentation": ["docstring_spanish"],
    }

    for category, patterns in categories.items():
        category_count = sum(len(results[p]) for p in patterns)
        if category_count == 0:
            continue

        print(f"\n{category.upper()} ({category_count} occurrences)")
        print("-" * 80)

        for pattern in patterns:
            if pattern not in results or not results[pattern]:
                continue

            print(f"\n  Pattern: {pattern} ({len(results[pattern])} matches)")

            # Group by file
            by_file = defaultdict(list)
            for filepath, line_num, line_content in results[pattern]:
                by_file[filepath].append((line_num, line_content))

            for filepath, matches in sorted(by_file.items()):
                # Make path relative
                rel_path = filepath.replace(os.getcwd(), "").lstrip(os.sep)
                print(f"    {rel_path}: {len(matches)} matches")
                for line_num, line_content in matches[:3]:  # Show first 3
                    print(f"      L{line_num}: {line_content[:70]}")
                if len(matches) > 3:
                    print(f"      ... and {len(matches) - 3} more")

    print("\n" + "=" * 80)
    print("END REPORT")
    print("=" * 80)


def generate_migration_checklist(results: Dict[str, List[Tuple[str, int, str]]]):
    """Generate a checklist for migration."""

    print("\n\nMIGRATION CHECKLIST")
    print("=" * 80)

    # Extract unique files
    files = set()
    for pattern_list in results.values():
        for filepath, _, _ in pattern_list:
            files.add(filepath)

    print("\nFiles requiring updates:")
    for filepath in sorted(files):
        rel_path = filepath.replace(os.getcwd(), "").lstrip(os.sep)
        print(f"  - [ ] {rel_path}")


if __name__ == "__main__":
    import sys

    # Allow custom directory
    directory = sys.argv[1] if len(sys.argv) > 1 else "apps/backend/app"

    if not os.path.exists(directory):
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    print(f"Scanning: {directory}")
    results = count_occurrences(directory)

    print_report(results)
    generate_migration_checklist(results)

    # Save to file
    output_file = f"MIGRATION_CHECKLIST_{Path.cwd().name}.txt"
    print("\n✓ Results can be saved to a file if needed")
