#!/usr/bin/env python3
"""
Bulk fix Pydantic V2 warnings across all schema files
"""

import os
import re


def fix_pydantic_imports(content):
    """Fix pydantic imports"""
    if "from pydantic import" in content:
        # Add field_validator and ConfigDict if using validator or Config
        if "@validator" in content or "class Config:" in content:
            if "field_validator" not in content:
                # Replace validator with field_validator in import
                content = re.sub(
                    r"from pydantic import ([^)]*validator[^)]*)",
                    lambda m: m.group(0).replace("validator", "field_validator"),
                    content,
                )
            if "ConfigDict" not in content:
                # Add ConfigDict to imports if not present
                content = re.sub(
                    r"from pydantic import ([^)]*)",
                    lambda m: m.group(0).rstrip(")") + ", ConfigDict)"
                    if "ConfigDict" not in m.group(0)
                    else m.group(0),
                    content,
                    count=1,
                )
    return content


def fix_validators(content):
    """Convert @validator to @field_validator with @classmethod"""
    # Replace @validator(...) def with @field_validator + @classmethod
    pattern = r"(@validator\([^)]+\))\s*\n(\s*)def\s+"
    content = re.sub(
        pattern,
        lambda m: m.group(1).replace("@validator", "@field_validator")
        + "\n"
        + m.group(2)
        + "@classmethod\n"
        + m.group(2)
        + "def ",
        content,
    )
    return content


def fix_config_classes(content):
    """Replace class Config with model_config = ConfigDict"""
    # Match class Config: and its content
    pattern = r"class Config:\s+from_attributes\s*=\s*True"
    content = re.sub(pattern, "model_config = ConfigDict(from_attributes=True)", content)
    return content


def fix_field_constraints(content):
    """Fix Field constraints: min_items -> min_length, etc."""
    content = content.replace("min_items=", "min_length=")
    content = content.replace("max_items=", "max_length=")
    return content


def fix_query_regex(content):
    """Fix Query regex= -> pattern="""
    content = re.sub(r"Query\(([^)]*?)regex=", r"Query(\1pattern=", content)
    return content


def process_file(file_path):
    """Process a single Python file"""
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        content = original_content

        # Apply all fixes
        content = fix_pydantic_imports(content)
        content = fix_validators(content)
        content = fix_config_classes(content)
        content = fix_field_constraints(content)
        content = fix_query_regex(content)

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    # Files to fix
    files_to_fix = [
        "app/schemas/production.py",
        "app/schemas/recipes.py",
        "app/schemas/notifications.py",
        "app/schemas/incidents.py",
        "app/schemas/sector_plantilla.py",
        "app/modules/accounting/interface/http/tenant.py",
        "app/modules/finanzas/interface/http/tenant.py",
        "app/modules/hr/interface/http/tenant.py",
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if process_file(file_path):
                print(f"✓ Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"  Skipped (no changes): {file_path}")
        else:
            print(f"✗ File not found: {file_path}")

    print(f"\n✓ Total files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
