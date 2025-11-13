#!/usr/bin/env python3
"""
Script para crear mapping automático de productos.
Mapea columnas típicas de Excel en español a esquema estándar.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from sqlalchemy import text

from app.config.database import SessionLocal
from app.models.core.modelsimport import ImportMapping


def create_product_mapping():
    """Crea mapping predefinido para productos en español."""

    db = SessionLocal()
    try:
        # Mapeo de columnas típicas en español a esquema estándar
        mappings = {
            # Nombre del producto
            "PRODUCTO": "nombre",
            "NOMBRE": "nombre",
            "DESCRIPCION": "nombre",
            "DESCRIPCIÓN": "nombre",
            # Precio
            "PRECIO UNITARIO VENTA": "precio",
            "PRECIO": "precio",
            "PVP": "precio",
            "PRECIO VENTA": "precio",
            # Stock/Cantidad
            "CANTIDAD": "stock",
            "STOCK": "stock",
            "EXISTENCIA": "stock",
            "SOBRANTE DIARIO": "stock",
            # Código
            "CODIGO": "codigo",
            "CÓDIGO": "codigo",
            "SKU": "codigo",
            "REFERENCIA": "codigo",
            # Categoría
            "CATEGORIA": "categoria",
            "CATEGORÍA": "categoria",
            "FAMILIA": "categoria",
            # Costo
            "COSTO": "costo",
            "PRECIO COMPRA": "costo",
            "COSTE": "costo",
            # Unidad
            "UNIDAD": "unidad",
            "UOM": "unidad",
            # IVA
            "IVA": "iva",
            "IMPUESTO": "iva",
        }

        # Defaults para campos que suelen faltar
        defaults = {
            "unidad": "unit",
            "iva": 0,
            "stock": 0,
        }

        # Buscar si ya existe un mapping de productos
        existing = (
            db.query(ImportMapping)
            .filter_by(source_type="productos", name="Productos Estándar (Español)")
            .first()
        )

        if existing:
            print(f"✅ Actualizando mapping existente ID={existing.id}")
            existing.mappings = mappings
            existing.defaults = defaults
        else:
            print("✅ Creando nuevo mapping de productos")
            # Necesitamos un empresa_id válido - tomamos el primero disponible
            first_empresa = db.execute(
                text("SELECT id FROM core_empresa LIMIT 1")
            ).first()
            if not first_empresa:
                raise ValueError("No hay empresas en la BD. Crea una empresa primero.")

            mapping = ImportMapping(
                empresa_id=first_empresa[0],
                source_type="productos",
                name="Productos Estándar (Español)",
                mappings=mappings,
                defaults=defaults,
                transforms={},
                dedupe_keys=["nombre"],  # Evitar duplicados por nombre
            )
            db.add(mapping)

        db.commit()
        print(f"✅ Mapping creado/actualizado con {len(mappings)} columnas mapeadas")
        print("\nMapeo de columnas:")
        for src, dst in sorted(mappings.items()):
            print(f"  {src:30} → {dst}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_product_mapping()
