#!/usr/bin/env python
"""
Script: Crear series de numeración por defecto
Uso: python scripts/create_default_series.py
"""

import sys
import os

# Añadir paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps"))
)

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.numbering import create_default_series


def main():
    """Crear series de numeración por defecto para tenants"""

    db = SessionLocal()

    try:
        # Obtener todos los tenants
        query = text("SELECT id, name FROM tenants ORDER BY created_at")
        tenants = db.execute(query).fetchall()

        if not tenants:
            print("⚠️  No hay tenants en la base de datos")
            print("   Primero crea un tenant con:")
            print(
                "   INSERT INTO tenants (name, country, plan) VALUES ('Mi Empresa', 'EC', 'basic');"
            )
            return

        print(f"📝 Encontrados {len(tenants)} tenant(s):")
        for tenant in tenants:
            print(f"   - {tenant[1]} ({tenant[0]})")

        print("\n🔧 Creando series de numeración...")

        for tenant_id, tenant_name in tenants:
            print(f"\n📋 Tenant: {tenant_name}")

            # Series backoffice (register_id = None)
            try:
                create_default_series(db, str(tenant_id), register_id=None)
                print("   ✅ Series backoffice creadas")
            except Exception as e:
                print(f"   ⚠️  Error backoffice: {e}")

            # Verificar si hay registros POS
            check_registers = text("""
                SELECT id, name FROM pos_registers
                WHERE tenant_id = :tenant_id
                ORDER BY created_at
            """)

            registers = db.execute(
                check_registers, {"tenant_id": str(tenant_id)}
            ).fetchall()

            if registers:
                print(f"   📦 Encontrados {len(registers)} registro(s) POS:")
                for reg_id, reg_name in registers:
                    try:
                        from uuid import UUID

                        create_default_series(
                            db, str(tenant_id), register_id=UUID(reg_id)
                        )
                        print(f"      ✅ Series POS creadas para: {reg_name}")
                    except Exception as e:
                        print(f"      ⚠️  Error en {reg_name}: {e}")
            else:
                print("   ℹ️  No hay registros POS (se usarán series backoffice)")

        print("\n✅ Proceso completado")

        # Mostrar resumen
        count_query = text("""
            SELECT 
                doc_type,
                COUNT(*) as total,
                COUNT(CASE WHEN register_id IS NULL THEN 1 END) as backoffice,
                COUNT(CASE WHEN register_id IS NOT NULL THEN 1 END) as pos
            FROM doc_series
            WHERE active = true
            GROUP BY doc_type
            ORDER BY doc_type
        """)

        summary = db.execute(count_query).fetchall()

        if summary:
            print("\n📊 Resumen de series activas:")
            print("   Tipo | Total | Backoffice | POS")
            print("   -----|-------|------------|----")
            for doc_type, total, backoffice, pos in summary:
                type_name = {"R": "Recibos", "F": "Facturas", "C": "Abonos"}.get(
                    doc_type, doc_type
                )
                print(f"   {type_name:8} | {total:5} | {backoffice:10} | {pos:3}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  GESTIQCLOUD - Creación de Series de Numeración")
    print("=" * 60)
    print()

    main()
