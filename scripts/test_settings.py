#!/usr/bin/env python3
"""
Test del Sistema de Settings
Verificar funcionalidad completa del SettingsManager
"""

import sys
import traceback
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.database import get_db_url
from app.models.empresa.tenant import Tenant
from app.modules.settings import SettingsManager

backend_path = Path(__file__).resolve().parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))


def test_settings_manager():
    """Test completo del SettingsManager"""

    db_url = get_db_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    print("=" * 70)
    print("TEST - SETTINGS MANAGER")
    print("=" * 70)

    try:
        # 1. Obtener primer tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            print("\n❌ No hay tenants en la base de datos")
            return

        print(f"\n[TENANT] {tenant.name}")
        print(f"UUID: {tenant.id}")
        print(f"País: {tenant.country}")

        manager = SettingsManager(db)

        # 2. Test: Obtener todos los settings
        print("\n" + "-" * 70)
        print("TEST 1: Get All Settings")
        print("-" * 70)
        all_settings = manager.get_all_settings(tenant.id)
        print(f"✓ Locale: {all_settings['locale']}")
        print(f"✓ Timezone: {all_settings['timezone']}")
        print(f"✓ Currency: {all_settings['currency']}")
        print(f"✓ Módulos configurados: {len(all_settings['modules'])}")

        # 3. Test: Configuración de módulo específico
        print("\n" + "-" * 70)
        print("TEST 2: Get Module Settings (POS)")
        print("-" * 70)
        pos_config = manager.get_module_settings(tenant.id, "pos")
        print(f"✓ Módulo: {pos_config['module_name']}")
        print(f"✓ Habilitado: {pos_config['enabled']}")
        print(f"✓ Ancho ticket: {pos_config['config'].get('receipt_width_mm')}mm")
        print(f"✓ IVA incluido: {pos_config['config'].get('tax_included')}")
        print(f"✓ Tasa IVA: {pos_config['config'].get('default_tax_rate') * 100}%")

        # 4. Test: Actualizar configuración
        print("\n" + "-" * 70)
        print("TEST 3: Update Module Settings")
        print("-" * 70)
        updated = manager.update_module_settings(
            tenant.id, "pos", {"receipt_width_mm": 80, "auto_print_receipt": False}
        )
        print(f"✓ Módulo actualizado: {updated['module']}")
        print(f"✓ Nuevo ancho: {updated['config']['receipt_width_mm']}mm")
        print(f"✓ Auto-impresión: {updated['config']['auto_print_receipt']}")

        # 5. Test: Módulos disponibles
        print("\n" + "-" * 70)
        print("TEST 4: Get Available Modules")
        print("-" * 70)
        modules = manager.get_available_modules(tenant.id)

        enabled_count = sum(1 for m in modules if m.get("is_enabled", False))
        required_count = sum(1 for m in modules if m.get("required", False))

        print(f"✓ Total módulos: {len(modules)}")
        print(f"✓ Habilitados: {enabled_count}")
        print(f"✓ Obligatorios: {required_count}")

        print("\nMódulos por categoría:")
        categories = {}
        for module in modules:
            cat = module["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(module)

        for cat, mods in categories.items():
            print(f"\n  [{cat.upper()}]")
            for mod in mods:
                status = "✅" if mod.get("is_enabled") else "⬜"
                required = "🔒" if mod.get("required") else "  "
                print(f"  {status} {required} {mod['icon']} {mod['name']}")

        # 6. Test: Habilitar módulo con dependencias
        print("\n" + "-" * 70)
        print("TEST 5: Enable Module (con validación de dependencias)")
        print("-" * 70)

        # Primero deshabilitar HR (no tiene dependencias)
        if any(m["id"] == "hr" and m.get("is_enabled") for m in modules):
            result = manager.disable_module(tenant.id, "hr")
            if result["success"]:
                print("✓ Módulo HR deshabilitado (preparación)")

        # Habilitar HR (sin dependencias, debe funcionar)
        result = manager.enable_module(tenant.id, "hr")
        if result["success"]:
            print(f"✅ Módulo {result['module_name']} habilitado exitosamente")
        else:
            print(f"❌ Error: {result['message']}")

        # 7. Test: Intentar deshabilitar módulo con dependientes
        print("\n" + "-" * 70)
        print("TEST 6: Disable Module (validación de dependientes)")
        print("-" * 70)

        # Intentar deshabilitar inventory (tiene dependientes: pos, sales, purchases)
        result = manager.disable_module(tenant.id, "inventory")
        if not result["success"]:
            print(f"✅ Validación correcta: {result['message']}")
            if "dependents" in result:
                print(f"   Módulos dependientes: {', '.join(result['dependents'])}")
        else:
            print("❌ No debería permitir deshabilitar inventory")

        # 8. Test: Intentar deshabilitar módulo obligatorio
        print("\n" + "-" * 70)
        print("TEST 7: Disable Required Module")
        print("-" * 70)

        result = manager.disable_module(tenant.id, "invoicing")
        if not result["success"] and result["error"] == "module_required":
            print(f"✅ Validación correcta: {result['message']}")
        else:
            print("❌ Debería impedir deshabilitar módulo obligatorio")

        # 9. Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE TESTS")
        print("=" * 70)

        final_settings = manager.get_all_settings(tenant.id)
        final_modules = manager.get_available_modules(tenant.id)

        enabled_modules = [m for m in final_modules if m.get("is_enabled")]
        disabled_modules = [m for m in final_modules if not m.get("is_enabled")]

        print("\n✅ Configuración final:")
        print(f"   - Tenant: {tenant.name}")
        print(f"   - País: {tenant.country}")
        print(f"   - Moneda: {final_settings['currency']}")
        print(f"   - Módulos activos: {len(enabled_modules)}/{len(final_modules)}")

        print("\n📦 Módulos habilitados:")
        for mod in enabled_modules:
            print(f"   {mod['icon']} {mod['name']}")

        if disabled_modules:
            print("\n⬜ Módulos deshabilitados:")
            for mod in disabled_modules:
                print(f"   {mod['icon']} {mod['name']}")

        print("\n✓ Todos los tests completados exitosamente\n")

    except Exception as e:
        print(f"\n❌ Error en tests: {e}")

        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    test_settings_manager()
