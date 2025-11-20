#!/usr/bin/env python3
"""
Script para agregar extend_existing=True a todos los modelos SQLAlchemy
"""

import re
from pathlib import Path


def fix_model_file(filepath: Path) -> bool:
    """Agrega extend_existing=True a un archivo de modelo si es necesario"""
    content = filepath.read_text(encoding="utf-8")
    original_content = content

    # Buscar clases que heredan de Base

    # Verificar si tiene __table_args__
    has_table_args = "__table_args__" in content

    if not has_table_args:
        # Buscar donde insertar __table_args__
        # Debe ir después de __tablename__
        tablename_pattern = r'(__tablename__\s*=\s*["\'][^"\']+["\'])\n'

        match = re.search(tablename_pattern, content)
        if match:
            # Insertar __table_args__ después de __tablename__
            insert_pos = match.end()
            new_line = '    __table_args__ = {"extend_existing": True}\n'
            content = content[:insert_pos] + new_line + content[insert_pos:]
            print(f"[OK] Agregado __table_args__ a {filepath.name}")
    else:
        # Verificar si ya tiene extend_existing
        if "extend_existing" not in content:
            # Buscar __table_args__ y agregar extend_existing
            # Caso 1: __table_args__ = (...)
            tuple_pattern = r"(__table_args__\s*=\s*\()(.*?)(\))"
            match = re.search(tuple_pattern, content, re.DOTALL)
            if match:
                # Agregar {"extend_existing": True} al final de la tupla
                start, middle, end = match.groups()
                if middle.strip().endswith(","):
                    new_middle = middle + '\n        {"extend_existing": True}\n    '
                else:
                    new_middle = middle + ',\n        {"extend_existing": True}\n    '
                content = (
                    content[: match.start()]
                    + start
                    + new_middle
                    + end
                    + content[match.end() :]
                )
                print(f"[OK] Agregado extend_existing a tupla en {filepath.name}")

            # Caso 2: __table_args__ = {...}
            dict_pattern = r"(__table_args__\s*=\s*\{)([^}]*)(\})"
            match = re.search(dict_pattern, content)
            if match:
                start, middle, end = match.groups()
                if "extend_existing" not in middle:
                    if middle.strip():
                        new_middle = middle + ', "extend_existing": True'
                    else:
                        new_middle = '"extend_existing": True'
                    content = (
                        content[: match.start()]
                        + start
                        + new_middle
                        + end
                        + content[match.end() :]
                    )
                    print(f"[OK] Agregado extend_existing a dict en {filepath.name}")

    if content != original_content:
        filepath.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    """Procesar todos los archivos de modelos"""
    models_dir = Path(__file__).parent.parent / "apps" / "backend" / "app" / "models"

    if not models_dir.exists():
        print(f"❌ No se encuentra el directorio: {models_dir}")
        return

    print(f"Buscando modelos en: {models_dir}\n")

    fixed_count = 0
    for py_file in models_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        if fix_model_file(py_file):
            fixed_count += 1

    print(f"\nTotal de archivos modificados: {fixed_count}")


if __name__ == "__main__":
    main()
