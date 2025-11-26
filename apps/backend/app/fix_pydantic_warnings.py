#!/usr/bin/env python3
"""Fix all Pydantic V2 deprecation warnings"""

import os
import re
from pathlib import Path


def fix_config_class(content: str) -> str:
    """Replace class Config with model_config = ConfigDict"""
    # Check if we need ConfigDict import
    if "class Config:" in content:
        if "ConfigDict" not in content:
            # Add import if pydantic is imported
            if "from pydantic import" in content:
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "from pydantic import" in line and "ConfigDict" not in line:
                        lines[i] = line.rstrip() + ", ConfigDict"
                        content = "\n".join(lines)
                        break

    # Replace Config class: from_attributes = True only
    content = re.sub(
        r"class Config:\s+from_attributes\s*=\s*True\s*\n(?:\s+(\w+)\s*=\s*([^\n]+)\s*\n)?",
        lambda m: "model_config = ConfigDict(from_attributes=True"
        + (f", {m.group(1)}={m.group(2).strip()}" if m.group(1) else "")
        + ")\n",
        content,
    )

    return content


def fix_validators(content: str) -> str:
    """Replace @validator with @field_validator"""
    # First, update imports
    if "@validator" in content:
        # Replace @validator with @field_validator in the code
        content = re.sub(
            r"@validator\(([^)]+)\)\s*\n\s*def\s+(\w+)\s*\(\s*cls\s*,",
            r"@field_validator(\1)\n    @classmethod\n    def \2(cls,",
            content,
        )

        # Add field_validator to imports if using @field_validator
        if "@field_validator" in content and "field_validator" not in content:
            # Find pydantic import line
            content = re.sub(
                r"from pydantic import ([^;\n]+)",
                lambda m: f"from pydantic import {m.group(1)}, field_validator"
                if "field_validator" not in m.group(1)
                else m.group(0),
                content,
                count=1,
            )

    return content


def fix_field_deprecated_args(content: str) -> bool:
    """Fix Field(..., extra='allow') type warnings"""
    changed = False

    # Replace Field(..., env="...") with Field(..., json_schema_extra=...)
    if re.search(r"Field\([^)]*,\s*env\s*=", content):
        # This requires more careful handling per file
        pass

    return changed


def fix_file(file_path: str) -> bool:
    """Fix a single file and return True if changed"""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original = content

        # Apply fixes
        content = fix_config_class(content)
        content = fix_validators(content)

        # Only write if changed
        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def find_python_files(directory: str) -> list[str]:
    """Find all Python files in directory"""
    exclude_dirs = {".venv", "__pycache__", ".pytest_cache", ".mypy_cache", "htmlcov"}

    files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in filenames:
            if filename.endswith(".py") and not filename.startswith("fix_"):
                files.append(os.path.join(root, filename))

    return files


def main():
    """Main function to fix all warnings"""
    app_dir = Path(__file__).parent

    python_files = find_python_files(str(app_dir))
    print(f"[*] Found {len(python_files)} Python files to check...")

    fixed_files = []
    for file_path in sorted(python_files):
        if fix_file(file_path):
            fixed_files.append(file_path)
            print(f"[+] Fixed: {file_path}")

    print("\n" + "=" * 40)
    print(f"Total files fixed: {len(fixed_files)}")


if __name__ == "__main__":
    main()
