"""
Auto-learning mapping feedback system.
Learns from manual corrections to improve future mappings.
"""

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger("imports.mapping_feedback")


class FeedbackType(str, Enum):
    """Type of feedback on a mapping."""
    ACCEPTED = "accepted"  # User kept auto-mapping, no changes
    CORRECTED = "corrected"  # User corrected one or more fields
    REJECTED = "rejected"  # User rejected entire document mapping


@dataclass
class FieldFeedback:
    """Feedback on a single field mapping."""
    field_name: str  # Source field (header)
    canonical_field: str  # Canonical field we suggested
    user_corrected_to: Optional[str] = None  # If user changed it
    confidence: float = 0.5  # Our confidence in the mapping (0-1)
    was_correct: bool = True  # Did our suggestion match user's intent?


@dataclass
class MappingFeedback:
    """Feedback on a complete document mapping."""
    id: Optional[UUID] = None
    tenant_id: UUID = None
    batch_id: Optional[UUID] = None
    item_id: Optional[UUID] = None
    
    # Document context
    doc_type: str = ""  # "sales_invoice", "expense", etc.
    headers: list[str] = field(default_factory=list)  # Column names from file
    
    # Mapping feedback
    field_feedbacks: dict[str, FieldFeedback] = field(default_factory=dict)
    feedback_type: FeedbackType = FeedbackType.ACCEPTED
    
    # User context
    user_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # File context
    filename: Optional[str] = None
    file_hash: Optional[str] = None  # For deduplication
    
    def mark_field_correct(self, source_field: str, canonical: str, confidence: float = 0.5):
        """Mark a field mapping as correct."""
        self.field_feedbacks[source_field] = FieldFeedback(
            field_name=source_field,
            canonical_field=canonical,
            confidence=confidence,
            was_correct=True,
        )
        if self.feedback_type == FeedbackType.ACCEPTED:
            return
        self.feedback_type = FeedbackType.CORRECTED
    
    def mark_field_corrected(self, source_field: str, our_suggestion: str, user_choice: str, confidence: float = 0.5):
        """Mark a field mapping as corrected by user."""
        self.field_feedbacks[source_field] = FieldFeedback(
            field_name=source_field,
            canonical_field=our_suggestion,
            user_corrected_to=user_choice,
            confidence=confidence,
            was_correct=False,
        )
        self.feedback_type = FeedbackType.CORRECTED
    
    def mark_rejected(self):
        """Mark entire mapping as rejected."""
        self.feedback_type = FeedbackType.REJECTED


class MappingLearner:
    """
    Learns from mapping feedback to improve future suggestions.
    Tracks: which mappings work, which fail, confidence scores.
    """
    
    def __init__(self, storage_file: str = "data/feedback/mapping_learner_stats.json"):
        # In-memory learning state (will be persisted to DB in implementation)
        # Structure: {tenant_id: {doc_type: {source_field: [(canonical, correct_count, total_count), ...]}}}
        self.mapping_stats: dict[Any, dict[str, dict[str, dict[str, dict[str, int]]]]] = {}
        self.storage_file = Path(storage_file)
        self._persistence_enabled = True
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._persistence_enabled = False
            logger.warning(f"Mapping learner persistence disabled: {e}")
        self._load()

    def _normalize_tenant_id(self, tenant_id: Any) -> str:
        return str(tenant_id)

    def _get_tenant_stats_bucket(self, tenant_id: Any) -> dict[str, dict[str, dict[str, dict[str, int]]]] | None:
        """Return tenant stats bucket accepting UUID or string keys."""
        if tenant_id in self.mapping_stats:
            return self.mapping_stats[tenant_id]
        normalized_tenant = self._normalize_tenant_id(tenant_id)
        if normalized_tenant in self.mapping_stats:
            return self.mapping_stats[normalized_tenant]
        return None

    def _normalize_header(self, header: str) -> str:
        text = unicodedata.normalize("NFKD", str(header or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _load(self) -> None:
        if not self._persistence_enabled:
            self.mapping_stats = {}
            return
        if not self.storage_file.exists():
            self.mapping_stats = {}
            return
        try:
            with self.storage_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.mapping_stats = data
                    return
        except Exception as e:
            logger.warning(f"Failed to load mapping learner stats: {e}")
        self.mapping_stats = {}

    def _save(self) -> None:
        if not self._persistence_enabled:
            return
        try:
            serialized = {str(k): v for k, v in self.mapping_stats.items()}
            with self.storage_file.open("w", encoding="utf-8") as f:
                json.dump(serialized, f, ensure_ascii=True, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save mapping learner stats: {e}")
    
    def record_feedback(self, feedback: MappingFeedback):
        """
        Record mapping feedback to learn from.
        Updates statistics for future suggestions.
        """
        tenant_id = feedback.tenant_id
        doc_type = feedback.doc_type
        
        # Initialize tenant if needed
        if tenant_id not in self.mapping_stats:
            self.mapping_stats[tenant_id] = {}
        
        if doc_type not in self.mapping_stats[tenant_id]:
            self.mapping_stats[tenant_id][doc_type] = {}
        
        type_stats = self.mapping_stats[tenant_id][doc_type]
        
        # Update stats for each field
        for source_field, field_feedback in feedback.field_feedbacks.items():
            normalized_source = self._normalize_header(source_field)
            if normalized_source not in type_stats:
                type_stats[normalized_source] = {}
            
            field_stats = type_stats[normalized_source]
            canonical = field_feedback.canonical_field
            
            if canonical not in field_stats:
                field_stats[canonical] = {"correct": 0, "total": 0}
            
            field_stats[canonical]["total"] += 1
            if field_feedback.was_correct:
                field_stats[canonical]["correct"] += 1
        self._save()
    
    def get_suggested_mapping(
        self,
        tenant_id: UUID,
        doc_type: str,
        headers: list[str],
        baseline_mapping: dict[str, str],
    ) -> dict[str, str]:
        """
        Get mapping suggestion for tenant, enhanced with learned patterns.
        
        Args:
            tenant_id: Tenant ID
            doc_type: Document type
            headers: Column headers from file
            baseline_mapping: Base mapping from universal_validator
        
        Returns:
            Enhanced mapping with learned weights
        """
        # Start with baseline
        suggestion = baseline_mapping.copy()
        
        # If no learning data, return baseline
        tenant_stats = self._get_tenant_stats_bucket(tenant_id)
        if tenant_stats is None or doc_type not in tenant_stats:
            return suggestion

        type_stats = tenant_stats[doc_type]
        
        # For each header, check if we have learned better mappings
        for header in headers:
            normalized_header = self._normalize_header(header)
            if normalized_header not in type_stats:
                continue
            
            field_stats = type_stats[normalized_header]
            if not field_stats:
                continue
            
            # Find best mapping by accuracy
            best_canonical = None
            best_accuracy = 0
            
            for canonical, stats in field_stats.items():
                if stats["total"] == 0:
                    continue
                accuracy = stats["correct"] / stats["total"]
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_canonical = canonical
            
            # Only override if we have enough data and confidence
            if best_canonical and best_accuracy > 0.7:
                suggestion[header] = best_canonical
        
        return suggestion
    
    def get_mapping_confidence(
        self,
        tenant_id: UUID,
        doc_type: str,
        header: str,
        canonical: str,
    ) -> float:
        """
        Get confidence score for a specific mapping.
        
        Returns: 0-1 confidence (0.5 = no data, 1.0 = always correct)
        """
        tenant_stats = self._get_tenant_stats_bucket(tenant_id)
        if tenant_stats is None or doc_type not in tenant_stats:
            return 0.5

        type_stats = tenant_stats[doc_type]
        normalized_header = self._normalize_header(header)
        if normalized_header not in type_stats:
            return 0.5
        
        field_stats = type_stats[normalized_header]
        
        if canonical not in field_stats:
            return 0.5
        
        stats = field_stats[canonical]
        if stats["total"] == 0:
            return 0.5
        
        return stats["correct"] / stats["total"]
    
    def get_top_candidates(
        self,
        tenant_id: UUID,
        doc_type: str,
        header: str,
        top_n: int = 3,
    ) -> list[tuple[str, float]]:
        """
        Get top N candidate mappings for a field.
        
        Returns: [(canonical_field, accuracy), ...]
        """
        tenant_stats = self._get_tenant_stats_bucket(tenant_id)
        if tenant_stats is None or doc_type not in tenant_stats:
            return []

        type_stats = tenant_stats[doc_type]
        normalized_header = self._normalize_header(header)
        if normalized_header not in type_stats:
            return []
        
        field_stats = type_stats[normalized_header]
        
        # Rank by accuracy then by frequency
        candidates = []
        for canonical, stats in field_stats.items():
            if stats["total"] == 0:
                continue
            accuracy = stats["correct"] / stats["total"]
            candidates.append((canonical, accuracy, stats["total"]))
        
        # Sort by accuracy desc, then by total count desc
        candidates.sort(key=lambda x: (-x[1], -x[2]))
        
        return [(c[0], c[1]) for c in candidates[:top_n]]
    
    def should_confirm_mapping(
        self,
        tenant_id: UUID,
        doc_type: str,
        headers: list[str],
        mapping: dict[str, str],
        confidence_threshold: float = 0.7,
    ) -> bool:
        """
        Decide if mapping should be auto-confirmed or needs user review.
        
        Returns: True if confident, False if needs confirmation
        """
        # If no learning data, ask for confirmation
        tenant_stats = self._get_tenant_stats_bucket(tenant_id)
        if tenant_stats is None or doc_type not in tenant_stats:
            return False

        type_stats = tenant_stats[doc_type]
        
        # Check confidence of all mapped fields
        for header, canonical in mapping.items():
            normalized_header = self._normalize_header(header)
            if normalized_header not in type_stats:
                # Unknown header pattern - need confirmation
                return False
            
            field_stats = type_stats[normalized_header]
            if canonical not in field_stats:
                # Unknown mapping - need confirmation
                return False
            
            stats = field_stats[canonical]
            if stats["total"] == 0:
                return False
            
            accuracy = stats["correct"] / stats["total"]
            if accuracy < confidence_threshold:
                return False
        
        return True


# Global learner instance
mapping_learner = MappingLearner()
