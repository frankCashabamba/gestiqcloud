import asyncio

from app.modules.imports.extractors.extractor_invoice import extract_invoice
from app.modules.imports.extractors.extractor_receipt import extract_receipt
from app.modules.imports.extractors.extractor_transfer import extract_transfers
from app.modules.imports.extractors.utilities import is_valid_concept, search_multiple
from app.modules.imports.schemas import DocumentoProcesado

try:
    from app.modules.imports.ai import get_ai_provider_singleton
except Exception:  # pragma: no cover
    get_ai_provider_singleton = None  # type: ignore


def extract_unknown(text: str) -> list[DocumentoProcesado]:
    # Search for date in multiple common formats
    date = search_multiple(
        [
            r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",  # 12/08/2025
            r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",  # 2025-08-12
            r"(?:\d{1,2})\s*(?:de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*\d{4}",
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"\b\d{2}[/-](ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[/-]\d{4}\b",  # Spanish
            r"\b\d{2}[/-](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[/-]\d{4}\b",  # English
            r"Fecha\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
        ],
        text,
    )

    # Search for highest amount (number with comma or dot)
    amount_str = (
        search_multiple(
            [r"-?[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"],  # e.g., 1.234,56 or 1234.56
            text,
        )
        or "0.00"
    )

    try:
        value = float(amount_str.replace(",", "."))
        amount = value if "." in amount_str or value < 10000 else 0.0
    except Exception:
        amount = 0.0

    # Try to extract some concept text
    concept_candidate = (
        search_multiple(
            [r"(?i)(?:(?:concepto|descripcion)[:\s-]*)?([A-Za-z0-9 ,.\-_/]{10,100})"],
            text,
        )
        or text[:100]
    )

    concept = concept_candidate.strip()
    if not is_valid_concept(concept):
        concept = "Document without concept"

    # Unified rule: by default we consider it an expense if the amount is positive
    document_type = "expense" if amount >= 0 else "income"
    return [
        DocumentoProcesado(
            fecha=date or "unknown",
            concepto=concept,
            tipo=document_type,
            importe=amount,
            cuenta="unknown",
            categoria="otros",
            cliente="unknown",
            invoice=None,
            documentoTipo="unknown",
            origen="ocr",
        )
    ]


def extract_by_combined_types(text: str) -> list[DocumentoProcesado]:
    extractors = [
        extract_invoice,
        extract_receipt,
        extract_transfers,
    ]

    candidates: list[DocumentoProcesado] = []

    for extractor in extractors:
        try:
            documents = extractor(text)
            if documents:
                candidates.extend(documents)
        except Exception as e:
            print(f"Error in extractor {extractor.__name__}: {e}")
            continue

    if not candidates:
        candidates = extract_unknown(text)

    if candidates:
        best = _pick_best(candidates)
        if _is_valid_document(best):
            return [best]

    # AI fallback: try to extract basic fields with LLM if configured
    doc_ai = _extract_with_ai(text)
    if doc_ai:
        return [doc_ai]

    return []


def _pick_best(documents: list[DocumentoProcesado]) -> DocumentoProcesado:
    def score_document(doc: DocumentoProcesado) -> int:
        score = 0
        if getattr(doc, "importe", 0) and doc.importe > 0:
            score += 2
        if getattr(doc, "fecha", "") and doc.fecha != "unknown":
            score += 1
        if getattr(doc, "concepto", "") and doc.concepto != "Document without concept":
            score += 1
        if getattr(doc, "cliente", "") and doc.cliente != "unknown":
            score += 1
        return score

    return max(documents, key=score_document)


def _is_valid_document(doc: DocumentoProcesado | dict) -> bool:
    try:
        date = getattr(doc, "fecha", None) or (doc.get("fecha") if isinstance(doc, dict) else None)
        amount = getattr(doc, "importe", None) or (
            doc.get("importe") if isinstance(doc, dict) else None
        )
        concept = getattr(doc, "concepto", None) or (
            doc.get("concepto") if isinstance(doc, dict) else None
        )
        if amount and float(amount) != 0:
            return True
        if date and date != "unknown":
            return True
        if concept and concept != "Document without concept":
            return True
    except Exception:
        pass
    return False


def _extract_with_ai(text: str) -> DocumentoProcesado | None:
    if not get_ai_provider_singleton:
        return None
    try:
        provider = asyncio.run(get_ai_provider_singleton())  # type: ignore
        expected_fields = ["fecha", "importe", "cliente", "concepto", "categoria", "tipo"]
        extracted = asyncio.run(provider.extract_fields(text[:4000], "unknown", expected_fields))
        if not extracted:
            return None
        doc_ai = DocumentoProcesado(
            fecha=extracted.get("fecha") or extracted.get("date") or "unknown",
            concepto=extracted.get("concepto")
            or extracted.get("concept")
            or "Document without concept",
            tipo=extracted.get("tipo") or "expense",
            importe=float(extracted.get("importe") or extracted.get("amount") or 0) or 0,
            cuenta=extracted.get("cuenta") or "unknown",
            categoria=extracted.get("categoria") or extracted.get("category") or "otros",
            cliente=extracted.get("cliente") or extracted.get("customer") or "unknown",
            invoice=extracted.get("invoice"),
            documentoTipo=extracted.get("documentoTipo") or "unknown",
            origen="ocr_ai",
        )
        if _is_valid_document(doc_ai):
            return doc_ai
    except Exception:
        return None
    return None
