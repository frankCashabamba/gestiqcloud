#!/usr/bin/env python3
"""
Seed Default Settings para todos los Tenants
Crear TenantSettings con configuración por defecto según país
"""

import argparse
import sys
import traceback
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config.database import get_db_url
from app.models.core.settings import TenantSettings
from app.models.empresa.tenant import Tenant
from app.modules.settings.application.use_cases import SettingsManager

# Agregar el directorio apps/backend al path
backend_path = Path(__file__).resolve().parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))


def seed_default_settings():
    """Crear settings por defecto para todos los tenants que no tienen"""

    # Conectar a la base de datos
    db_url = get_db_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    print("=" * 60)
    print("SEED DEFAULT SETTINGS")
    print("=" * 60)

    try:
        # Obtener todos los tenants
        tenants = db.query(Tenant).all()
        print(f"\n✓ Encontrados {len(tenants)} tenants")

        if not tenants:
            print("\n⚠️  No hay tenants en la base de datos")
            print("   Ejecuta primero el script de creación de tenants")
            return

        manager = SettingsManager(db)
        created_count = 0
        existing_count = 0
        error_count = 0

        for tenant in tenants:
            try:
                print(f"\n[{tenant.name}]")
                print(f"  UUID: {tenant.id}")
                print(f"  País: {tenant.country}")

                # Verificar si ya existe
                existing = (
                    db.query(TenantSettings)
                    .filter(TenantSettings.tenant_id == tenant.id)
                    .first()
                )

                if existing:
                    print("  ✓ Settings ya existen")
                    existing_count += 1
                    continue

                # Crear settings por defecto
                result = manager.init_default_settings(
                    tenant_id=tenant.id, country=tenant.country
                )

                if result.get("created"):
                    print("  ✅ Settings creados:")
                    print(f"     - Locale: {result['locale']}")
                    print(f"     - Timezone: {result['timezone']}")
                    print(f"     - Currency: {result['currency']}")
                    print(f"     - Módulos: {result['modules_count']}")
                    created_count += 1
                else:
                    print(f"  ℹ️  {result.get('message', 'Ya existían')}")
                    existing_count += 1

            except Exception as e:
                print(f"  ❌ Error: {e}")
                error_count += 1
                continue

        # Resumen
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        print(f"Total tenants: {len(tenants)}")
        print(f"✅ Settings creados: {created_count}")
        print(f"✓  Settings existentes: {existing_count}")
        if error_count > 0:
            print(f"❌ Errores: {error_count}")
        print()

        # Mostrar detalles de módulos para el primer tenant
        if tenants:
            first_tenant = tenants[0]
            print("\n" + "=" * 60)
            print(f"MÓDULOS DISPONIBLES - {first_tenant.name}")
            print("=" * 60)

            modules = manager.get_available_modules(first_tenant.id)
            for module in modules:
                enabled_icon = "✅" if module.get("is_enabled", False) else "⬜"
                required_icon = "🔒" if module.get("required", False) else "  "
                print(
                    f"{enabled_icon} {required_icon} {module['icon']} {module['name']} ({module['id']})"
                )
                print(f"      {module['description']}")

            print(f"\nTotal módulos: {len(modules)}")
            enabled_count = sum(1 for m in modules if m.get("is_enabled", False))
            print(f"Habilitados: {enabled_count}")

        print("\n✓ Seed completado exitosamente\n")

    except Exception as e:
        print(f"\n❌ Error general: {e}")

        traceback.print_exc()

    finally:
        db.close()


def verify_settings():
    """Verificar que todos los tenants tengan settings"""

    db_url = get_db_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE SETTINGS")
    print("=" * 60)

    try:
        # Query para verificar
        query = text(
            """
            SELECT
                t.id,
                t.name,
                t.country,
                ts.id IS NOT NULL as has_settings,
                ts.currency,
                jsonb_object_keys(ts.settings) as modules
            FROM tenants t
            LEFT JOIN tenant_settings ts ON t.id = ts.tenant_id
            ORDER BY t.name
        """
        )

        result = db.execute(query)
        rows = result.fetchall()

        tenants_with_settings = 0
        tenants_without_settings = 0

        for row in rows:
            if row.has_settings:
                tenants_with_settings += 1
                print(f"✅ {row.name} ({row.country}) - {row.currency}")
            else:
                tenants_without_settings += 1
                print(f"❌ {row.name} ({row.country}) - SIN SETTINGS")

        print(f"\nTenants con settings: {tenants_with_settings}")
        print(f"Tenants sin settings: {tenants_without_settings}")

    except Exception as e:
        print(f"Error en verificación: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed default settings para tenants")
    parser.add_argument(
        "--verify", action="store_true", help="Solo verificar, no crear"
    )

    args = parser.parse_args()

    if args.verify:
        verify_settings()
    else:
        seed_default_settings()
        print("\n" + "-" * 60)
        verify_settings()
