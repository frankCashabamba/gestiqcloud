#!/usr/bin/env python3
import re
from pathlib import Path

models_dir = Path(
    r"C:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models"
)
migrations_dir = Path(
    r"C:\Users\pc_cashabamba\Documents\GitHub\proyecto\ops\migrations"
)

# Extract table names from models
model_tables = set()
for py_file in models_dir.rglob("*.py"):
    if py_file.name == "__init__.py":
        continue
    content = py_file.read_text(encoding="utf-8", errors="ignore")
    # Find all class definitions that inherit from Base
    matches = re.findall(r"class\s+(\w+)\(Base\)", content)
    model_tables.update(matches)

# Extract table names from migrations
migration_tables = set()
for sql_file in migrations_dir.rglob("*.sql"):
    content = sql_file.read_text(encoding="utf-8", errors="ignore")
    # Find all CREATE TABLE statements
    matches = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", content)
    migration_tables.update(matches)

print("=" * 60)
print(f"Tables in models: {len(model_tables)}")
print(f"Tables in migrations: {len(migration_tables)}")
print("=" * 60)

missing = model_tables - migration_tables
if missing:
    print(f"\nMISSING TABLES ({len(missing)}):")
    for table in sorted(missing):
        print(f"  - {table}")
else:
    print("\nAll model tables have migrations!")

extra = migration_tables - model_tables
if extra:
    print(f"\nEXTRA TABLES IN MIGRATIONS ({len(extra)}):")
    for table in sorted(extra):
        print(f"  - {table}")
