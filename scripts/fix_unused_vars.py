#!/usr/bin/env python3
"""Script para arreglar variables no usadas prefijándolas con _"""

import re
from pathlib import Path


def prefix_unused_var(file_path, var_name, line_num):
    """Prefijar una variable no usada con _"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if 0 < line_num <= len(lines):
            line = lines[line_num - 1]
            # Reemplazar la primera ocurrencia del nombre de variable en esa línea
            new_line = re.sub(rf"\b{var_name}\b", f"_{var_name}", line, count=1)
            if new_line != line:
                lines[line_num - 1] = new_line
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                print(f"[OK] Fixed {var_name} in {file_path}:{line_num}")
                return True
    except Exception as e:
        print(f"[ERROR] Failed to fix {var_name} in {file_path}: {e}")
    return False


def main():
    project_root = Path(__file__).parent.parent
    backend_path = project_root / "apps" / "backend"

    # Lista manual de variables no usadas reportadas por ruff
    unused_vars = [
        ("app/modules/imports/application/use_cases.py", "tenant_id_uuid", 411),
        ("app/modules/imports/interface/http/tenant.py", "tenant_uuid", 1357),
        ("app/modules/ai_agent/notifier.py", "phone", 158),
        (
            "app/modules/imports/application/test_photo_utils.py",
            "original_available",
            123,
        ),
    ]

    scripts_vars = [
        ("../scripts/test_notifications.py", "whatsapp_channel_id", 274),
        ("../scripts/test_notifications.py", "telegram_channel_id", 275),
        ("../scripts/py/auto_migrate.py", "applied_any", 310),
        ("../scripts/fix_extend_existing.py", "class_pattern", 16),
        ("../ops/scripts/validate_imports_spec1.py", "result", 126),
    ]

    factory_vars = [
        ("../factory_batches.py", "patterns", 96),
        ("../factory_batches.py", "in_duplicate", 337),
    ]

    middleware_vars = [
        ("app/middleware/rls.py", "claims", 28),
    ]

    print("Prefijando variables no usadas...\n")

    fixed_count = 0
    for file_rel, var_name, line_num in unused_vars:
        file_path = backend_path / file_rel
        if file_path.exists():
            if prefix_unused_var(file_path, var_name, line_num):
                fixed_count += 1

    for file_rel, var_name, line_num in scripts_vars + factory_vars:
        file_path = project_root / file_rel
        if file_path.exists():
            if prefix_unused_var(file_path, var_name, line_num):
                fixed_count += 1

    for file_rel, var_name, line_num in middleware_vars:
        file_path = backend_path / file_rel
        if file_path.exists():
            if prefix_unused_var(file_path, var_name, line_num):
                fixed_count += 1

    print(f"\n{fixed_count} variables prefijadas correctamente")


if __name__ == "__main__":
    main()
