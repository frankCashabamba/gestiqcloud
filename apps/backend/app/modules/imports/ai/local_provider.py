"""Local AI provider using pattern matching and heuristics."""

import logging
import re
from typing import Any

from app.config.settings import settings

from .base import AIProvider, ClassificationResult
from .cache import ClassificationCache

logger = logging.getLogger("imports.ai.local")


class LocalAIProvider(AIProvider):
    """
    Local AI provider using pattern matching and regex heuristics.
    No external API calls, fully local and free.
    """

    # Document type patterns
    DOC_PATTERNS = {
        "invoice": [
            r"invoice|factura|número de factura|invoice number",
            r"total|amount|monto|total amount",
            r"customer|cliente|buyer|bill to",
            r"tax|iva|impuesto|taxes",
            r"due date|vencimiento",
        ],
        "expense_receipt": [
            r"receipt|recibo|comprobante",
            r"expense|gasto|purchase",
            r"date|fecha",
            r"amount|monto|total",
            r"category|categoría",
        ],
        "bank_tx": [
            r"transaction|transacción|transfer|transferencia",
            r"debit|credit|débito|crédito",
            r"account|cuenta|account number",
            r"statement|extracto|bank statement",
            r"balance|saldo",
        ],
        "product": [
            r"product|producto|item|name",
            r"price|precio|cost|valor",
            r"quantity|cantidad|qty|stock",
            r"description|descripción|details",
            r"sku|code|código",
        ],
    }

    # Field extraction patterns
    FIELD_PATTERNS = {
        "total": r"total[:\s]+[\$\s]*([0-9]+[.,][0-9]{2})",
        "tax": r"(tax|iva|impuesto)[:\s]+[\$\s]*([0-9]+[.,][0-9]{2})",
        "date": r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        "invoice_number": r"(invoice|factura)[:\s]*([A-Z0-9\-]+)",
        "amount": r"amount[:\s]+[\$\s]*([0-9]+[.,][0-9]{2})",
    }

    def __init__(self):
        """Initialize local provider."""
        self.cache = (
            ClassificationCache(ttl_seconds=settings.IMPORT_AI_CACHE_TTL)
            if settings.IMPORT_AI_CACHE_ENABLED
            else None
        )
        self.request_count = 0
        self.cache_hits = 0
        logger.info(f"LocalAIProvider initialized (cache: {settings.IMPORT_AI_CACHE_ENABLED})")

    async def classify_document(
        self,
        text: str,
        available_parsers: list[str],
        doc_metadata: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Classify document using pattern matching.

        Strategy:
        1. Check cache if enabled
        2. Score based on keyword patterns
        3. Return best match with confidence
        """
        self.request_count += 1

        # Try cache
        if self.cache:
            cached = self.cache.get(text, available_parsers)
            if cached:
                self.cache_hits += 1
                return ClassificationResult(**cached)

        # Normalize text
        text_lower = text.lower()

        # Score each parser
        scores: dict[str, float] = {}
        pattern_matches: dict[str, list[str]] = {}

        for parser in available_parsers:
            doc_type = self._parser_to_doctype(parser)
            patterns = self.DOC_PATTERNS.get(doc_type, [])

            matches = []
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matches.append(pattern[:20] + "...")

            # Confidence = (matched patterns / total patterns)
            if patterns:
                confidence = len(matches) / len(patterns)
            else:
                confidence = 0.0

            scores[parser] = confidence
            pattern_matches[parser] = matches

        # Select best match
        best_parser = max(scores, key=scores.get)
        confidence = min(scores[best_parser], 1.0)

        # Prepare result
        result = ClassificationResult(
            suggested_parser=best_parser,
            confidence=confidence,
            probabilities={p: round(s, 3) for p, s in scores.items()},
            reasoning=(
                f"Pattern matching ({len(pattern_matches[best_parser])} "
                f"matches). Best: {best_parser} ({confidence:.0%})"
            ),
            provider="local",
            enhanced_by_ai=False,
        )

        # Cache result
        if self.cache:
            self.cache.set(text, available_parsers, result.__dict__)

        return result

    async def extract_fields(
        self,
        text: str,
        doc_type: str,
        expected_fields: list[str],
    ) -> dict[str, Any]:
        """
        Extract fields using local heuristics (regex + simples reglas).

        Nota: esto es offline, sin coste, y sirve para rellenar campos mínimos
        (fecha, importe, concepto, cliente, categoría) para evitar ERROR_VALIDATION.
        """
        extracted: dict[str, Any] = {}
        text_norm = text[:6000]  # limitar ruido
        text_lower = text_norm.lower()

        # Fecha: varios formatos comunes
        date_patterns = [
            r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",  # 12/08/2025
            r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",  # 2025-08-12
            r"(?:\d{1,2})\s*(?:de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*\d{4}",
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        ]
        for pat in date_patterns:
            m = re.search(pat, text_norm, re.IGNORECASE)
            if m:
                extracted["fecha"] = m.group(0)
                break

        # Importe: tomar el número con mayor valor absoluto con dos decimales
        amount_pattern = r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"
        candidates = re.findall(amount_pattern, text_norm)
        if candidates:
            try:
                # normalizar a float y escoger el máximo absoluto
                parsed = [
                    (c, float(c.replace(".", "").replace(",", ".") if c.count(",") == 1 else c.replace(",", "")))
                    for c in candidates
                ]
                best = max(parsed, key=lambda x: abs(x[1]))
                extracted["importe"] = best[1]
            except Exception:
                pass

        # Concepto: línea con "concepto"/"description"/"detalle" o primer texto largo
        concept_match = re.search(
            r"(?i)(concepto|descripcion|description|detalle)[:\-]?\s*(.+)", text_norm.splitlines().__str__()
        )
        if concept_match and concept_match.group(2):
            extracted["concepto"] = concept_match.group(2)[:120].strip()
        else:
            # fallback: primera línea con letras y algo de longitud
            for line in text_norm.splitlines():
                l = line.strip()
                if len(l) > 8 and re.search(r"[A-Za-z]", l):
                    extracted["concepto"] = l[:120]
                    break

        # Cliente: email o línea tras "bill to"/"cliente"
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text_norm)
        if email_match:
            extracted["cliente"] = email_match.group(0)
        else:
            client_match = re.search(r"(?i)(bill to|cliente)[:\-]?\s*(.+)", text_norm)
            if client_match and client_match.group(2):
                extracted["cliente"] = client_match.group(2).splitlines()[0][:120].strip()

        # Categoría tentativa según doc_type
        if doc_type in ("invoice", "expense_receipt", "desconocido"):
            extracted.setdefault("categoria", "gastos")
            extracted.setdefault("tipo", "expense")
        elif doc_type in ("bank_tx",):
            extracted.setdefault("categoria", "banco")
            extracted.setdefault("tipo", "transferencia")

        # Filtrar solo los campos solicitados
        return {k: v for k, v in extracted.items() if k in expected_fields or not expected_fields}

    def get_telemetry(self) -> dict[str, Any]:
        """Get telemetry metrics."""
        cache_stats = self.cache.get_stats() if self.cache else None

        return {
            "provider": "local",
            "model": "pattern_matching",
            "requests": self.request_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                self.cache_hits / self.request_count if self.request_count > 0 else 0.0
            ),
            "cost_per_request": 0.0,
            "latency_ms": "10-50",
            "cache": cache_stats,
        }

    @staticmethod
    def _parser_to_doctype(parser: str) -> str:
        """Map parser ID to document type."""
        mapping = {
            "csv_invoices": "invoice",
            "csv_products": "product",
            "csv_expenses": "expense_receipt",
            "csv_bank": "bank_tx",
            "xml_invoice": "invoice",
            "xml_products": "product",
            "xml_bank": "bank_tx",
            "xlsx_invoice": "invoice",
            "xlsx_products": "product",
            "xlsx_expenses": "expense_receipt",
            "pdf_qr": "expense_receipt",
            "products_excel": "product",
            "xml_camt053_bank": "bank_tx",
        }
        return mapping.get(parser, "invoice")
