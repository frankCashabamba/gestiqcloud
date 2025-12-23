"""
Endpoint POST /imports/ocr/extract para extracción OCR de documentos.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.core.access_guard import with_access_claims
from app.modules.imports.services.ocr_service import ocr_service
from app.modules.imports.extractores.ocr_extractor import ocr_extractor

logger = logging.getLogger("app.imports.ocr")

router = APIRouter(
    prefix="/ocr",
    tags=["Imports OCR"],
    dependencies=[Depends(with_access_claims)],
)


class OCRExtractResponse(BaseModel):
    """Respuesta de extracción OCR."""

    text: str
    pages: int
    layout: str
    confidence: float
    tables: list[list[list[str]]]
    processing_time_ms: float
    metadata: dict[str, Any]


class OCRExtractAndParseResponse(BaseModel):
    """Respuesta de extracción OCR con parsing."""

    text: str
    pages: int
    layout: str
    ocr_confidence: float
    doc_type: str
    extracted_data: dict[str, Any]
    extraction_confidence: float
    processing_time_ms: float


def _get_claims(request: Request) -> dict[str, Any]:
    """Extract access claims from request."""
    access_claims = getattr(request.state, "access_claims", None)
    if not access_claims:
        raise HTTPException(status_code=401, detail="No access claims")
    return access_claims


@router.post("/extract", response_model=OCRExtractResponse)
async def ocr_extract(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Extrae texto de un archivo PDF o imagen usando OCR.

    Soporta:
    - PDF (texto embebido o escaneado)
    - Imágenes (PNG, JPG, JPEG, TIFF, BMP)

    Retorna:
    - text: Texto extraído completo
    - pages: Número de páginas procesadas
    - layout: Tipo de documento detectado (invoice, receipt, bank_statement, table, unknown)
    - confidence: Confianza del OCR (0-1)
    - tables: Tablas detectadas (si las hay)
    - processing_time_ms: Tiempo de procesamiento
    """
    _get_claims(request)

    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    if not ocr_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. Check PyMuPDF and Tesseract installation.",
        )

    ext = file.filename.lower().split(".")[-1]
    allowed_extensions = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "gif"]

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=422,
            detail=f"Extensión no soportada: {ext}. Permitidas: {', '.join(allowed_extensions)}",
        )

    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            result = await ocr_service.extract_text(tmp_path)

            logger.info(
                f"OCR extraction complete: filename={file.filename}, "
                f"pages={result.pages}, layout={result.layout.value}, "
                f"confidence={result.confidence:.2f}, "
                f"time_ms={result.processing_time_ms:.1f}"
            )

            return OCRExtractResponse(
                text=result.text,
                pages=result.pages,
                layout=result.layout.value,
                confidence=result.confidence,
                tables=result.tables,
                processing_time_ms=result.processing_time_ms,
                metadata=result.metadata,
            )

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"OCR runtime error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Error in OCR extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar archivo: {str(e)}",
        )


@router.post("/extract-and-parse", response_model=OCRExtractAndParseResponse)
async def ocr_extract_and_parse(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Extrae texto de un archivo y aplica parsing heurístico según el layout.

    Combina:
    1. Extracción OCR (PyMuPDF + Tesseract)
    2. Detección de layout
    3. Extracción de campos según tipo de documento

    Para facturas extrae: invoice_number, date, vendor, total, tax, etc.
    Para recibos extrae: date, total, items, payment_method
    Para extractos bancarios: transactions, balances, account_number
    """
    _get_claims(request)

    if not file.filename:
        raise HTTPException(status_code=422, detail="Nombre de archivo requerido")

    if not ocr_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. Check PyMuPDF and Tesseract installation.",
        )

    ext = file.filename.lower().split(".")[-1]
    allowed_extensions = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "gif"]

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=422,
            detail=f"Extensión no soportada: {ext}. Permitidas: {', '.join(allowed_extensions)}",
        )

    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            ocr_result = await ocr_service.extract_text(tmp_path)

            extracted = ocr_extractor.extract(ocr_result)

            logger.info(
                f"OCR extract+parse complete: filename={file.filename}, "
                f"layout={ocr_result.layout.value}, doc_type={extracted['doc_type']}, "
                f"confidence={extracted['confidence']:.2f}"
            )

            return OCRExtractAndParseResponse(
                text=ocr_result.text[:10000],
                pages=ocr_result.pages,
                layout=ocr_result.layout.value,
                ocr_confidence=ocr_result.confidence,
                doc_type=extracted["doc_type"],
                extracted_data=extracted["data"],
                extraction_confidence=extracted["confidence"],
                processing_time_ms=ocr_result.processing_time_ms,
            )

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error(f"OCR runtime error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Error in OCR extract+parse: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar archivo: {str(e)}",
        )


@router.get("/status")
async def ocr_status():
    """
    Retorna el estado del servicio OCR.

    Útil para verificar si las dependencias están instaladas.
    """
    return {
        "available": ocr_service.is_available(),
        "pymupdf_available": ocr_service._fitz_available,
        "tesseract_available": ocr_service._tesseract_available,
        "supported_extensions": list(ocr_service.SUPPORTED_EXTENSIONS),
    }
