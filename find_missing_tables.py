#!/usr/bin/env python3
import re
from pathlib import Path


def camel_to_snake(name):
    """Convert PascalCase to snake_case"""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


models_dir = Path(
    r"C:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models"
)
migrations_dir = Path(
    r"C:\Users\pc_cashabamba\Documents\GitHub\proyecto\ops\migrations"
)

# Extract table names from models (with their class names)
model_tables = {}
for py_file in models_dir.rglob("*.py"):
    if py_file.name == "__init__.py":
        continue
    content = py_file.read_text(encoding="utf-8", errors="ignore")
    # Find all class definitions that inherit from Base
    matches = re.findall(r"class\s+(\w+)\(Base\)", content)
    for match in matches:
        snake_case = camel_to_snake(match)
        model_tables[match] = snake_case

# Extract table names from migrations
migration_tables = set()
for sql_file in migrations_dir.rglob("*.sql"):
    content = sql_file.read_text(encoding="utf-8", errors="ignore")
    # Find all CREATE TABLE statements
    matches = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", content)
    migration_tables.update(matches)

print("=" * 80)
print(f"Tables in models: {len(model_tables)}")
print(f"Tables in migrations: {len(migration_tables)}")
print("=" * 80)

# Find missing tables
missing = []
for model_name, snake_case in model_tables.items():
    if snake_case not in migration_tables:
        missing.append((model_name, snake_case))

if missing:
    print(f"\nMISSING TABLES ({len(missing)}):")
    for model_name, table_name in sorted(missing):
        print(f"  - {model_name:30} -> {table_name}")
else:
    print("\nAll model tables have migrations!")

# Show extra tables in migrations
extra = migration_tables - set(v for k, v in model_tables.items())
if extra:
    print(f"\nEXTRA TABLES IN MIGRATIONS ({len(extra)}):")
    for table in sorted(extra):
        print(f"  - {table}")
