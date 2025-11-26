#!/usr/bin/env python3
"""Fix all Pydantic V2 warnings"""

import os
import re


def fix_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Replace @validator with @field_validator + @classmethod
    # Pattern: @validator("field_name")\n def validate_...
    pattern = r"@validator\(([^)]+)\)\s+def\s+(\w+)\s*\(cls,\s*v"
    replacement = r"@field_validator(\1)\n    @classmethod\n    def \2(cls, v"
    content = re.sub(pattern, replacement, content)

    # 2. Replace class Config with model_config = ConfigDict
    config_pattern = r"class Config:\s+from_attributes\s*=\s*True(?:\s+(\w+)\s*=\s*([^\n]+))?"

    def replace_config(match):
        extra = match.group(1)
        if extra:
            return f"model_config = ConfigDict(from_attributes=True, {extra}={match.group(2)})"
        return "model_config = ConfigDict(from_attributes=True)"

    content = re.sub(config_pattern, replace_config, content)

    # 3. Replace min_items with min_length
    content = content.replace("min_items=", "min_length=")
    content = content.replace("max_items=", "max_length=")

    # 4. Replace regex with pattern
    content = re.sub(r"Query\(([^,]*),\s*regex=", r"Query(\1, pattern=", content)
    content = re.sub(r"Query\(None,\s*regex=", r"Query(None, pattern=", content)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


# Files to fix
files = [
    "app/schemas/payroll.py",
    "app/schemas/production.py",
    "app/schemas/recipes.py",
    "app/schemas/notifications.py",
    "app/schemas/incidents.py",
    "app/schemas/sector_plantilla.py",
    "app/modules/accounting/interface/http/tenant.py",
    "app/modules/finanzas/interface/http/tenant.py",
    "app/modules/hr/interface/http/tenant.py",
]

fixed = 0
for file_path in files:
    if os.path.exists(file_path):
        if fix_file(file_path):
            print(f"✓ Fixed: {file_path}")
            fixed += 1
    else:
        print(f"✗ Not found: {file_path}")

print(f"\nTotal fixed: {fixed}")
