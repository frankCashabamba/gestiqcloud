#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para remover aliases en español de modelos y actualizar todas las referencias.
Los aliases están al final de los archivos de modelos.
"""

import re
from pathlib import Path

BACKEND_PATH = Path(
    r"c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app"
)

# Mapeo de alias español -> nombre real
ALIAS_MAPPINGS = {
    "RolEmpresa": "CompanyRole",
    "UsuarioEmpresa": "CompanyUser",
    "UsuarioRolEmpresa": "CompanyUserRole",
    "Nomina": "Payroll",
    "NominaConcepto": "PayrollConcept",
}

# Archivos que contienen los aliases (donde eliminarlos)
ALIAS_FILES = {
    "models/company/company_role.py": ["RolEmpresa"],
    "models/company/company_user.py": ["UsuarioEmpresa"],
    "models/company/company_user_role.py": ["UsuarioRolEmpresa"],
}


def remove_alias_definition(filepath: Path, alias_name: str) -> bool:
    """Elimina la línea de definición del alias del archivo"""
    if not filepath.exists():
        return False

    try:
        content = filepath.read_text(encoding="utf-8")
        original = content

        # Patrón: [nombre_alias] = [nombre_real] (puede tener espacios)
        pattern = rf"^{re.escape(alias_name)}\s*=\s*\w+\s*$"

        # Eliminar línea completa (incluyendo el salto de línea anterior si es comentario)
        lines = content.split("\n")
        new_lines = []

        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                continue
            # También eliminar comentarios de compatibilidad
            if (
                "backward compatibility" in line.lower()
                or "keep old name" in line.lower()
            ):
                if i + 1 < len(lines) and re.match(pattern, lines[i + 1].strip()):
                    continue
            new_lines.append(line)

        content = "\n".join(new_lines)

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] removiendo alias en {filepath.name}: {e}")
        return False


def replace_aliases_in_file(filepath: Path) -> int:
    """Reemplaza todos los usos de alias con los nombres reales en un archivo"""
    if not filepath.exists():
        return 0

    try:
        content = filepath.read_text(encoding="utf-8")
        original = content
        changes = 0

        for alias, real_name in ALIAS_MAPPINGS.items():
            # Usar word boundaries para no reemplazar parcialmente
            pattern = r"\b" + re.escape(alias) + r"\b"

            if re.search(pattern, content):
                content = re.sub(pattern, real_name, content)
                changes += len(re.findall(pattern, original))

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            return changes
        return 0
    except Exception as e:
        print(f"[ERROR] reemplazando aliases en {filepath.name}: {e}")
        return 0


def main():
    print("\n" + "=" * 70)
    print("REMOVER ALIASES EN ESPANOL DE MODELOS Y ACTUALIZAR REFERENCIAS")
    print("=" * 70)

    # PASO 1: Eliminar definiciones de alias
    print("\n[PASO 1] Eliminando definiciones de alias en archivos de modelos")
    print("-" * 70)

    for file_path, aliases in ALIAS_FILES.items():
        filepath = BACKEND_PATH / file_path
        for alias in aliases:
            if remove_alias_definition(filepath, alias):
                print(f"  [OK] Removido alias '{alias}' de {file_path}")
            else:
                print(f"  [-] No se encontró alias '{alias}' en {file_path}")

    # PASO 2: Reemplazar todos los usos en el codebase
    print("\n[PASO 2] Reemplazando alias por nombres reales en todo el codebase")
    print("-" * 70)

    total_changes = 0
    files_modified = 0

    for py_file in BACKEND_PATH.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        changes = replace_aliases_in_file(py_file)
        if changes > 0:
            rel_path = py_file.relative_to(BACKEND_PATH)
            print(f"  [OK] {rel_path}: {changes} reemplazos")
            total_changes += changes
            files_modified += 1

    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    print(f"Archivos modificados: {files_modified}")
    print(f"Total de reemplazos: {total_changes}")
    print("\n[OK] Aliases removidos y referencias actualizadas")
    print("\nProximos pasos:")
    print("  1. git diff (revisar cambios)")
    print("  2. pytest tests/ -v (validar que todo funciona)")
    print(
        "  3. git add -A && git commit -m 'Remove Spanish model aliases and replace with English names'"
    )


if __name__ == "__main__":
    main()
