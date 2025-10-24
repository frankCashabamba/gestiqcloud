"""
Endpoint para importar productos desde Excel/CSV
Ruta: POST /api/v1/import-products
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.services.products_importer import ProductsImporter

router = APIRouter(
    prefix="/import-products",
    tags=["Products Import"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.post("")
async def import_products_from_excel(
    file: UploadFile = File(...),
    sheet_name: str = Form("REGISTRO"),
    update_existing: bool = Form(False),
    warehouse_id: str = Form("default"),
    db: Session = Depends(get_db),
):
    """
    Importa catálogo de productos + stock desde Excel/CSV.
    
    **Formato esperado:**
    - PRODUCTO (obligatorio): Nombre del producto
    - CANTIDAD (opcional): Stock disponible
    - PRECIO / PRECIO_VENTA (opcional): Precio de venta
    - CODIGO / SKU (opcional): Código del producto
    - CATEGORIA (opcional): Categoría
    
    **Formatos soportados:** .xlsx, .xls, .csv
    
    **Ejemplo Excel:**
    ```
    PRODUCTO          | CANTIDAD | PRECIO | CATEGORIA
    ------------------|----------|--------|----------
    tapados           | 196      | 0.15   | PAN
    pan dulce-mestizo | 10       | 0.15   | PAN
    empanadas queso   | 30       | 0.20   | SALADOS
    ```
    
    Returns:
        Estadísticas de importación
    """
    # Validar tipo de archivo
    if not file.filename:
        raise HTTPException(400, "No se proporcionó archivo")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".xlsx", ".xls", ".csv"]:
        raise HTTPException(
            400,
            f"Formato no soportado: {file_ext}. Use .xlsx, .xls o .csv"
        )
    
    # Obtener tenant_id del RLS context
    tenant_id_result = db.execute("SELECT current_setting('app.tenant_id', TRUE)").scalar()
    if not tenant_id_result:
        raise HTTPException(403, "tenant_id no configurado en sesión")
    
    tenant_id = str(tenant_id_result)
    
    try:
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext
        ) as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        
        # Importar
        importer = ProductsImporter(
            db=db,
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
        )
        
        # Manejar CSV
        if file_ext == ".csv":
            import pandas as pd
            df = pd.read_csv(tmp_path)
            # Convertir a Excel temporal para reutilizar lógica
            tmp_excel = tmp_path + ".xlsx"
            df.to_excel(tmp_excel, index=False, sheet_name=sheet_name)
            tmp_path = tmp_excel
        
        stats = importer.import_from_excel(
            file_path=tmp_path,
            sheet_name=sheet_name,
            update_existing=update_existing,
        )
        
        # Limpiar archivo temporal
        Path(tmp_path).unlink(missing_ok=True)
        if file_ext == ".csv":
            Path(tmp_path + ".xlsx").unlink(missing_ok=True)
        
        return {
            "status": "success",
            "message": f"{stats['products_created']} productos creados, {stats['stock_initialized']} con stock",
            "stats": stats,
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error al importar: {str(e)}")


@router.get("/template")
def download_template():
    """
    Descarga una plantilla Excel de ejemplo para importar productos.
    """
    return {
        "message": "Template disponible en /static/templates/productos_template.xlsx",
        "columns": [
            {"name": "PRODUCTO", "required": True, "description": "Nombre del producto"},
            {"name": "CANTIDAD", "required": False, "description": "Stock disponible"},
            {"name": "PRECIO", "required": False, "description": "Precio de venta"},
            {"name": "CODIGO", "required": False, "description": "SKU/Código"},
            {"name": "CATEGORIA", "required": False, "description": "Categoría"},
        ],
        "example": {
            "PRODUCTO": "Pan integral",
            "CANTIDAD": 50,
            "PRECIO": 1.20,
            "CODIGO": "PAN-INT-001",
            "CATEGORIA": "PANADERIA",
        },
    }
