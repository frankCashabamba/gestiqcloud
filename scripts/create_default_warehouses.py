#!/usr/bin/env python3
"""
Script para crear almacenes por defecto para todos los tenants.
Ejecutar después de aplicar migración de warehouses.
"""

import sys
from pathlib import Path

# Add project root to path
backend_path = Path(__file__).resolve().parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config.database import get_db_url


def create_default_warehouses():
    """Crear almacén por defecto para cada tenant que no tenga ninguno"""
    
    engine = create_engine(get_db_url())
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Obtener tenants sin almacén
        tenants_without_warehouse = db.execute(text("""
            SELECT t.id, t.name, t.country
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM warehouses w WHERE w.tenant_id = t.id
            )
        """)).fetchall()
        
        if not tenants_without_warehouse:
            print("Todos los tenants ya tienen almacenes configurados.")
            return
        
        print(f"Creando almacenes por defecto para {len(tenants_without_warehouse)} tenants...\n")
        
        for tenant in tenants_without_warehouse:
            tenant_id, tenant_name, country = tenant
            
            # Crear almacén principal
            db.execute(text("""
                INSERT INTO warehouses (
                    tenant_id, code, name, is_default, active, country
                ) VALUES (
                    :tid, 'PRINCIPAL', :name, TRUE, TRUE, :country
                )
            """), {
                "tid": tenant_id,
                "name": f"Almacén Principal - {tenant_name}",
                "country": country or 'ES'
            })
            
            print(f"✓ Almacén creado para tenant: {tenant_name} ({tenant_id})")
        
        db.commit()
        print(f"\n{len(tenants_without_warehouse)} almacenes creados exitosamente.")
        
    except Exception as e:
        db.rollback()
        print(f"\nError al crear almacenes: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_default_warehouses()
