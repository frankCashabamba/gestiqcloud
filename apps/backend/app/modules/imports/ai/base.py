"""Base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ClassificationResult:
    """Result of a document classification."""

    suggested_parser: str
    confidence: float
    probabilities: dict[str, float]  # {parser_id: score}
    reasoning: str
    provider: str
    enhanced_by_ai: bool = False


class AIProvider(ABC):
    """Abstract base class for AI document classification providers."""

    @abstractmethod
    async def classify_document(
        self,
        text: str,
        available_parsers: list[str],
        doc_metadata: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Classify a document to select the best parser.

        Args:
            text: Document text content
            available_parsers: List of available parser IDs
            doc_metadata: Optional metadata (filename, file_type, etc.)

        Returns:
            ClassificationResult with suggested parser and confidence
        """
        pass

    @abstractmethod
    async def extract_fields(
        self,
        text: str,
        doc_type: str,
        expected_fields: list[str],
    ) -> dict[str, Any]:
        """
        Extract specific fields from document.

        Args:
            text: Document text content
            doc_type: Document type (invoice, receipt, bank_tx, etc.)
            expected_fields: List of field names to extract

        Returns:
            Dictionary with extracted fields
        """
        pass

    @abstractmethod
    def get_telemetry(self) -> dict[str, Any]:
        """
        Get telemetry and usage metrics.

        Returns:
            Dictionary with provider stats (requests, cost, latency, etc.)
        """
        pass

    async def enhance_classification(
        self,
        base_result: ClassificationResult,
        text: str,
        available_parsers: list[str],
        confidence_threshold: float = 0.7,
    ) -> ClassificationResult:
        """
        Enhance base classification with AI if confidence is below threshold.

        Default implementation: use AI if base_result.confidence < threshold
        """
        if base_result.confidence < confidence_threshold:
            ai_result = await self.classify_document(text, available_parsers)
            if ai_result.confidence > base_result.confidence:
                ai_result.enhanced_by_ai = True
                return ai_result

        return base_result
