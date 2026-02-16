"""
Endpoint POST /imports/uploads/analyze para análisis inteligente de archivos.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.core.access_guard import with_access_claims
from app.modules.imports.services.smart_router import AnalysisResult, smart_router

logger = logging.getLogger("app.imports.analyze")

router = APIRouter(
    prefix="/uploads",
    tags=["Imports Analyze"],
    dependencies=[Depends(with_access_claims)],
)


class AnalyzeResponse(BaseModel):
    """Respuesta del análisis de archivo."""

    suggested_parser: str
    suggested_doc_type: str
    confidence: float
    headers_sample: list[str]
    mapping_suggestion: dict[str, str] | None
    explanation: str
    decision_log: list[dict[str, Any]]
    requires_confirmation: bool
    available_parsers: list[str]
    probabilities: dict[str, float] | None
    ai_enhanced: bool
    ai_provider: str | None


def _get_claims(request: Request) -> dict[str, Any]:
    """Extract access claims from request."""
    access_claims = getattr(request.state, "access_claims", None)
    if not access_claims:
        raise HTTPException(status_code=401, detail="No access claims")
    return access_claims


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_upload(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Analiza un archivo para determinar el mejor parser y mapeo.

    Este endpoint unifica:
    - Detección de extensión/mime
    - Heurísticas del dispatcher
    - Clasificación por contenido
    - Mejora opcional con IA si la confianza es baja

    Retorna:
    - suggested_parser: Parser recomendado
    - suggested_doc_type: Tipo de documento detectado
    - confidence: Nivel de confianza (0-1)
    - headers_sample: Muestra de headers detectados
    - mapping_suggestion: Mapeo sugerido de headers a campos
    - explanation: Explicación de la decisión
    - decision_log: Trazabilidad de cada paso
    - requires_confirmation: True si el usuario debe confirmar
    - available_parsers: Lista de parsers disponibles
    - ai_enhanced: Si fue mejorado por IA
    - ai_provider: Proveedor de IA usado (si aplica)
    """
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")

    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    ext = file.filename.lower().split(".")[-1]
    allowed_extensions = [
        "xlsx",
        "xls",
        "xlsm",
        "xlsb",
        "csv",
        "xml",
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "tiff",
        "bmp",
        "gif",
        "heic",
        "heif",
    ]

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=422,
            detail=f"Extensión no soportada: {ext}. Permitidas: {', '.join(allowed_extensions)}",
        )

    try:
        contents = await file.read()
        tmp_path = None
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            result: AnalysisResult = await smart_router.analyze_file(
                file_path=tmp_path,
                filename=file.filename,
                content_type=file.content_type,
                tenant_id=tenant_id,
            )

            logger.info(
                f"File analyzed: filename={file.filename}, "
                f"parser={result.suggested_parser}, "
                f"doc_type={result.suggested_doc_type}, "
                f"confidence={result.confidence:.2f}, "
                f"ai_enhanced={result.ai_enhanced}, "
                f"tenant_id={tenant_id}"
            )

            return AnalyzeResponse(
                suggested_parser=result.suggested_parser,
                suggested_doc_type=result.suggested_doc_type,
                confidence=result.confidence,
                headers_sample=result.headers_sample,
                mapping_suggestion=result.mapping_suggestion,
                explanation=result.explanation,
                decision_log=result.decision_log,
                requires_confirmation=result.requires_confirmation,
                available_parsers=result.available_parsers,
                probabilities=result.probabilities,
                ai_enhanced=result.ai_enhanced,
                ai_provider=result.ai_provider,
            )

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    # En Windows el archivo puede seguir en uso brevemente; ignorar para evitar 500
                    pass

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error analyzing file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar archivo: {str(e)}",
        )
