"""
Vista Previa de Importación - Endpoints para análisis y preview antes de importar
"""

import os
import tempfile
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.modules.imports.parsers.products_excel import normalize_product_row, parse_products_excel
from app.modules.imports.services.classifier import classifier
from app.modules.imports.services.smart_router import smart_router
from app.modules.imports.validators.products import validate_product
from app.services.excel_analyzer import analyze_excel_stream

router = APIRouter(
    prefix="/preview", tags=["Imports Preview"], dependencies=[Depends(with_access_claims)]
)

# Files router (for /imports/files endpoints)
files_router = APIRouter(
    prefix="/files", tags=["Imports Files"], dependencies=[Depends(with_access_claims)]
)


class PreviewResponse(BaseModel):
    """Respuesta de vista previa"""

    success: bool
    analysis: dict[str, Any]
    preview_items: list[dict[str, Any]]
    categories: list[str]
    stats: dict[str, Any]
    suggestions: dict[str, str]  # Mapeo sugerido


class ConfirmImportRequest(BaseModel):
    """Confirmación de importación con mapeo ajustado"""

    filename: str
    source_type: str = "productos"
    column_mapping: dict[str, str]  # {"columna_excel": "campo_destino"}
    save_as_template: bool = False
    template_name: str = ""


class SaveTemplateRequest(BaseModel):
    """JSON payload for saving import templates."""

    name: str
    source_type: str
    mappings: dict[str, str]


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
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
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
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
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
                    item["_validation"] = {"valid": len(errors) == 0, "errors": errors}
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
            suggestions=analysis.get("suggested_mapping", {}),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar Excel: {str(e)}")


@router.post("/validate-mapping")
async def validate_column_mapping(
    request: Request,
    mapping: dict[str, str],
    sample_row: dict[str, Any],
):
    """
    Valida un mapeo de columnas contra una fila de muestra
    Devuelve errores de validación si los hay
    """
    _get_claims(request)

    # Aplicar mapeo a la fila de muestra
    mapped_row = {}
    for excel_col, dest_field in mapping.items():
        if dest_field != "ignore" and excel_col in sample_row:
            mapped_row[dest_field] = sample_row[excel_col]

    # Validar como producto
    errors = validate_product(mapped_row)

    return {"valid": len(errors) == 0, "errors": errors, "mapped_row": mapped_row}


@router.get("/templates")
async def list_import_templates(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Lista templates de importación guardados para el tenant
    """
    from app.models.imports import ImportColumnMapping

    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")

    templates = (
        db.query(ImportColumnMapping)
        .filter(ImportColumnMapping.tenant_id == tenant_id, ImportColumnMapping.is_active)  # noqa: E712
        .order_by(ImportColumnMapping.created_at.desc())
        .all()
    )

    return {
        "templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "source_type": "generic",
                "mappings": t.mapping or {},
                "created_at": t.created_at.isoformat(),
            }
            for t in templates
        ]
    }


@router.post("/save-template")
async def save_import_template(
    request: Request,
    payload: SaveTemplateRequest | None = Body(default=None),
    name: str | None = None,
    source_type: str | None = None,
    mappings: dict[str, str] | None = None,
    db: Session = Depends(get_db),
):
    """
    Guarda un template de mapeo para reutilizar
    """
    from uuid import uuid4

    from app.models.imports import ImportColumnMapping

    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")

    # Prefer JSON payload; keep query/body params for backward compatibility.
    if payload is not None:
        name = payload.name
        source_type = payload.source_type
        mappings = payload.mappings

    if not name or not source_type or not isinstance(mappings, dict):
        raise HTTPException(status_code=422, detail="name, source_type y mappings son requeridos")

    template = ImportColumnMapping(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        description=f"compat:/preview/save-template source_type={source_type}",
        mapping=mappings,
        transforms={},
        defaults={},
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        "success": True,
        "template_id": str(template.id),
        "message": f"Template '{name}' guardado correctamente",
    }


class ClassifyResponse(BaseModel):
    """Respuesta de clasificación de archivo"""

    suggested_parser: str | None
    confidence: float
    reason: str
    available_parsers: list[str]
    content_analysis: dict[str, Any] | None = None
    probabilities: dict[str, float] | None = None
    enhanced_by_ai: bool | None = False
    ai_provider: str | None = None


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
    _get_claims(request)

    # Validar tipo básico de archivo
    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    ext = file.filename.lower().split(".")[-1]
    allowed = ["xlsx", "xls", "csv", "xml", "pdf", "png", "jpg", "jpeg", "heic"]
    use_ocr_router = ext in {"pdf", "png", "jpg", "jpeg", "heic"}
    if ext not in allowed:
        raise HTTPException(status_code=422, detail="Extensión no soportada")

    try:
        # Guardar temporalmente para análisis
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            if use_ocr_router:
                # Para PDF/imagen, usar smart_router (incluye OCR) para sugerir parser/doc_type
                claims = _get_claims(request)
                tenant_id = claims.get("tenant_id")
                result = await smart_router.analyze_file(
                    file_path=tmp_path,
                    filename=file.filename,
                    content_type=file.content_type,
                    tenant_id=tenant_id,
                )
                return ClassifyResponse(
                    suggested_parser=result.suggested_parser,
                    confidence=result.confidence,
                    reason=result.explanation,
                    available_parsers=result.available_parsers,
                    content_analysis={"doc_type": result.suggested_doc_type},
                    probabilities=result.probabilities,
                    enhanced_by_ai=result.ai_enhanced,
                    ai_provider=result.ai_provider,
                )

            # Clasificar archivo estructurado (Excel/CSV/XML)
            result = classifier.classify_file(tmp_path, file.filename)
            return ClassifyResponse(**result)

        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al clasificar archivo: {str(e)}")


@files_router.post("/classify-with-ai", response_model=ClassifyResponse)
async def classify_file_with_ai(
    request: Request,
    file: UploadFile = File(...),
    provider: str | None = Query(None, description="Override AI provider"),
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
    _get_claims(request)

    # Validar tipo básico de archivo
    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    ext = file.filename.lower().split(".")[-1]
    allowed = ["xlsx", "xls", "csv", "xml", "pdf", "png", "jpg", "jpeg", "heic"]
    use_ocr_router = ext in {"pdf", "png", "jpg", "jpeg", "heic"}
    if ext not in allowed:
        raise HTTPException(status_code=422, detail="Extensión no soportada")

    try:
        # Guardar temporalmente para análisis
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            if use_ocr_router:
                claims = _get_claims(request)
                tenant_id = claims.get("tenant_id")
                result = await smart_router.analyze_file(
                    file_path=tmp_path,
                    filename=file.filename,
                    content_type=file.content_type,
                    tenant_id=tenant_id,
                )
                return ClassifyResponse(
                    suggested_parser=result.suggested_parser,
                    confidence=result.confidence,
                    reason=result.explanation,
                    available_parsers=result.available_parsers,
                    content_analysis={"doc_type": result.suggested_doc_type},
                    probabilities=result.probabilities,
                    enhanced_by_ai=result.ai_enhanced,
                    ai_provider=result.ai_provider,
                )

            # Clasificar con IA (estructurado)
            result = await classifier.classify_file_with_ai(
                tmp_path,
                file.filename,
                provider_name=provider,
            )

            return ClassifyResponse(**result)

        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al clasificar archivo con IA: {str(e)}")
