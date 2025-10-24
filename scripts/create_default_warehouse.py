#!/usr/bin/env python3
"""
Script: Crear almacén por defecto para tenant
Ejecutar antes de importar Excel
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.config.database import SessionLocal


def create_default_warehouse(tenant_id: str, name: str = "Almacén Principal"):
    """Crear almacén por defecto para un tenant"""
    db = SessionLocal()
    
    try:
        # Verificar si ya existe
        check = db.execute(
            text("""
                SELECT id FROM warehouses
                WHERE tenant_id = :tenant_id::uuid AND is_default = true
            """),
            {"tenant_id": tenant_id}
        ).fetchone()
        
        if check:
            print(f"✅ Almacén por defecto ya existe: {check[0]}")
            return check[0]
        
        # Crear almacén
        result = db.execute(
            text("""
                INSERT INTO warehouses (tenant_id, code, name, is_active, is_default)
                VALUES (:tenant_id::uuid, 'MAIN', :name, true, true)
                RETURNING id, code, name
            """),
            {"tenant_id": tenant_id, "name": name}
        ).fetchone()
        
        db.commit()
        
        print(f"✅ Almacén creado: ID={result[0]}, Código={result[1]}, Nombre={result[2]}")
        return result[0]
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return None
    
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python create_default_warehouse.py <TENANT_UUID> [nombre]")
        print("Ejemplo: python create_default_warehouse.py 123e4567-e89b-12d3-a456-426614174000 'Almacén Principal'")
        sys.exit(1)
    
    tenant_id = sys.argv[1]
    warehouse_name = sys.argv[2] if len(sys.argv) > 2 else "Almacén Principal"
    
    create_default_warehouse(tenant_id, warehouse_name)
