"""
Confidence-based gating for import processing.
Blocks promotion (next stage) if confidence is below threshold.
Requires explicit user confirmation for uncertain classifications.
"""

from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Confidence levels for decision gating."""

    HIGH = "high"  # >= 0.85 - auto-approve
    MEDIUM = "medium"  # 0.70-0.85 - warn, allow override
    LOW = "low"  # < 0.70 - block, require confirmation
    UNKNOWN = "unknown"  # No confidence data


@dataclass
class ConfidenceGate:
    """Confidence-based decision gate for a document."""

    document_id: str
    doc_type: str

    # Confidence components (0-1 scale)
    parser_confidence: float  # How sure we are about the parser
    doc_type_confidence: float  # How sure we are about doc classification
    mapping_confidence: float  # How sure we are about field mappings
    validation_confidence: float  # How sure we are doc is valid

    # Derived
    overall_confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNKNOWN

    def calculate_overall(self):
        """Calculate overall confidence as weighted average."""
        weights = {
            "parser": 0.20,  # Parser choice is important
            "doc_type": 0.25,  # Doc type classification is critical
            "mapping": 0.30,  # Field mapping is critical
            "validation": 0.25,  # Validation is important
        }

        self.overall_confidence = (
            self.parser_confidence * weights["parser"]
            + self.doc_type_confidence * weights["doc_type"]
            + self.mapping_confidence * weights["mapping"]
            + self.validation_confidence * weights["validation"]
        )

        self.confidence_level = self._level_from_score(self.overall_confidence)
        return self.overall_confidence

    def _level_from_score(self, score: float) -> ConfidenceLevel:
        """Map numeric score to confidence level."""
        if score >= 0.85:
            return ConfidenceLevel.HIGH
        elif score >= 0.70:
            return ConfidenceLevel.MEDIUM
        elif score > 0:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNKNOWN

    def should_auto_approve(self) -> bool:
        """Should this document be auto-approved?"""
        return self.confidence_level == ConfidenceLevel.HIGH

    def requires_confirmation(self) -> bool:
        """Does this document require user confirmation?"""
        return self.confidence_level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)

    def should_block_promotion(self) -> bool:
        """Should we block promotion to next stage?"""
        return self.confidence_level == ConfidenceLevel.LOW


class ConfidenceGatingPolicy:
    """
    Policy for handling documents based on confidence levels.
    Configurable thresholds per document type and tenant.
    """

    def __init__(
        self,
        auto_approve_threshold: float = 0.85,
        require_confirm_threshold: float = 0.70,
        block_promotion_threshold: float = 0.70,
    ):
        self.auto_approve_threshold = auto_approve_threshold
        self.require_confirm_threshold = require_confirm_threshold
        self.block_promotion_threshold = block_promotion_threshold

    def evaluate(self, gate: ConfidenceGate) -> dict:
        """
        Evaluate a document against policy.

        Returns:
            {
                "action": "auto_approve" | "confirm" | "block",
                "message": "...",
                "components": {
                    "parser": {...},
                    "doc_type": {...},
                    "mapping": {...},
                    "validation": {...},
                }
            }
        """
        gate.calculate_overall()

        confidence = gate.overall_confidence

        if confidence >= self.auto_approve_threshold:
            action = "auto_approve"
            message = f"High confidence ({confidence:.0%}). Approved."
        elif confidence >= self.require_confirm_threshold:
            action = "confirm"
            message = f"Medium confidence ({confidence:.0%}). User confirmation required."
        else:
            action = "block"
            message = f"Low confidence ({confidence:.0%}). Promotion blocked. Requires user review."

        return {
            "action": action,
            "message": message,
            "overall_confidence": confidence,
            "confidence_level": gate.confidence_level.value,
            "components": {
                "parser": {
                    "confidence": gate.parser_confidence,
                    "level": self._level_from_score(gate.parser_confidence).value,
                },
                "doc_type": {
                    "confidence": gate.doc_type_confidence,
                    "level": self._level_from_score(gate.doc_type_confidence).value,
                },
                "mapping": {
                    "confidence": gate.mapping_confidence,
                    "level": self._level_from_score(gate.mapping_confidence).value,
                },
                "validation": {
                    "confidence": gate.validation_confidence,
                    "level": self._level_from_score(gate.validation_confidence).value,
                },
            },
        }

    def _level_from_score(self, score: float) -> ConfidenceLevel:
        """Map numeric score to confidence level."""
        if score >= 0.85:
            return ConfidenceLevel.HIGH
        elif score >= 0.70:
            return ConfidenceLevel.MEDIUM
        elif score > 0:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNKNOWN


class UserConfirmation:
    """Tracks user confirmation of uncertain documents."""

    def __init__(
        self,
        document_id: str,
        gate: ConfidenceGate,
    ):
        self.document_id = document_id
        self.gate = gate
        self.confirmed = False
        self.confirmation_data = {}

    def confirm_parser(self, parser: str):
        """User confirmed parser choice."""
        self.confirmation_data["parser"] = parser

    def confirm_doc_type(self, doc_type: str):
        """User confirmed document type."""
        self.confirmation_data["doc_type"] = doc_type

    def confirm_mapping(self, mapping: dict[str, str]):
        """User confirmed field mapping."""
        self.confirmation_data["mapping"] = mapping

    def mark_confirmed(self):
        """Mark document as confirmed by user."""
        self.confirmed = True

    def get_confirmation_requirements(self) -> list[str]:
        """Get list of things that need user confirmation."""
        requirements = []

        if self.gate.parser_confidence < 0.70:
            requirements.append("parser")

        if self.gate.doc_type_confidence < 0.70:
            requirements.append("doc_type")

        if self.gate.mapping_confidence < 0.70:
            requirements.append("mapping")

        if self.gate.validation_confidence < 0.70:
            requirements.append("validation")

        return requirements


# Default policy instance
default_confidence_policy = ConfidenceGatingPolicy(
    auto_approve_threshold=0.85,
    require_confirm_threshold=0.70,
    block_promotion_threshold=0.70,
)


def create_gate(
    document_id: str,
    doc_type: str,
    parser_confidence: float,
    doc_type_confidence: float,
    mapping_confidence: float,
    validation_confidence: float,
) -> ConfidenceGate:
    """Factory function to create a confidence gate."""
    return ConfidenceGate(
        document_id=document_id,
        doc_type=doc_type,
        parser_confidence=parser_confidence,
        doc_type_confidence=doc_type_confidence,
        mapping_confidence=mapping_confidence,
        validation_confidence=validation_confidence,
    )
