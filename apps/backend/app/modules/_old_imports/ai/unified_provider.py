"""Imports AI provider backed by app.services.ai unified provider stack."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.ai.base import AITask
from app.services.ai.service import AIService

from .base import AIProvider, ClassificationResult

logger = logging.getLogger("imports.ai.unified")


class UnifiedServiceAIProvider(AIProvider):
    """Adapter that delegates imports classification to AIService providers."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.request_count = 0
        self.error_count = 0

    async def classify_document(
        self,
        text: str,
        available_parsers: list[str],
        doc_metadata: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        self.request_count += 1
        if not available_parsers:
            return ClassificationResult(
                suggested_parser="",
                confidence=0.0,
                probabilities={},
                reasoning="No parsers provided",
                provider=self.provider_name,
                enhanced_by_ai=False,
            )

        prompt = (
            "Classify this document and choose the best parser.\n\n"
            f"Available parsers: {available_parsers}\n\n"
            f"Document text:\n{text[:4000]}\n\n"
            "Return JSON only with:\n"
            '{ "suggested_parser": "...", "confidence": 0.0-1.0, "reasoning": "...", "probabilities": {"parser": 0.0} }'
        )

        response = await AIService.query(
            task=AITask.CLASSIFICATION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=400,
            provider=self.provider_name,
            context=doc_metadata or {},
            enable_recovery=True,
        )

        if response.is_error:
            self.error_count += 1
            logger.warning("Unified provider classification error: %s", response.error)
            return self._fallback_result(
                available_parsers, str(response.error or "classification_error")
            )

        try:
            data = self._parse_json(response.content)
            suggested = str(data.get("suggested_parser") or available_parsers[0])
            if suggested not in available_parsers:
                suggested = available_parsers[0]

            confidence = float(data.get("confidence", 0.5))
            confidence = min(max(confidence, 0.0), 1.0)

            probabilities = data.get("probabilities")
            if not isinstance(probabilities, dict):
                probabilities = self._build_probabilities(available_parsers, suggested, confidence)

            return ClassificationResult(
                suggested_parser=suggested,
                confidence=confidence,
                probabilities=probabilities,
                reasoning=str(data.get("reasoning") or "AI classification"),
                provider=self.provider_name,
                enhanced_by_ai=True,
            )
        except Exception as exc:
            self.error_count += 1
            logger.warning("Unified provider parse error: %s", exc)
            return self._fallback_result(available_parsers, f"parse_error: {exc}")

    async def extract_fields(
        self,
        text: str,
        doc_type: str,
        expected_fields: list[str],
    ) -> dict[str, Any]:
        self.request_count += 1
        prompt = (
            f"Extract fields from a {doc_type} document.\n"
            f"Fields: {expected_fields}\n"
            f"Text:\n{text[:4000]}\n\n"
            "Return JSON object only with found fields."
        )
        response = await AIService.query(
            task=AITask.EXTRACTION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=500,
            provider=self.provider_name,
            enable_recovery=True,
        )
        if response.is_error:
            self.error_count += 1
            return {}
        try:
            data = self._parse_json(response.content)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def get_telemetry(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "requests": self.request_count,
            "errors": self.error_count,
            "error_rate": (self.error_count / self.request_count) if self.request_count else 0.0,
        }

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if "```json" in text:
                payload = text.split("```json", 1)[1].split("```", 1)[0].strip()
                return json.loads(payload)
            if "```" in text:
                payload = text.split("```", 1)[1].split("```", 1)[0].strip()
                return json.loads(payload)
            raise

    @staticmethod
    def _build_probabilities(
        parsers: list[str],
        suggested: str,
        confidence: float,
    ) -> dict[str, float]:
        rest = max(len(parsers) - 1, 1)
        other_value = round((1.0 - confidence) / rest, 3)
        return {
            parser: (round(confidence, 3) if parser == suggested else other_value)
            for parser in parsers
        }

    def _fallback_result(self, parsers: list[str], reason: str) -> ClassificationResult:
        suggested = parsers[0] if parsers else ""
        confidence = 0.2 if suggested else 0.0
        return ClassificationResult(
            suggested_parser=suggested,
            confidence=confidence,
            probabilities=(
                self._build_probabilities(parsers, suggested, confidence) if parsers else {}
            ),
            reasoning=reason,
            provider=self.provider_name,
            enhanced_by_ai=False,
        )
