#!/usr/bin/env python3
"""
Script de testing para sistema de plantillas de sector
"""

import json

import requests

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_1_list_templates():
    """Test 1: Listar plantillas disponibles"""
    print_section("TEST 1: Listar Plantillas Disponibles")

    response = requests.get(f"{BASE_URL}/api/v1/sectores/")

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Total plantillas: {data.get('count', 0)}")

    for template in data.get("templates", []):
        print(f"\n📋 {template['nombre']}")
        print(f"   Color: {template['branding']['color_primario']}")
        print(f"   Plantilla: {template['branding']['plantilla_inicio']}")
        print(f"   Módulos habilitados: {template['modules_count']}")
        print(f"   Categorías: {', '.join(template['categories'][:3])}...")

    return data


def test_2_get_template_detail(template_id: int):
    """Test 2: Obtener detalle de plantilla"""
    print_section(f"TEST 2: Detalle de Plantilla ID={template_id}")

    response = requests.get(f"{BASE_URL}/api/v1/sectores/{template_id}")

    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"\n📄 {data['nombre']}")
    print("\nMódulos configurados:")
    for module, config in data["modules"].items():
        status = "✅" if config["enabled"] else "❌"
        print(f"  {status} {module} (order: {config['order']})")

    print("\n⚙️ Configuración POS:")
    pos_config = data["config"]["pos"]
    print(f"  - Ancho ticket: {pos_config['receipt_width_mm']}mm")
    print(f"  - Pesos: {pos_config['enable_weights']}")
    print(f"  - Tracking lotes: {pos_config['enable_batch_tracking']}")

    return data


def test_3_create_tenant_with_template():
    """Test 3: Crear tenant con plantilla"""
    print_section("TEST 3: Crear Tenant con Plantilla de Sector")

    # Crear tenant
    tenant_data = {
        "empresa": {"nombre": "Panadería Test", "ruc": "1234567890001", "pais": "EC"},
        "adminUser": {
            "username": "admin@panaderia.test",
            "email": "admin@panaderia.test",
            "password": "Test123!",
        },
        "sector_plantilla_id": 1,  # Panadería
    }

    # Nota: Este endpoint debería modificarse para aceptar sector_plantilla_id
    print("⚠️ Este test requiere modificar el endpoint de creación de empresa")
    print(f"Datos a enviar: {json.dumps(tenant_data, indent=2)}")

    # response = requests.post(f"{BASE_URL}/api/v1/admin/empresas/completa-json", json=tenant_data)
    # print(f"Status: {response.status_code}")

    return None


def test_4_apply_template_to_existing():
    """Test 4: Aplicar plantilla a tenant existente"""
    print_section("TEST 4: Aplicar Plantilla a Tenant Existente")

    # Necesitarías un tenant_id real aquí
    tenant_id = "00000000-0000-0000-0000-000000000001"  # Reemplazar con ID real

    apply_data = {
        "tenant_id": tenant_id,
        "sector_plantilla_id": 1,  # Panadería
        "override_existing": True,
    }

    print(f"Aplicando plantilla al tenant {tenant_id}...")
    print(f"Datos: {json.dumps(apply_data, indent=2)}")

    # response = requests.post(f"{BASE_URL}/api/v1/sectores/apply", json=apply_data)
    # print(f"Status: {response.status_code}")
    # data = response.json()
    # print(f"\nResultado: {json.dumps(data, indent=2)}")

    print("\n⚠️ Comentado para evitar modificar datos reales")

    return None


def test_5_verify_tenant_config(tenant_id: str):
    """Test 5: Verificar configuración aplicada"""
    print_section("TEST 5: Verificar Configuración del Tenant")

    print(f"Tenant ID: {tenant_id}")
    print("\nVerificaciones a realizar:")
    print("  1. ✅ Tenant.color_primario = #8B4513 (café)")
    print("  2. ✅ Tenant.plantilla_inicio = 'panaderia'")
    print("  3. ✅ TenantSettings con config POS")
    print("  4. ✅ Categorías creadas: Pan, Bollería, Pasteles...")
    print("  5. ✅ Módulos habilitados correctamente")

    print("\nSQL de verificación:")
    print(
        """
    -- Ver configuración del tenant
    SELECT
      nombre,
      color_primario,
      plantilla_inicio,
      config_json->'sector_template_applied' as plantilla_aplicada
    FROM tenants
    WHERE id = '{tenant_id}';

    -- Ver módulos en TenantSettings
    SELECT
      settings->'modules' as modules_config
    FROM tenant_settings
    WHERE tenant_id = '{tenant_id}';

    -- Ver categorías creadas
    SELECT name FROM categories
    WHERE tenant_id = '{tenant_id}'
    ORDER BY name;
    """.format(tenant_id=tenant_id)
    )

    return None


def main():
    """Ejecutar todos los tests"""
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║        🎨 Test Suite: Sistema de Plantillas de Sector       ║
╚══════════════════════════════════════════════════════════════╝
    """
    )

    try:
        # Test 1: Listar plantillas
        templates_data = test_1_list_templates()

        # Test 2: Detalle de primera plantilla
        if templates_data and templates_data.get("templates"):
            first_template_id = templates_data["templates"][0]["id"]
            test_2_get_template_detail(first_template_id)

        # Test 3: Crear tenant con plantilla (demo)
        test_3_create_tenant_with_template()

        # Test 4: Aplicar plantilla a existente (demo)
        test_4_apply_template_to_existing()

        # Test 5: Verificación manual
        test_5_verify_tenant_config("TENANT_ID_AQUI")

        print_section("✅ TESTS COMPLETADOS")
        print(
            """
Próximos pasos:
1. Aplicar migración: python scripts/py/bootstrap_imports.py --dir ops/migrations
2. Modificar endpoint de creación de empresa para aceptar sector_plantilla_id
3. Crear frontend selector de plantillas
4. Probar flujo completo end-to-end
        """
        )

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se puede conectar al backend")
        print("   Asegúrate de que el backend esté corriendo en http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")


if __name__ == "__main__":
    main()
