"""
Vista Previa de Importación - Endpoints para análisis y preview antes de importar
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from io import BytesIO
import tempfile
import os

from app.config.database import get_db
from app.services.excel_analyzer import analyze_excel_stream
from app.modules.imports.parsers.products_excel import parse_products_excel, normalize_product_row
from app.modules.imports.validators.products import validate_product
from app.modules.imports.services.classifier import classifier
from pydantic import BaseModel

from app.core.access_guard import with_access_claims

router = APIRouter(
    prefix="/preview", 
    tags=["Imports Preview"], 
    dependencies=[Depends(with_access_claims)]
)

# Files router (for /imports/files endpoints)
files_router = APIRouter(
    prefix="/files",
    tags=["Imports Files"],
    dependencies=[Depends(with_access_claims)]
)


class PreviewResponse(BaseModel):
    """Respuesta de vista previa"""
    success: bool
    analysis: Dict[str, Any]
    preview_items: List[Dict[str, Any]]
    categories: List[str]
    stats: Dict[str, Any]
    suggestions: Dict[str, str]  # Mapeo sugerido


class ConfirmImportRequest(BaseModel):
    """Confirmación de importación con mapeo ajustado"""
    filename: str
    source_type: str = "productos"
    column_mapping: Dict[str, str]  # {"columna_excel": "campo_destino"}
    save_as_template: bool = False
    template_name: str = ""


def _get_claims(request: Request):
    """Extract access claims from request"""
    access_claims = getattr(request.state, "access_claims", None)
    if not access_claims:
        raise HTTPException(status_code=401, detail="No access claims")
    return access_claims


@router.post("/analyze-excel", response_model=PreviewResponse)
async def analyze_excel_for_preview(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Analiza un archivo Excel y devuelve:
    - Headers detectados
    - Mapeo sugerido
    - Vista previa de primeras 10 filas
    - Estadísticas
    - Categorías detectadas (para productos)
    """
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Falta tenant_id")
    
    # Validar tipo de archivo
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=422, detail="Solo se aceptan archivos Excel (.xlsx, .xls)")
    
    try:
        # Leer contenido
        contents = await file.read()
        
        # Análisis con excel_analyzer
        with BytesIO(contents) as stream:
            analysis = analyze_excel_stream(stream)
        
        # Parser especializado para productos
        preview_items = []
        categories = []
        
        if file.filename:
            # Guardar temporalmente para parser openpyxl
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            
            try:
                # Parse con detección de categorías
                result = parse_products_excel(tmp_path)
                
                # Tomar primeras 10 filas para preview
                preview_items = result["products"][:10]
                categories = result["categories"]
                
                # Normalizar y validar cada item de preview
                for item in preview_items:
                    normalized = normalize_product_row(item)
                    errors = validate_product(normalized)
                    item["_validation"] = {
                        "valid": len(errors) == 0,
                        "errors": errors
                    }
                    item["_normalized"] = normalized
                
                stats = result["stats"]
                
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        return PreviewResponse(
            success=True,
            analysis=analysis,
            preview_items=preview_items,
            categories=categories,
            stats=stats,
            suggestions=analysis.get("suggested_mapping", {})
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar Excel: {str(e)}"
        )


@router.post("/validate-mapping")
async def validate_column_mapping(
    request: Request,
    mapping: Dict[str, str],
    sample_row: Dict[str, Any],
):
    """
    Valida un mapeo de columnas contra una fila de muestra
    Devuelve errores de validación si los hay
    """
    claims = _get_claims(request)
    
    # Aplicar mapeo a la fila de muestra
    mapped_row = {}
    for excel_col, dest_field in mapping.items():
        if dest_field != "ignore" and excel_col in sample_row:
            mapped_row[dest_field] = sample_row[excel_col]
    
    # Validar como producto
    errors = validate_product(mapped_row)
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "mapped_row": mapped_row
    }


@router.get("/templates")
async def list_import_templates(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Lista templates de importación guardados para el tenant
    """
    from app.models.core.modelsimport import ImportMapping
    
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    
    templates = (
        db.query(ImportMapping)
        .filter(ImportMapping.tenant_id == tenant_id)
        .order_by(ImportMapping.created_at.desc())
        .all()
    )
    
    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "source_type": t.source_type,
                "mappings": t.mappings,
                "created_at": t.created_at.isoformat()
            }
            for t in templates
        ]
    }


@router.post("/save-template")
async def save_import_template(
    request: Request,
    name: str,
    source_type: str,
    mappings: Dict[str, str],
    db: Session = Depends(get_db),
):
    """
    Guarda un template de mapeo para reutilizar
    """
    from app.models.core.modelsimport import ImportMapping
    
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")
    
    template = ImportMapping(
        tenant_id=tenant_id,
        name=name,
        source_type=source_type,
        mappings=mappings,
        version=1
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "success": True,
        "template_id": str(template.id),
        "message": f"Template '{name}' guardado correctamente"
    }


class ClassifyResponse(BaseModel):
    """Respuesta de clasificación de archivo"""
    suggested_parser: Optional[str]
    confidence: float
    reason: str
    available_parsers: list[str]
    content_analysis: Optional[Dict[str, Any]] = None
    probabilities: Optional[Dict[str, float]] = None
    enhanced_by_ai: Optional[bool] = False
    ai_provider: Optional[str] = None


@files_router.post("/classify", response_model=ClassifyResponse)
async def classify_file(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Clasifica un archivo para sugerir el parser apropiado.

    Usa análisis básico de contenido para determinar si es productos, banco, etc.
    En el futuro se integrará IA local/pago.
    """
    claims = _get_claims(request)

    # Validar tipo básico de archivo
    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    ext = file.filename.lower().split('.')[-1]
    if ext not in ['xlsx', 'xls', 'csv', 'xml']:
        raise HTTPException(status_code=422, detail="Solo se aceptan archivos Excel, CSV o XML")

    try:
        # Guardar temporalmente para análisis
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Clasificar archivo
            result = classifier.classify_file(tmp_path, file.filename)

            return ClassifyResponse(**result)

        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al clasificar archivo: {str(e)}"
        )


@files_router.post("/classify-with-ai", response_model=ClassifyResponse)
async def classify_file_with_ai(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Clasifica un archivo con enhancers de IA (Fase D).
    
    Primero usa análisis heurístico, luego optionally mejora con IA si la confianza es baja.
    Compatible con:
    - Local Ollama
    - OpenAI (API key en settings)
    - Azure OpenAI
    
    Retorna:
    - suggested_parser: Nombre del parser recomendado
    - confidence: Confianza (0-1)
    - probabilities: Scores por cada parser disponible
    - enhanced_by_ai: Si fue mejorado por IA
    - ai_provider: Proveedor de IA usado (si aplica)
    """
    claims = _get_claims(request)

    # Validar tipo básico de archivo
    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    ext = file.filename.lower().split('.')[-1]
    if ext not in ['xlsx', 'xls', 'csv', 'xml']:
        raise HTTPException(status_code=422, detail="Solo se aceptan archivos Excel, CSV o XML")

    try:
        # Guardar temporalmente para análisis
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Clasificar con IA
            result = await classifier.classify_file_with_ai(tmp_path, file.filename)

            return ClassifyResponse(**result)

        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al clasificar archivo con IA: {str(e)}"
        )
