#!/usr/bin/env python
"""
Test script para validar la funcionalidad de Precio Sugerido desde Receta

Uso:
    python test_suggested_price.py
"""

import json
import requests
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
TENANT_ID = "your-tenant-id"  # Reemplazar con tu tenant ID
API_KEY = "your-api-key"      # Reemplazar con tu API key

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_create_product_with_recipe():
    """Test 1: Crear producto y asignarle una receta"""
    print_section("Test 1: Crear Producto con Receta")
    
    # Crear producto
    product_data = {
        "name": "PAN TAPADO TEST",
        "price": 0.0,
        "stock": 0,
        "unit": "unit",
        "category": "Panadería",
        "sku": "PAN-TEST-001"
    }
    
    resp = requests.post(
        f"{BASE_URL}/api/v1/tenant/products",
        headers=headers,
        json=product_data
    )
    
    if resp.status_code not in [200, 201]:
        print(f"❌ Error creando producto: {resp.status_code}")
        print(resp.text)
        return None
    
    product = resp.json()
    product_id = product.get("id")
    print(f"✓ Producto creado: {product_id}")
    print(f"  Nombre: {product.get('name')}")
    print(f"  Precio inicial: {product.get('price')}")
    
    return product_id

def test_create_recipe_with_ingredients(product_id):
    """Test 2: Crear receta con ingredientes para calcular costo"""
    print_section("Test 2: Crear Receta con Ingredientes")
    
    # Suponer que ya tenemos IDs de productos ingredientes
    # En un test real, habría que crearlos primero
    
    recipe_data = {
        "name": "Receta PAN TAPADO",
        "product_id": product_id,
        "yield_qty": 216,
        "prep_time_minutes": 30,
        "instructions": "Mezclar, fermentar, hornear",
        "is_active": True,
        "ingredients": [
            {
                "product_id": "ingredient-id-1",
                "qty": 50,
                "unit": "lb",
                "purchase_packaging": "Bag 110 lbs",
                "qty_per_package": 110,
                "package_unit": "lb",
                "package_cost": 35.00,
                "notes": "Harina"
            }
            # Agregar más ingredientes según sea necesario
        ]
    }
    
    resp = requests.post(
        f"{BASE_URL}/api/v1/tenant/recipes",
        headers=headers,
        json=recipe_data
    )
    
    if resp.status_code not in [200, 201]:
        print(f"❌ Error creando receta: {resp.status_code}")
        print(resp.text)
        return None
    
    recipe = resp.json()
    recipe_id = recipe.get("id")
    print(f"✓ Receta creada: {recipe_id}")
    print(f"  Nombre: {recipe.get('name')}")
    print(f"  Rendimiento: {recipe.get('yield_qty')} unidades")
    print(f"  Costo total: ${recipe.get('total_cost')}")
    print(f"  Costo por unidad: ${recipe.get('unit_cost')}")
    
    return recipe_id

def test_sync_product_price(recipe_id):
    """Test 3: Sincronizar precio sugerido del producto"""
    print_section("Test 3: Sincronizar Precio Sugerido")
    
    resp = requests.post(
        f"{BASE_URL}/api/v1/tenant/recipes/{recipe_id}/sync-product-price",
        headers=headers
    )
    
    if resp.status_code not in [200, 201]:
        print(f"❌ Error sincronizando precio: {resp.status_code}")
        print(resp.text)
        return None
    
    result = resp.json()
    print(f"✓ Sincronización exitosa")
    print(f"  Precio sugerido: ${result.get('suggested_price')}")
    print(f"  Costo unitario: ${result.get('unit_cost')}")
    print(f"  Mensaje: {result.get('message')}")
    
    return result

def test_get_product_with_suggested_price(product_id):
    """Test 4: Obtener producto y verificar precio sugerido"""
    print_section("Test 4: Verificar Producto con Precio Sugerido")
    
    resp = requests.get(
        f"{BASE_URL}/api/v1/tenant/products/{product_id}",
        headers=headers
    )
    
    if resp.status_code != 200:
        print(f"❌ Error obteniendo producto: {resp.status_code}")
        print(resp.text)
        return None
    
    product = resp.json()
    print(f"✓ Producto obtenido: {product.get('id')}")
    print(f"  Nombre: {product.get('name')}")
    print(f"  Precio actual: ${product.get('price')}")
    print(f"  Precio sugerido: ${product.get('suggested_price')}")
    print(f"  Usar precio sugerido: {product.get('use_suggested_price')}")
    
    return product

def test_apply_suggested_price(product_id):
    """Test 5: Aplicar precio sugerido al producto"""
    print_section("Test 5: Aplicar Precio Sugerido")
    
    # Primero obtener el producto
    resp = requests.get(
        f"{BASE_URL}/api/v1/tenant/products/{product_id}",
        headers=headers
    )
    
    if resp.status_code != 200:
        print(f"❌ Error obteniendo producto: {resp.status_code}")
        return None
    
    product = resp.json()
    suggested_price = product.get('suggested_price')
    
    if not suggested_price:
        print(f"❌ Producto no tiene precio sugerido")
        return None
    
    # Actualizar producto para usar precio sugerido
    update_data = {
        "use_suggested_price": True,
        "price": suggested_price
    }
    
    resp = requests.put(
        f"{BASE_URL}/api/v1/tenant/products/{product_id}",
        headers=headers,
        json=update_data
    )
    
    if resp.status_code != 200:
        print(f"❌ Error actualizando producto: {resp.status_code}")
        print(resp.text)
        return None
    
    updated = resp.json()
    print(f"✓ Producto actualizado")
    print(f"  Precio aplicado: ${updated.get('price')}")
    print(f"  Usar precio sugerido: {updated.get('use_suggested_price')}")
    
    return updated

def main():
    print("\n" + "="*60)
    print("  TEST: Suggested Price Feature")
    print("="*60)
    
    # Verificar configuración
    if API_KEY == "your-api-key":
        print("\n⚠️  ADVERTENCIA: Reemplaza API_KEY con tu clave válida")
        print("   Edita las variables en el script")
        return
    
    # Ejecutar tests
    product_id = test_create_product_with_recipe()
    if not product_id:
        print("\n❌ No se pudo crear producto. Abortando tests.")
        return
    
    recipe_id = test_create_recipe_with_ingredients(product_id)
    if not recipe_id:
        print("\n⚠️  No se pudo crear receta. Saltando tests de sincronización.")
    else:
        sync_result = test_sync_product_price(recipe_id)
        product = test_get_product_with_suggested_price(product_id)
        
        if product and product.get('suggested_price'):
            test_apply_suggested_price(product_id)
    
    print_section("Tests Completados")
    print("✓ Todos los tests han finalizado\n")

if __name__ == "__main__":
    main()
