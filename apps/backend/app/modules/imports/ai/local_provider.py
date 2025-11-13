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
        logger.info("LocalAIProvider initialized " f"(cache: {settings.IMPORT_AI_CACHE_ENABLED})")

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
        Extract fields using regex patterns.

        Args:
            text: Document text
            doc_type: Document type (invoice, receipt, etc.)
            expected_fields: Field names to extract

        Returns:
            Dict with extracted values
        """
        extracted: dict[str, Any] = {}
        text_lower = text.lower()

        for field in expected_fields:
            pattern = self.FIELD_PATTERNS.get(field)
            if not pattern:
                continue

            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Get last group (usually the value)
                groups = match.groups()
                if groups:
                    extracted[field] = groups[-1]
                else:
                    extracted[field] = match.group(0)

        return extracted

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
