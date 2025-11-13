#!/usr/bin/env python3
"""
Script directo para importar Excel a la base de datos.
Uso: python scripts/import_excel_direct.py <ruta_excel> <tenant_id>
"""

import sys
import os
from pathlib import Path
import traceback
import pandas as pd
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.modules.imports.application.handlers import promote_items_to_productos
from app.models.core.modelsimport import ImportBatch, ImportItem
from datetime import datetime
from uuid import uuid4


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "apps" / "backend"))
sys.path.insert(0, str(project_root / "apps"))

os.environ.setdefault(
    "DB_DSN", "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
)
os.environ.setdefault("IMPORTS_ENABLED", "1")



def import_excel(file_path: str, tenant_id: str):
    """Importa un Excel directamente a productos."""

    if not Path(file_path).exists():
        print(f"❌ Archivo no encontrado: {file_path}")
        return 1

    print(f"📂 Leyendo archivo: {file_path}")

    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        print(f"❌ Error al leer Excel: {e}")
        return 1

    print(f"✅ Leídas {len(df)} filas, columnas: {list(df.columns)}")

    # Create batch
    db: Session = SessionLocal()
    try:
        batch = ImportBatch(
            id=uuid4(),
            tenant_id=tenant_id,
            entity_type="productos",
            status="draft",
            created_at=datetime.utcnow(),
        )
        db.add(batch)
        db.flush()
        print(f"✅ Batch creado: {batch.id}")

        # Add items
        item_count = 0
        for idx, row in df.iterrows():
            # Map columns (adjust based on your Excel structure)
            data_raw = row.to_dict()

            # Auto-map common fields
            item_data = {}

            # Nombre/Name
            for col in ["nombre", "name", "producto", "Nombre", "Name", "Producto"]:
                if col in data_raw and pd.notna(data_raw[col]):
                    item_data["nombre"] = str(data_raw[col])
                    break

            # SKU/Codigo
            for col in ["sku", "codigo", "code", "SKU", "Codigo", "Code"]:
                if col in data_raw and pd.notna(data_raw[col]):
                    item_data["sku"] = str(data_raw[col])
                    break

            # Precio
            for col in ["precio", "price", "Precio", "Price", "precio_venta", "pvp"]:
                if col in data_raw and pd.notna(data_raw[col]):
                    try:
                        item_data["precio"] = float(data_raw[col])
                    except Exception:
                        pass
                    break

            # Categoria
            for col in ["categoria", "category", "Categoria", "Category"]:
                if col in data_raw and pd.notna(data_raw[col]):
                    item_data["categoria"] = str(data_raw[col])
                    break

            # Código de barras
            for col in ["codigo_barras", "barcode", "ean", "Codigo_Barras", "EAN"]:
                if col in data_raw and pd.notna(data_raw[col]):
                    item_data["codigo_barras"] = str(data_raw[col])
                    break

            if not item_data.get("nombre"):
                print(f"⚠️  Fila {idx + 1}: Sin nombre, saltando")
                continue

            item = ImportItem(
                id=uuid4(),
                batch_id=batch.id,
                row_index=idx,
                data_raw=data_raw,
                data_normalized=item_data,
                validation_status="valid",
                created_at=datetime.utcnow(),
            )
            db.add(item)
            item_count += 1

        db.commit()
        print(f"✅ {item_count} items agregados al batch")

        # Promote to productos
        print("🚀 Promoviendo items a productos...")
        batch.status = "validated"
        db.commit()

        result = promote_items_to_productos(db, batch.id, tenant_id)

        print("✅ Importación completa:")
        print(f"   - Creados: {result.get('created', 0)}")
        print(f"   - Actualizados: {result.get('updated', 0)}")
        print(f"   - Errores: {result.get('errors', 0)}")

        return 0

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/import_excel_direct.py <ruta_excel> <tenant_id>")
        print(
            "Ejemplo: python scripts/import_excel_direct.py 22-10-20251.xlsx 00000000-0000-0000-0000-000000000001"
        )
        sys.exit(1)

    excel_path = sys.argv[1]
    tenant_id = sys.argv[2]

    sys.exit(import_excel(excel_path, tenant_id))
