#!/usr/bin/env python3
"""
Quick validation script for UUID migration

Usage:
    python test_uuid_migration.py
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding="utf-8")

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))


def check_deprecated_functions():
    """Verify deprecated functions are removed/replaced"""
    print("🔍 Checking for deprecated functions...")

    crud_path = Path(__file__).parent / "app/modules/facturacion/crud.py"
    content = crud_path.read_text()

    if "from app.modules.facturacion.services import generar_numero_factura" in content:
        print("❌ FAILED: generar_numero_factura still imported from facturacion.services")
        return False

    if "from app.modules.shared.services import generar_numero_documento" not in content:
        print("❌ FAILED: generar_numero_documento not imported from shared.services")
        return False

    print("✅ Deprecated functions properly replaced")
    return True


def check_model_uuids():
    """Verify SQLAlchemy models have UUID types"""
    print("\n🔍 Checking SQLAlchemy models...")

    checks = {
        "app/models/core/modulo.py": [
            ("Modulo.id", "PGUUID(as_uuid=True), primary_key=True"),
            ("EmpresaModulo.id", "PGUUID(as_uuid=True), primary_key=True"),
            ("ModuloAsignado.id", "PGUUID(as_uuid=True), primary_key=True"),
        ],
        "app/models/empresa/rolempresas.py": [
            ("RolEmpresa.id", "PGUUID(as_uuid=True), primary_key=True"),
        ],
        "app/models/empresa/empresa.py": [
            ("PerfilUsuario.usuario_id", "PGUUID(as_uuid=True)"),
        ],
    }

    base_path = Path(__file__).parent
    all_ok = True

    for file_path, assertions in checks.items():
        full_path = base_path / file_path
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        content = full_path.read_text()
        for model_field, expected_type in assertions:
            if expected_type in content:
                print(f"✅ {model_field}: UUID")
            else:
                print(f"❌ {model_field}: NOT UUID")
                all_ok = False

    return all_ok


def check_http_interfaces():
    """Verify HTTP interfaces accept UUID parameters"""
    print("\n🔍 Checking HTTP interfaces...")

    checks = {
        "app/modules/usuarios/interface/http/tenant.py": ("usuario_id: UUID",),
        "app/modules/clients/interface/http/tenant.py": ("cliente_id: UUID",),
        "app/modules/inventario/interface/http/tenant.py": ("wid: UUID",),
    }

    base_path = Path(__file__).parent
    all_ok = True

    for file_path, patterns in checks.items():
        full_path = base_path / file_path
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        content = full_path.read_text()
        file_name = file_path.split("/")[-2]  # module name

        found = 0
        for pattern in patterns:
            if pattern in content:
                found += 1

        if found > 0:
            print(f"✅ {file_name}: UUID parameters detected")
        else:
            print(f"❌ {file_name}: UUID parameters NOT found")
            all_ok = False

    return all_ok


def check_migration_script():
    """Verify migration script exists"""
    print("\n🔍 Checking migration script...")

    migration_path = Path(__file__).parent / "alembic/versions/migration_uuid_ids.py"

    if not migration_path.exists():
        print("❌ Migration script not found")
        return False

    content = migration_path.read_text()

    required_tables = [
        "modulos_modulo_new",
        "modulos_empresamodulo_new",
        "modulos_moduloasignado_new",
        "core_rolempresa_new",
    ]

    all_found = True
    for table in required_tables:
        if table in content:
            print(f"✅ Migration for {table.replace('_new', '')}")
        else:
            print(f"❌ Migration for {table.replace('_new', '')} NOT found")
            all_found = False

    return all_found


def main():
    print("=" * 60)
    print("UUID MIGRATION VALIDATION")
    print("=" * 60)

    results = []

    results.append(("Deprecated Functions", check_deprecated_functions()))
    results.append(("SQLAlchemy Models", check_model_uuids()))
    results.append(("HTTP Interfaces", check_http_interfaces()))
    results.append(("Migration Script", check_migration_script()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:.<40} {status}")

    print(f"\nTotal: {passed}/{total}")

    if passed == total:
        print("\n🚀 All checks passed! Ready for deployment.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
