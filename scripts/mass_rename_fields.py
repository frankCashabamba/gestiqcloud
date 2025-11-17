#!/usr/bin/env python3
"""
Script para cambiar masivamente nombres de campos de español a inglés.
Ejecutar: python mass_rename_fields.py
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# CONFIGURAR AQUÍ LOS CAMBIOS
FIELD_MAPPINGS: Dict[str, str] = {
    # Ejemplo - REEMPLAZAR CON TUS CAMBIOS REALES
    # "nombre": "name",
    # "descripcion": "description",
    # "activo": "active",
    # "creado_en": "created_at",
    # "actualizado_en": "updated_at",
}

# Extensiones de archivo a procesar
EXTENSIONS = {
    ".py",  # Python backend
    ".ts",  # TypeScript
    ".tsx",  # React
    ".js",  # JavaScript
    ".jsx",  # React JS
    ".json",  # Config files
}

# Directorios a excluir
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".qodo",
    "dist",
    "build",
}


def should_skip_file(file_path: Path) -> bool:
    """Revisar si el archivo debe ser ignorado."""
    for exclude in EXCLUDE_DIRS:
        if exclude in file_path.parts:
            return True
    return file_path.suffix not in EXTENSIONS


def create_regex_patterns() -> List[Tuple[str, str, re.Pattern]]:
    """Crear patrones regex que respeten límites de palabra."""
    patterns = []

    for spanish, english in FIELD_MAPPINGS.items():
        # Patrón para: nombre_campo, "nombre_campo", nombre: etc
        regex = re.compile(r"\b" + re.escape(spanish) + r"\b", re.IGNORECASE)
        patterns.append((spanish, english, regex))

    return patterns


def process_file(
    file_path: Path, patterns: List[Tuple[str, str, re.Pattern]]
) -> Tuple[bool, int]:
    """Procesar un archivo y reemplazar ocurrencias.

    Retorna: (archivo_modificado, número_de_cambios)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Algunos archivos pueden tener otra codificación
        try:
            content = file_path.read_text(encoding="latin-1")
        except Exception as e:
            print(f"  ⚠️  No se puede leer: {e}")
            return False, 0

    original_content = content
    change_count = 0

    # Aplicar cada patrón
    for spanish, english, pattern in patterns:
        # Respetar case sensitivity en algunos contextos
        matches = list(pattern.finditer(content))
        if matches:
            # Preservar case: nombreCampo -> nameCampo
            def replace_func(match):
                nonlocal change_count
                change_count += 1
                matched_text = match.group(0)

                # Si está en camelCase
                if matched_text[0].islower():
                    return english[0].lower() + english[1:]
                else:
                    return english[0].upper() + english[1:]

            content = pattern.sub(replace_func, content)

    # Escribir si hay cambios
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True, change_count

    return False, change_count


def main():
    """Procesar todos los archivos."""
    if not FIELD_MAPPINGS:
        print("❌ ERROR: FIELD_MAPPINGS está vacío")
        print("   Configura los cambios en la parte superior del script")
        return

    print("\n📋 Configuración:")
    print(f"   Cambios a realizar: {len(FIELD_MAPPINGS)}")
    for sp, en in FIELD_MAPPINGS.items():
        print(f"     • {sp} → {en}")

    # Encontrar archivos
    project_root = Path(__file__).parent.parent
    patterns = create_regex_patterns()

    files_to_process = []
    for path in project_root.rglob("*"):
        if path.is_file() and not should_skip_file(path):
            files_to_process.append(path)

    print(f"\n🔍 Archivos encontrados: {len(files_to_process)}")

    # Procesar archivos
    modified_files = 0
    total_changes = 0

    print("\n⚙️  Procesando archivos...\n")

    for idx, file_path in enumerate(files_to_process, 1):
        modified, changes = process_file(file_path, patterns)

        if modified:
            modified_files += 1
            total_changes += changes
            rel_path = file_path.relative_to(project_root)
            print(
                f"  ✏️  [{idx}/{len(files_to_process)}] {rel_path} ({changes} cambios)"
            )

    # Resumen
    print(f"\n{'='*60}")
    print("✅ Resumen:")
    print(f"   Archivos procesados: {len(files_to_process)}")
    print(f"   Archivos modificados: {modified_files}")
    print(f"   Cambios totales: {total_changes}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
