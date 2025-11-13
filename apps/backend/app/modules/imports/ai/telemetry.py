"""Telemetry and logging for AI classifications."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("imports.ai.telemetry")


@dataclass
class ClassificationMetric:
    """Single classification metric record."""
    timestamp: datetime
    document_type: str
    parser_suggested: str
    confidence: float
    provider: str
    execution_time_ms: float
    text_length: int = 0
    correct: Optional[bool] = None  # Posterior validation
    cost: float = 0.0
    file_name: Optional[str] = None
    tenant_id: Optional[str] = None


class AITelemetry:
    """Track AI classification metrics for accuracy and cost monitoring."""
    
    def __init__(self, max_metrics: int = 10000):
        """
        Initialize telemetry tracker.
        
        Args:
            max_metrics: Maximum metrics to keep in memory (FIFO)
        """
        self.metrics: List[ClassificationMetric] = []
        self.max_metrics = max_metrics
        self.logger = logging.getLogger("imports.ai.telemetry")
    
    def record(self, metric: ClassificationMetric) -> None:
        """Record a classification metric."""
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
        
        # Log
        self.logger.info(
            f"Classification: {metric.document_type} "
            f"(confidence: {metric.confidence:.0%}) "
            f"via {metric.provider} "
            f"({metric.execution_time_ms:.0f}ms, "
            f"${metric.cost:.6f})"
        )
    
    def get_accuracy(self, provider: Optional[str] = None) -> float:
        """
        Calculate accuracy from validated metrics.
        
        Args:
            provider: Filter by provider (None = all)
        
        Returns:
            Accuracy as float 0-1
        """
        # Filter metrics that have been validated
        validated = [m for m in self.metrics if m.correct is not None]
        
        if not validated:
            return 0.0
        
        if provider:
            validated = [m for m in validated if m.provider == provider]
        
        if not validated:
            return 0.0
        
        correct = sum(1 for m in validated if m.correct)
        return correct / len(validated)
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics per provider."""
        providers = {}
        
        for metric in self.metrics:
            if metric.provider not in providers:
                providers[metric.provider] = {
                    "count": 0,
                    "avg_confidence": 0.0,
                    "avg_time_ms": 0.0,
                    "total_cost": 0.0,
                    "validated_count": 0,
                    "correct_count": 0,
                }
            
            p = providers[metric.provider]
            p["count"] += 1
            p["total_cost"] += metric.cost
            
            if metric.correct is not None:
                p["validated_count"] += 1
                if metric.correct:
                    p["correct_count"] += 1
        
        # Compute averages
        for provider, stats in providers.items():
            if stats["count"] > 0:
                # Recalculate averages from all metrics
                provider_metrics = [
                    m for m in self.metrics if m.provider == provider
                ]
                stats["avg_confidence"] = sum(
                    m.confidence for m in provider_metrics
                ) / len(provider_metrics)
                stats["avg_time_ms"] = sum(
                    m.execution_time_ms for m in provider_metrics
                ) / len(provider_metrics)
                
                if stats["validated_count"] > 0:
                    stats["accuracy"] = (
                        stats["correct_count"] / stats["validated_count"]
                    )
        
        return providers
    
    def get_total_cost(self, provider: Optional[str] = None) -> float:
        """Get total cost by provider."""
        filtered = self.metrics
        if provider:
            filtered = [m for m in filtered if m.provider == provider]
        
        return sum(m.cost for m in filtered)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall summary."""
        if not self.metrics:
            return {}
        
        return {
            "total_requests": len(self.metrics),
            "providers": self.get_provider_stats(),
            "total_cost": self.get_total_cost(),
            "avg_confidence": sum(
                m.confidence for m in self.metrics
            ) / len(self.metrics),
            "avg_time_ms": sum(
                m.execution_time_ms for m in self.metrics
            ) / len(self.metrics),
            "oldest_metric": self.metrics[0].timestamp.isoformat(),
            "newest_metric": self.metrics[-1].timestamp.isoformat(),
        }
    
    def mark_correct(self, metric_index: int, correct: bool) -> None:
        """Mark a metric as validated (correct/incorrect)."""
        if 0 <= metric_index < len(self.metrics):
            self.metrics[metric_index].correct = correct
    
    def export_metrics(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export metrics as list of dicts."""
        filtered = self.metrics
        if provider:
            filtered = [m for m in filtered if m.provider == provider]
        
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "document_type": m.document_type,
                "parser_suggested": m.parser_suggested,
                "confidence": round(m.confidence, 3),
                "provider": m.provider,
                "execution_time_ms": round(m.execution_time_ms, 2),
                "text_length": m.text_length,
                "correct": m.correct,
                "cost": round(m.cost, 6),
                "file_name": m.file_name,
                "tenant_id": m.tenant_id,
            }
            for m in filtered
        ]


# Global telemetry instance
telemetry = AITelemetry()
