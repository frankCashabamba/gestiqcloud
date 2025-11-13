#!/usr/bin/env python
"""
Script: Inicializar datos demo para POS
Uso: python scripts/init_pos_demo.py
"""

import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps"))
)

from sqlalchemy import text
from app.db.session import SessionLocal


def main():
    """Crear datos demo para testing POS"""

    db = SessionLocal()

    try:
        print("🔍 Verificando tenant...")

        # Obtener primer tenant
        tenant_query = text("SELECT id, name FROM tenants LIMIT 1")
        tenant = db.execute(tenant_query).first()

        if not tenant:
            print("❌ No hay tenants. Creando uno...")
            create_tenant = text("""
                INSERT INTO tenants (name, country, plan)
                VALUES ('Empresa Demo', 'EC', 'basic')
                RETURNING id, name
            """)
            tenant = db.execute(create_tenant).first()
            db.commit()

        tenant_id = str(tenant[0])
        print(f"✅ Usando tenant: {tenant[1]} ({tenant_id[:8]}...)")

        # Crear registro POS si no existe
        print("\n🔍 Verificando registro POS...")

        register_query = text("""
            SELECT id, name FROM pos_registers
            WHERE tenant_id = :tenant_id
            LIMIT 1
        """)

        register = db.execute(register_query, {"tenant_id": tenant_id}).first()

        if not register:
            print("   Creando registro POS...")
            create_register = text("""
                INSERT INTO pos_registers (tenant_id, name, active)
                VALUES (:tenant_id, 'Caja Principal', true)
                RETURNING id, name
            """)
            register = db.execute(create_register, {"tenant_id": tenant_id}).first()
            db.commit()

        register_id = str(register[0])
        print(f"✅ Registro POS: {register[1]} ({register_id[:8]}...)")

        # Crear productos demo si no existen
        print("\n🔍 Verificando productos...")

        products_query = text("""
            SELECT COUNT(*) FROM products
            WHERE empresa_id = (SELECT empresa_id FROM tenants WHERE id = :tenant_id)
        """)

        products_count = db.execute(products_query, {"tenant_id": tenant_id}).scalar()

        if products_count < 5:
            print("   Creando productos demo...")

            demo_products = [
                ("PROD001", "Coca Cola 500ml", Decimal("1.50"), "unit"),
                ("PROD002", "Pan Integral", Decimal("0.75"), "unit"),
                ("PROD003", "Leche Entera 1L", Decimal("1.20"), "unit"),
                ("PROD004", "Queso Fresco", Decimal("4.50"), "kg"),
                ("PROD005", "Manzanas", Decimal("2.30"), "kg"),
            ]

            for sku, name, price, uom in demo_products:
                insert_product = text("""
                    INSERT INTO products (
                        empresa_id, sku, nombre, precio, unidad_medida, activo
                    )
                    SELECT 
                        empresa_id, :sku, :nombre, :precio, :uom, true
                    FROM tenants
                    WHERE id = :tenant_id
                    ON CONFLICT (sku) DO NOTHING
                """)

                db.execute(
                    insert_product,
                    {
                        "tenant_id": tenant_id,
                        "sku": sku,
                        "nombre": name,
                        "precio": float(price),
                        "uom": uom,
                    },
                )

            db.commit()
            print(f"✅ {len(demo_products)} productos creados")
        else:
            print(f"✅ Ya existen {products_count} productos")

        # Crear cliente demo
        print("\n🔍 Verificando cliente...")

        customer_query = text("""
            SELECT id, nombre FROM clientes
            WHERE empresa_id = (SELECT empresa_id FROM tenants WHERE id = :tenant_id)
            LIMIT 1
        """)

        customer = db.execute(customer_query, {"tenant_id": tenant_id}).first()

        if not customer:
            print("   Creando cliente demo...")
            create_customer = text("""
                INSERT INTO clientes (
                    empresa_id, nombre, identificacion, pais, email
                )
                SELECT 
                    empresa_id, 'Cliente Demo', '0999999999', 'EC', 'demo@example.com'
                FROM tenants
                WHERE id = :tenant_id
                RETURNING id, nombre
            """)
            customer = db.execute(create_customer, {"tenant_id": tenant_id}).first()
            db.commit()

        print(f"✅ Cliente: {customer[1]} ({customer[0]})")

        # Crear series de numeración
        print("\n📝 Creando series de numeración...")
        from app.services.numbering import create_default_series
        from uuid import UUID

        try:
            create_default_series(db, tenant_id, register_id=None)
            create_default_series(db, tenant_id, register_id=UUID(register_id))
            print("✅ Series de numeración creadas")
        except Exception as e:
            print(f"⚠️  {e}")

        # Resumen
        print("\n" + "=" * 60)
        print("✅ DATOS DEMO INICIALIZADOS")
        print("=" * 60)
        print(f"\n🏢 Tenant ID: {tenant_id}")
        print(f"🏪 Register ID: {register_id}")
        print(
            f"\n📦 Productos: {products_count + 5 if products_count < 5 else products_count}"
        )
        print("👤 Clientes: 1+")
        print("\n🚀 Ahora puedes:")
        print("   1. Abrir turno: POST /api/v1/pos/shifts")
        print("   2. Crear ticket: POST /api/v1/pos/receipts")
        print("   3. Convertir a factura: POST /api/v1/pos/receipts/{id}/to_invoice")
        print("\n📚 Ver ejemplos completos en: MIGRATION_PLAN.md")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  GESTIQCLOUD - Inicialización Demo POS")
    print("=" * 60)
    print()

    main()
