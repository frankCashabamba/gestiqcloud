from typing import List
from app.modules.imports.schemas import DocumentoProcesado
from app.modules.imports.extractores.utilidades import (
    buscar_multiple,
    es_concepto_valido,
)
from app.modules.imports.extractores.extractor_factura import extraer_factura
from app.modules.imports.extractores.extractor_recibo import extraer_recibo
from app.modules.imports.extractores.extractor_transferencia import (
    extraer_transferencias,
)


def extraer_desconocido(texto: str) -> List[DocumentoProcesado]:
    # Buscar fecha en múltiples formatos comunes
    fecha = buscar_multiple(
        [
            r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",  # 12/08/2025
            r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",  # 2025-08-12
            r"(?:\d{1,2})\s*(?:de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*\d{4}",
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"\b\d{2}[/-](ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[/-]\d{4}\b",  # español
            r"\b\d{2}[/-](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[/-]\d{4}\b",  # inglés
            r"Fecha\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
        ],
        texto,
    )

    # Buscar importe más alto (número con coma o punto)
    importe_str = (
        buscar_multiple(
            [
                r"-?[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"  # e.g., 1.234,56 or 1234.56
            ],
            texto,
        )
        or "0.00"
    )

    try:
        valor = float(importe_str.replace(",", "."))
        importe = valor if "." in importe_str or valor < 10000 else 0.0
    except Exception:
        importe = 0.0

    # Intentar extraer algún texto de concepto
    concepto_candidato = (
        buscar_multiple(
            [r"(?i)(?:(?:concepto|descripcion)[:\s-]*)?([A-Za-z0-9 ,.\-_/]{10,100})"],
            texto,
        )
        or texto[:100]
    )

    concepto = concepto_candidato.strip()
    if not es_concepto_valido(concepto):
        concepto = "Documento sin concepto"

    # Regla unificada: por defecto consideramos gasto si el importe es positivo
    tipo = "gasto" if importe >= 0 else "ingreso"
    return [
        DocumentoProcesado(
            fecha=fecha or "desconocida",
            concepto=concepto,
            tipo=tipo,
            importe=importe,
            cuenta="desconocida",
            categoria="otros",
            cliente="desconocido",
            invoice=None,
            documentoTipo="desconocido",
            origen="ocr",
        )
    ]


def extraer_por_tipos_combinados(texto: str) -> List[DocumentoProcesado]:
    extractores = [
        extraer_factura,
        extraer_recibo,
        extraer_transferencias,
    ]

    candidatos: List[DocumentoProcesado] = []

    for extractor in extractores:
        try:
            documentos = extractor(texto)
            if documentos:
                candidatos.extend(documentos)
        except Exception as e:
            print(f"❌ Error en extractor {extractor.__name__}: {e}")
            continue

    if not candidatos:
        return extraer_desconocido(texto)

    # ✅ Elegir el mejor documento según puntuación
    def puntuar(doc: DocumentoProcesado) -> int:
        score = 0
        if doc.importe and doc.importe > 0:
            score += 2
        if doc.fecha and doc.fecha != "desconocida":
            score += 1
        if doc.concepto and doc.concepto != "Documento sin concepto":
            score += 1
        if doc.cliente and doc.cliente != "desconocido":
            score += 1
        return score

    mejor = max(candidatos, key=puntuar)
    return [mejor]
