#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para reemplazar empresa_id → tenant_id en todo el código Python.

IMPORTANTE: Este script hace cambios masivos. Se recomienda:
1. Hacer commit antes de ejecutar
2. Revisar los cambios con git diff después
"""

import re
from pathlib import Path
from typing import Tuple

# Directorios a procesar
DIRS_TO_PROCESS = [
    "apps/backend/app/api",
    "apps/backend/app/core",
    "apps/backend/app/db",
    "apps/backend/app/middleware",
    "apps/backend/app/modules",
    "apps/backend/app/routers",
    "apps/backend/app/services",
    "apps/backend/app/settings",
    "apps/backend/app/schemas",
    "apps/backend/app/workers",
]

# Archivos a EXCLUIR (no tocar)
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    "migrations/",  # No tocar migraciones SQL
    "alembic/",  # No tocar Alembic
]

# Patrones a reemplazar (pattern, replacement)
REPLACEMENTS = [
    # Atributos de modelos y acceso a propiedades
    (r"\.empresa_id\b", r".tenant_id"),
    (r"\bempresa_id\s*=", r"tenant_id ="),
    (r"\bempresa_id:", r"tenant_id:"),
    (r"\bempresa_id\)", r"tenant_id)"),
    (r"\(empresa_id\b", r"(tenant_id"),
    (r",\s*empresa_id\b", r", tenant_id"),
    (r"\bempresa_id,", r"tenant_id,"),
    # Llamadas a funciones con empresa_id como keyword arg
    (r"\bempresa_id\s*=\s*", r"tenant_id="),
    # Diccionarios y JSON
    (r'"empresa_id"', r'"tenant_id"'),
    (r"'empresa_id'", r"'tenant_id'"),
    # Comparaciones y filtros
    (r"empresa_id\s*==", r"tenant_id =="),
    (r"empresa_id\s*!=", r"tenant_id !="),
]

# Patrones a NO reemplazar (contextos donde debe quedar empresa_id)
SKIP_PATTERNS = [
    r"#.*empresa_id",  # Comentarios explicativos
    r'""".*empresa_id.*"""',  # Docstrings
    r"'''.*empresa_id.*'''",
    r"# Legacy.*empresa_id",  # Comentarios legacy
    r"# DEPRECATED.*empresa_id",
]


def should_skip_file(filepath: Path) -> bool:
    """Determina si un archivo debe ser excluido."""
    filepath_str = str(filepath)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in filepath_str:
            return True
    return False


def should_skip_line(line: str) -> bool:
    """Determina si una línea debe ser excluida del reemplazo."""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def replace_in_file(filepath: Path, dry_run: bool = False) -> Tuple[int, int]:
    """
    Reemplaza empresa_id por tenant_id en un archivo.

    Returns:
        Tuple[int, int]: (líneas procesadas, líneas modificadas)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"ERROR leyendo {filepath}: {e}")
        return 0, 0

    modified_lines = 0
    new_lines = []

    for line in lines:
        original_line = line

        # Skip líneas con comentarios legacy
        if should_skip_line(line):
            new_lines.append(line)
            continue

        # Aplicar reemplazos
        for pattern, replacement in REPLACEMENTS:
            line = re.sub(pattern, replacement, line)

        if line != original_line:
            modified_lines += 1

        new_lines.append(line)

    # Escribir archivo si hubo cambios
    if modified_lines > 0 and not dry_run:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(
                f"✓ {filepath.relative_to(Path.cwd())}: {modified_lines} líneas modificadas"
            )
        except Exception as e:
            print(f"ERROR escribiendo {filepath}: {e}")
            return len(lines), 0
    elif modified_lines > 0:
        print(
            f"[DRY-RUN] {filepath.relative_to(Path.cwd())}: {modified_lines} líneas se modificarían"
        )

    return len(lines), modified_lines


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Reemplazar empresa_id por tenant_id")
    parser.add_argument(
        "--dry-run", action="store_true", help="Simular sin modificar archivos"
    )
    parser.add_argument(
        "--force", action="store_true", help="Ejecutar sin confirmación"
    )
    args = parser.parse_args()

    root = Path.cwd()
    print(f"Directorio base: {root}")
    print(f"Modo: {'DRY-RUN' if args.dry_run else 'EJECUCIÓN REAL'}\n")

    if not args.dry_run and not args.force:
        resp = input(
            "⚠️  ADVERTENCIA: Esto modificará muchos archivos. ¿Continuar? (yes/no): "
        )
        if resp.lower() != "yes":
            print("Cancelado.")
            return

    total_files = 0
    total_lines = 0
    total_modified = 0

    for dir_path in DIRS_TO_PROCESS:
        full_path = root / dir_path
        if not full_path.exists():
            print(f"⚠️  Directorio no encontrado: {dir_path}")
            continue

        print(f"\n📁 Procesando: {dir_path}")

        for py_file in full_path.rglob("*.py"):
            if should_skip_file(py_file):
                continue

            lines_processed, lines_modified = replace_in_file(
                py_file, dry_run=args.dry_run
            )
            total_files += 1
            total_lines += lines_processed
            total_modified += lines_modified

    print(f"\n{'=' * 60}")
    print("RESUMEN:")
    print(f"  Archivos procesados: {total_files}")
    print(f"  Líneas totales: {total_lines}")
    print(f"  Líneas modificadas: {total_modified}")

    if args.dry_run:
        print("\n💡 Para aplicar los cambios, ejecuta sin --dry-run")
    else:
        print("\n✅ Cambios aplicados. Revisa con: git diff")


if __name__ == "__main__":
    main()
