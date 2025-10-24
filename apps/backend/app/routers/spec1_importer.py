"""
Router: Excel Importer SPEC-1 - Importación de archivos tipo 22-10-20251.xlsx
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date
from typing import Optional
import logging
import tempfile
import os

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant
from app.services.excel_importer_spec1 import ExcelImporterSPEC1

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/imports/spec1", tags=["imports-spec1"])


@router.post("/excel")
async def import_excel_spec1(
    file: UploadFile = File(...),
    fecha_manual: Optional[str] = Form(None),
    simulate_sales: bool = Form(True),
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(ensure_tenant),
):
    """
    Importar archivo Excel según SPEC-1
    
    - Hoja REGISTRO → daily_inventory + ventas simuladas
    - Extrae fecha del nombre o usa fecha_manual
    - Crea productos automáticamente si no existen
    - Idempotente (puede reimportarse)
    """
    # Validar extensión
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos Excel (.xlsx, .xls)",
        )
    
    # Parsear fecha manual si se proporciona
    fecha_obj = None
    if fecha_manual:
        try:
            fecha_obj = date.fromisoformat(fecha_manual)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Fecha inválida: {fecha_manual}. Use formato YYYY-MM-DD",
            )
    
    # Guardar archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        # Ejecutar importación
        importer = ExcelImporterSPEC1(db, tenant_id)
        stats = importer.import_file(
            file_path=tmp_path,
            fecha_manual=fecha_obj,
            simulate_sales=simulate_sales,
        )
        
        logger.info(f"Importación completada: {stats}")
        
        return {
            "success": len(stats["errors"]) == 0,
            "filename": file.filename,
            "stats": stats,
        }
    
    except Exception as e:
        logger.error(f"Error en importación: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al importar: {str(e)}",
        )
    
    finally:
        # Limpiar archivo temporal
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/template")
def get_template_info():
    """Información del formato esperado del Excel"""
    return {
        "template": "SPEC-1 Excel Template",
        "filename_format": "dd-mm-aaaa.xlsx (ej: 22-10-2025.xlsx)",
        "sheets": {
            "REGISTRO": {
                "required": True,
                "columns": [
                    "PRODUCTO",
                    "CANTIDAD (stock inicial)",
                    "VENTA DIARIA",
                    "SOBRANTE DIARIO (stock final)",
                    "PRECIO UNITARIO VENTA",
                    "TOTAL (opcional, se recalcula)",
                ],
            },
            "compras": {
                "required": False,
                "status": "Pendiente de implementación",
            },
            "LECHE": {
                "required": False,
                "status": "Pendiente de implementación",
            },
        },
        "features": [
            "Extrae fecha del nombre del archivo",
            "Crea productos automáticamente con prefijo [IMP]",
            "Simula ventas para alimentar POS/Reportes",
            "Idempotente (puede reimportarse)",
            "Genera daily_inventory por producto/fecha",
        ],
    }
