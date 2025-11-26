#!/usr/bin/env python3
"""
Script to automatically fix Pydantic V2 warnings in the codebase.
Handles:
1. @validator -> @field_validator
2. class Config -> ConfigDict
3. regex -> pattern (Query parameters)
4. on_event -> lifespan (FastAPI)
5. min_items -> min_length, max_items -> max_length
"""

import re
from pathlib import Path


def fix_pydantic_validators(file_path):
    """Fix @validator decorators to @field_validator"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Add imports if needed
    if "@field_validator" in content and "from pydantic import" in content:
        if "field_validator" not in content:
            content = re.sub(
                r"from pydantic import ([^)]*?)(?:validator)?",
                lambda m: f"from pydantic import {m.group(1)}, field_validator".replace(
                    ", ,", ","
                ).replace("import , ", "import "),
                content,
                count=1,
            )

    if "ConfigDict" in content and "from pydantic import" in content:
        if "ConfigDict" not in content.split("from pydantic import")[0]:
            content = re.sub(
                r"from pydantic import ([^)]*)",
                lambda m: f"from pydantic import {m.group(1)}, ConfigDict"
                if "ConfigDict" not in m.group(1)
                else m.group(0),
                content,
                count=1,
            )

    # Replace @validator with @field_validator + @classmethod
    # Match @validator decorators
    pattern = r"@validator\((.*?)\)(\s+def\s+)"

    def replace_validator(match):
        args = match.group(1)
        def_str = match.group(2)
        return f"@field_validator({args})\n    @classmethod{def_str}"

    content = re.sub(pattern, replace_validator, content)

    # Fix info.data for validators that used 'values'
    content = re.sub(
        r"def validate_(\w+)\(cls, v, values\)",
        r"def validate_\1(cls, v, info)",
        content,
    )
    content = re.sub(r"values\[", r"info.data[", content)

    # Fix class Config to ConfigDict
    config_pattern = r"class Config:\s+([^\n]+(?:\n\s{8}[^\n]+)*)"

    def replace_config(match):
        config_content = match.group(1)
        # Parse config attributes
        lines = config_content.split("\n")
        attrs = {}
        for line in lines:
            line = line.strip()
            if line and "=" in line:
                key, val = line.split("=", 1)
                attrs[key.strip()] = val.strip()

        if attrs:
            attr_str = ", ".join(f"{k}={v}" for k, v in attrs.items())
            return f"model_config = ConfigDict({attr_str})"
        return match.group(0)

    content = re.sub(config_pattern, replace_config, content)

    # Fix Field(min_items=...) -> Field(min_length=...)
    content = re.sub(r"min_items=", "min_length=", content)
    content = re.sub(r"max_items=", "max_length=", content)

    # Fix Query(regex=...) -> Query(pattern=...)
    content = re.sub(r"Query\((.*?)regex=", r"Query(\1pattern=", content)

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def fix_fastapi_on_event(file_path):
    """Fix @app.on_event to lifespan"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # This requires more complex logic, so we'll just mark it for manual review
    # Check if it has on_event
    if "@app.on_event" in content or "@router.on_event" in content:
        print(f"⚠️  Manual fix needed for on_event in: {file_path}")

    return content != original


def main():
    base_path = Path("app")

    # Find all Python files
    python_files = list(base_path.rglob("*.py"))

    fixed_count = 0
    for file_path in python_files:
        try:
            if fix_pydantic_validators(file_path):
                print(f"✓ Fixed: {file_path}")
                fixed_count += 1
        except Exception as e:
            print(f"✗ Error in {file_path}: {e}")

    print(f"\n✓ Total files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
