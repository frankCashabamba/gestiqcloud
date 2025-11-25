#!/usr/bin/env python3
"""Script para encontrar referencias legacy en el código."""

import re
from pathlib import Path

LEGACY_PATTERNS = {
    "Proveedor": r"\bProveedor\w+",
    "Gasto": r"\bGasto\w+",
    "Nomina": r"\bNomina\w+",
    "ConfiguracionEmpresa": r"\bConfiguracion\w+",
    "PermisoAccionGlobal": r"\bPermisoAccion\w+",
    "Empresa": r"\bEmpresa\b(?!_)",
    "UsuarioEmpresa": r"\bUsuarioEmpresa\w+",
    "RolEmpresa": r"\bRolEmpresa\w+",
}


def scan_python_files(root_path: str) -> dict[str, set[str]]:
    """Scan Python files for legacy patterns."""
    results = {pattern: set() for pattern in LEGACY_PATTERNS}
    root = Path(root_path)

    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            for pattern_name, regex in LEGACY_PATTERNS.items():
                if re.search(regex, content):
                    results[pattern_name].add(str(py_file))
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return results


if __name__ == "__main__":
    app_path = "c:\\Users\\pc_cashabamba\\Documents\\GitHub\\proyecto\\apps\\backend\\app"
    print(f"Scanning {app_path}...\n")

    results = scan_python_files(app_path)

    for pattern, files in results.items():
        if files:
            print(f"\n=== {pattern} ===")
            for file in sorted(files):
                print(f"  {file}")

    print(f"\n\nTotal files with legacy code: {sum(len(f) for f in results.values())}")
