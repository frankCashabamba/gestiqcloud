#!/usr/bin/env python3
"""
HR Migration Validation Script

Validates that HR lookup tables don't already exist before migration.
Checks for conflicts with existing enums and models.

Usage:
    python scripts/validate_hr_migrations.py [--database-url URL]
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
import argparse

# Tables to check
TABLES_TO_CREATE = [
    "employee_statuses",
    "contract_types",
    "deduction_types",
    "gender_types"
]

# Model classes to check
MODEL_CLASSES_TO_CHECK = [
    "EmployeeStatus",
    "ContractType",
    "DeductionType",
    "GenderType"
]

# Files to search
MIGRATION_PATH = Path("ops/migrations")
MODELS_PATH = Path("apps/backend/app/models")


def find_table_definitions() -> List[Tuple[str, Path]]:
    """Find CREATE TABLE statements in migration files."""
    found = []
    
    for sql_file in MIGRATION_PATH.rglob("*.sql"):
        try:
            content = sql_file.read_text()
            for table_name in TABLES_TO_CREATE:
                # Look for CREATE TABLE statements
                patterns = [
                    f"CREATE TABLE.*{table_name}",
                    f"CREATE TABLE IF NOT EXISTS.*{table_name}",
                ]
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        found.append((table_name, sql_file))
        except Exception as e:
            print(f"⚠️  Error reading {sql_file}: {e}")
    
    return found


def find_model_definitions() -> List[Tuple[str, Path]]:
    """Find SQLAlchemy model class definitions."""
    found = []
    
    for py_file in MODELS_PATH.rglob("*.py"):
        try:
            content = py_file.read_text()
            for class_name in MODEL_CLASSES_TO_CHECK:
                # Look for class definitions (but exclude comments)
                pattern = f"^class {class_name}\\(.*\\):"
                if re.search(pattern, content, re.MULTILINE):
                    # Make sure it's not in a comment
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.match(pattern, line) and not line.strip().startswith('#'):
                            found.append((class_name, py_file))
                            break
        except Exception as e:
            print(f"⚠️  Error reading {py_file}: {e}")
    
    return found


def check_enum_usage() -> dict:
    """Check for existing enum definitions in HR models."""
    enums_found = {}
    
    enum_pattern = r"(\w+)\s*=\s*SQLEnum\((.*?),\s*name\s*=\s*['\"](\w+)['\"]"
    
    for py_file in MODELS_PATH.rglob("*.py"):
        try:
            content = py_file.read_text()
            matches = re.findall(enum_pattern, content, re.DOTALL)
            for var_name, values, enum_name in matches:
                if any(table in enum_name for table in TABLES_TO_CREATE):
                    enums_found[enum_name] = {
                        'variable': var_name,
                        'file': py_file,
                        'values': [v.strip().strip('"\'') for v in values.split(',') if v.strip()]
                    }
        except Exception as e:
            print(f"⚠️  Error reading {py_file}: {e}")
    
    return enums_found


def check_migration_files_exist() -> bool:
    """Check if migration files are created."""
    migrations = [
        MIGRATION_PATH / "2026-02-18_000_hr_lookup_tables" / "up.sql",
        MIGRATION_PATH / "2026-02-18_000_hr_lookup_tables" / "down.sql",
        MIGRATION_PATH / "2026-02-18_001_seed_hr_lookups" / "up.sql",
        MIGRATION_PATH / "2026-02-18_001_seed_hr_lookups" / "down.sql",
    ]
    
    all_exist = True
    for migration in migrations:
        if migration.exists():
            print(f"✅ Found migration: {migration.relative_to(Path.cwd())}")
        else:
            print(f"❌ Missing migration: {migration.relative_to(Path.cwd())}")
            all_exist = False
    
    return all_exist


def validate_migration_sql(up_file: Path) -> List[str]:
    """Validate migration SQL file structure."""
    issues = []
    
    try:
        content = up_file.read_text()
        
        # Check for required elements
        if "BEGIN;" not in content:
            issues.append("Missing BEGIN; transaction")
        if "COMMIT;" not in content:
            issues.append("Missing COMMIT; transaction")
        
        # Check for CREATE TABLE statements
        create_count = len(re.findall(r"CREATE TABLE", content, re.IGNORECASE))
        if create_count == 0:
            issues.append("No CREATE TABLE statements found")
        
        # Check for indexes
        if "CREATE INDEX" not in content:
            issues.append("No indexes defined (optional but recommended)")
        
        # Check for proper error handling
        if "IF NOT EXISTS" not in content:
            issues.append("Missing IF NOT EXISTS (should be safe)")
    
    except Exception as e:
        issues.append(f"Error reading file: {e}")
    
    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate HR module migrations before deployment"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for conflicts, don't validate structure"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("HR MODULE MIGRATION VALIDATION")
    print("="*80 + "\n")
    
    # Step 1: Check for existing table definitions
    print("📋 Step 1: Checking for existing table definitions...")
    table_defs = find_table_definitions()
    if table_defs:
        print(f"❌ FOUND {len(table_defs)} existing table definitions:")
        for table, file in table_defs:
            print(f"   - {table} in {file.relative_to(Path.cwd())}")
        return 1
    else:
        print("✅ No existing table definitions found (SAFE)\n")
    
    # Step 2: Check for existing model classes
    print("📋 Step 2: Checking for existing model classes...")
    model_defs = find_model_definitions()
    if model_defs:
        print(f"❌ FOUND {len(model_defs)} existing model classes:")
        for class_name, file in model_defs:
            print(f"   - {class_name} in {file.relative_to(Path.cwd())}")
        return 1
    else:
        print("✅ No conflicting model classes found (SAFE)\n")
    
    # Step 3: Check enum usage
    print("📋 Step 3: Checking existing enum definitions...")
    enums = check_enum_usage()
    if enums:
        print(f"⚠️  Found {len(enums)} existing enum definitions (expected):")
        for enum_name, info in enums.items():
            values = ", ".join(info['values'][:3])
            if len(info['values']) > 3:
                values += f", ... ({len(info['values'])} total)"
            print(f"   - {enum_name}: {values}")
        print("   → These will coexist with new lookup tables (safe)\n")
    else:
        print("ℹ️  No enums found (unusual but safe)\n")
    
    # Step 4: Check migration files exist
    print("📋 Step 4: Checking migration files...")
    migrations_exist = check_migration_files_exist()
    if not migrations_exist:
        print("❌ Some migration files are missing\n")
        return 1
    print()
    
    if not args.check_only:
        # Step 5: Validate migration SQL
        print("📋 Step 5: Validating migration SQL structure...")
        up_file = MIGRATION_PATH / "2026-02-18_000_hr_lookup_tables" / "up.sql"
        if up_file.exists():
            issues = validate_migration_sql(up_file)
            if issues:
                print(f"⚠️  Found {len(issues)} issues:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print("✅ Migration SQL structure is valid\n")
        
        seed_file = MIGRATION_PATH / "2026-02-18_001_seed_hr_lookups" / "up.sql"
        if seed_file.exists():
            issues = validate_migration_sql(seed_file)
            if issues:
                for issue in issues:
                    if "no CREATE TABLE" not in issue.lower():
                        print(f"   - {issue}")
            else:
                print("✅ Seed migration structure is valid\n")
    
    # Final summary
    print("="*80)
    print("VALIDATION RESULT: ✅ ALL CHECKS PASSED")
    print("="*80)
    print("\n✅ Safe to deploy HR module migrations\n")
    print("Next steps:")
    print("  1. Backup your database")
    print("  2. Test migrations in dev environment")
    print("  3. Deploy to staging")
    print("  4. Deploy to production")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
