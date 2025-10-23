#!/usr/bin/env python3
"""
Script para crear mapping de importación para diarios de panadería.

Ejecutar después de tener el backend corriendo:
python scripts/create_panaderia_mapping.py
"""

import requests
import json
import sys
import os

# Configuración
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TOKEN = os.getenv("API_TOKEN")  # Debe estar configurado

def create_panaderia_mapping():
    """Crea un mapping para importar diarios de panadería desde Excel."""

    # Mapping de columnas Excel a campos normalizados
    mapping = {
        "fecha": ["Fecha", "FECHA", "Date", "DATE"],
        "producto": ["Producto", "PRODUCTO", "Product", "PRODUCT"],
        "cantidad_producida": ["Cantidad", "CANTIDAD", "Qty", "QTY", "Cantidad Producida"],
        "unidad": ["Unidad", "UNIDAD", "Unit", "UNIT", "UOM"],
        "harina_kg": ["Harina KG", "HARINA_KG", "Harina (kg)"],
        "levadura_g": ["Levadura G", "LEVADURA_G", "Levadura (g)"],
        "manteca_kg": ["Manteca KG", "MANTECA_KG", "Manteca (kg)"],
        "azucar_kg": ["Azucar KG", "AZUCAR_KG", "Azúcar (kg)"],
        "sal_g": ["Sal G", "SAL_G", "Sal (g)"],
        "notas": ["Notas", "NOTAS", "Notes", "OBSERVACIONES"]
    }

    # Transformaciones (ejemplos)
    transforms = {
        "fecha": "date",  # Convertir a formato ISO
        "cantidad_producida": "float",
        "harina_kg": "float",
        "levadura_g": "float"
    }

    # Valores por defecto
    defaults = {
        "unidad": "unidades"  # Si no especificada
    }

    # Claves para deduplicación
    dedupe_keys = ["fecha", "producto", "cantidad_producida"]

    payload = {
        "name": "Diario Panadería Estándar",
        "source_type": "panaderia_diario",
        "version": 1,
        "mappings": mapping,
        "transforms": transforms,
        "defaults": defaults,
        "dedupe_keys": dedupe_keys
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{API_BASE}/api/v1/imports/mappings",
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Mapping creado exitosamente: {data['id']}")
            print(f"Nombre: {data['name']}")
            print(f"Tipo: {data['source_type']}")
            return data['id']
        else:
            print(f"❌ Error al crear mapping: {response.status_code}")
            print(response.text)
            return None

    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

if __name__ == "__main__":
    if not TOKEN:
        print("❌ API_TOKEN no configurado. Configure la variable de entorno API_TOKEN")
        sys.exit(1)

    print("Creando mapping para diarios de panadería...")
    mapping_id = create_panaderia_mapping()

    if mapping_id:
        print(f"\n🎉 Mapping listo. Ahora puedes importar Excel con diarios de panadería.")
        print("Ejemplo de columnas esperadas en el Excel:")
        print("- Fecha (dd/mm/yyyy)")
        print("- Producto (ej: Pan blanco)")
        print("- Cantidad (número)")
        print("- Unidad (opcional: kg, unidades, etc.)")
        print("- Harina KG, Levadura G, etc. (opcional)")
    else:
        print("\n❌ Falló la creación del mapping.")
        sys.exit(1)
