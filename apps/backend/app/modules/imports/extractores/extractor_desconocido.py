import asyncio

from app.modules.imports.extractores.extractor_factura import extract_invoice
from app.modules.imports.extractores.extractor_recibo import extract_receipt
from app.modules.imports.extractores.extractor_transferencia import extract_transfers
from app.modules.imports.extractores.utilidades import is_valid_concept, search_multiple
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

    def _canonical_to_docproc(c: dict) -> DocumentoProcesado | None:
        doc_type = (c.get("doc_type") or "").strip()
        totals = c.get("totals") or {}
        lines = c.get("lines") or []
        first_line = lines[0] if isinstance(lines, list) and lines else {}
        vendor = c.get("vendor") or {}
        buyer = c.get("buyer") or {}
        routing = c.get("routing_proposal") or {}

        issue_date = (
            c.get("issue_date")
            or c.get("invoice_date")
            or c.get("expense_date")
            or c.get("value_date")
        )
        total = None
        if isinstance(totals, dict):
            total = totals.get("total")
        if total is None:
            total = c.get("total") or c.get("amount")
        if total is None and isinstance(first_line, dict):
            total = first_line.get("total") or first_line.get("unit_price")

        concept = None
        if isinstance(first_line, dict):
            concept = first_line.get("desc")
        concept = concept or c.get("description") or c.get("concept") or "Document without concept"

        client = None
        if isinstance(vendor, dict):
            client = vendor.get("name")
        if not client and isinstance(buyer, dict):
            client = buyer.get("name")

        category = routing.get("category_code") if isinstance(routing, dict) else None
        account = routing.get("account") if isinstance(routing, dict) else None
        invoice_no = c.get("invoice_number") or c.get("invoice")

        try:
            amount = float(total) if total is not None else 0.0
        except Exception:
            amount = 0.0

        return DocumentoProcesado(
            fecha=str(issue_date) if issue_date is not None else "unknown",
            concepto=str(concept) if concept is not None else "Document without concept",
            tipo="expense",
            importe=amount,
            cuenta=str(account) if account is not None else "unknown",
            categoria=str(category) if category is not None else "otros",
            cliente=str(client) if client is not None else "unknown",
            invoice=str(invoice_no) if invoice_no is not None else None,
            documentoTipo=doc_type or "unknown",
            origen=str(c.get("source") or "ocr"),
        )

    candidates: list[DocumentoProcesado] = []

    for extractor in extractors:
        try:
            documents = extractor(text)
            if documents:
                for d in documents:
                    if isinstance(d, dict) and ("doc_type" in d or "totals" in d or "lines" in d):
                        dp = _canonical_to_docproc(d)
                        if dp is not None:
                            candidates.append(dp)
                    elif isinstance(d, DocumentoProcesado):
                        candidates.append(d)
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
