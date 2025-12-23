import asyncio
from app.modules.imports.extractores.extractor_factura import extraer_factura
from app.modules.imports.extractores.extractor_recibo import extraer_recibo
from app.modules.imports.extractores.extractor_transferencia import extraer_transferencias
from app.modules.imports.extractores.utilidades import buscar_multiple, es_concepto_valido
from app.modules.imports.schemas import DocumentoProcesado

try:
    from app.modules.imports.ai import get_ai_provider_singleton
except Exception:  # pragma: no cover
    get_ai_provider_singleton = None  # type: ignore


def extraer_desconocido(texto: str) -> list[DocumentoProcesado]:
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
            [r"-?[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"],  # e.g., 1.234,56 or 1234.56
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


def extraer_por_tipos_combinados(texto: str) -> list[DocumentoProcesado]:
    extractores = [
        extraer_factura,
        extraer_recibo,
        extraer_transferencias,
    ]

    candidatos: list[DocumentoProcesado] = []

    for extractor in extractores:
        try:
            documentos = extractor(texto)
            if documentos:
                candidatos.extend(documentos)
        except Exception as e:
            print(f"❌ Error en extractor {extractor.__name__}: {e}")
            continue

    if not candidatos:
        candidatos = extraer_desconocido(texto)

    if candidatos:
        mejor = _pick_best(candidatos)
        if _es_documento_valido(mejor):
            return [mejor]

    # Fallback IA: intenta extraer campos básicos con LLM si está configurado
    doc_ai = _extraer_con_ia(texto)
    if doc_ai:
        return [doc_ai]

    return []


def _pick_best(documentos: list[DocumentoProcesado]) -> DocumentoProcesado:
    def puntuar(doc: DocumentoProcesado) -> int:
        score = 0
        if getattr(doc, "importe", 0) and doc.importe > 0:
            score += 2
        if getattr(doc, "fecha", "") and doc.fecha != "desconocida":
            score += 1
        if getattr(doc, "concepto", "") and doc.concepto != "Documento sin concepto":
            score += 1
        if getattr(doc, "cliente", "") and doc.cliente != "desconocido":
            score += 1
        return score

    return max(documentos, key=puntuar)


def _es_documento_valido(doc: DocumentoProcesado | dict) -> bool:
    try:
        fecha = getattr(doc, "fecha", None) or (doc.get("fecha") if isinstance(doc, dict) else None)
        importe = getattr(doc, "importe", None) or (doc.get("importe") if isinstance(doc, dict) else None)
        concepto = getattr(doc, "concepto", None) or (doc.get("concepto") if isinstance(doc, dict) else None)
        if importe and float(importe) != 0:
            return True
        if fecha and fecha != "desconocida":
            return True
        if concepto and concepto != "Documento sin concepto":
            return True
    except Exception:
        pass
    return False


def _extraer_con_ia(texto: str) -> DocumentoProcesado | None:
    if not get_ai_provider_singleton:
        return None
    try:
        provider = asyncio.run(get_ai_provider_singleton())  # type: ignore
        expected_fields = ["fecha", "importe", "cliente", "concepto", "categoria", "tipo"]
        extracted = asyncio.run(provider.extract_fields(texto[:4000], "desconocido", expected_fields))
        if not extracted:
            return None
        doc_ai = DocumentoProcesado(
            fecha=extracted.get("fecha") or extracted.get("date") or "desconocida",
            concepto=extracted.get("concepto") or extracted.get("concept") or "Documento sin concepto",
            tipo=extracted.get("tipo") or "gasto",
            importe=float(extracted.get("importe") or extracted.get("amount") or 0) or 0,
            cuenta=extracted.get("cuenta") or "desconocida",
            categoria=extracted.get("categoria") or extracted.get("category") or "otros",
            cliente=extracted.get("cliente") or extracted.get("customer") or "desconocido",
            invoice=extracted.get("invoice"),
            documentoTipo=extracted.get("documentoTipo") or "desconocido",
            origen="ocr_ai",
        )
        if _es_documento_valido(doc_ai):
            return doc_ai
    except Exception:
        return None
    return None
