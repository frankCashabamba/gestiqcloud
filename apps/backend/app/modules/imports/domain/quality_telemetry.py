"""
Quality telemetry tracking for import operations.
Measures accuracy, correction rates, and performance metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    """Types of quality metrics."""

    PARSER_ACCURACY = "parser_accuracy"  # % of correct parser choices
    DOC_TYPE_ACCURACY = "doc_type_accuracy"  # % of correct classifications
    MAPPING_ACCURACY = "mapping_accuracy"  # % of correct field mappings
    VALIDATION_PASS_RATE = "validation_pass_rate"  # % of documents passing validation
    MANUAL_CORRECTION_RATE = "manual_correction_rate"  # % of docs requiring manual fixes
    PROMOTION_SUCCESS_RATE = "promotion_success_rate"  # % of promoted docs that succeeded


@dataclass
class QualityMetric:
    """Single quality metric."""

    metric_type: MetricType
    value: float  # 0-1 scale for percentages, raw number otherwise
    sample_size: int  # How many samples this is based on
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Context
    tenant_id: str | None = None
    doc_type: str | None = None  # "sales_invoice", "expense", etc.
    time_period: str | None = None  # "daily", "weekly", "monthly"

    def is_sufficient_data(self, min_samples: int = 10) -> bool:
        """Check if metric has enough samples to be meaningful."""
        return self.sample_size >= min_samples


@dataclass
class QualityTimeline:
    """Timeline of quality metrics over time."""

    metric_type: MetricType
    data_points: list[QualityMetric] = field(default_factory=list)

    def add_metric(self, metric: QualityMetric):
        """Add a metric data point."""
        self.data_points.append(metric)

    def get_trend(self) -> str | None:
        """Get trend direction."""
        if len(self.data_points) < 2:
            return None

        recent = self.data_points[-1].value
        previous = self.data_points[-2].value

        if recent > previous + 0.05:
            return "improving"
        elif recent < previous - 0.05:
            return "declining"
        else:
            return "stable"

    def get_average(self, last_n: int = 10) -> float:
        """Get average metric value over last N periods."""
        if not self.data_points:
            return 0.0

        relevant = self.data_points[-last_n:]
        return sum(m.value for m in relevant) / len(relevant)


class QualityTelemetryCollector:
    """
    Collects and aggregates quality metrics.
    Tracks performance per tenant, doc type, and time period.
    """

    def __init__(self):
        # Storage: {metric_type: {tenant_id: {doc_type: QualityTimeline}}}
        self.metrics = {}

    def record_parser_decision(
        self,
        tenant_id: str,
        suggested_parser: str,
        doc_type: str,
        is_correct: bool,
    ):
        """Record a parser decision (correct or incorrect)."""
        self._record_metric(
            MetricType.PARSER_ACCURACY,
            tenant_id,
            doc_type,
            1.0 if is_correct else 0.0,
        )

    def record_doc_type_classification(
        self,
        tenant_id: str,
        suggested_doc_type: str,
        actual_doc_type: str,
        confidence: float,
    ):
        """Record a document type classification."""
        is_correct = suggested_doc_type == actual_doc_type
        self._record_metric(
            MetricType.DOC_TYPE_ACCURACY,
            tenant_id,
            suggested_doc_type,
            1.0 if is_correct else 0.0,
        )

    def record_mapping_accuracy(
        self,
        tenant_id: str,
        doc_type: str,
        correct_mappings: int,
        total_mappings: int,
    ):
        """Record field mapping accuracy."""
        if total_mappings == 0:
            accuracy = 0.0
        else:
            accuracy = correct_mappings / total_mappings

        self._record_metric(
            MetricType.MAPPING_ACCURACY,
            tenant_id,
            doc_type,
            accuracy,
        )

    def record_validation_result(
        self,
        tenant_id: str,
        doc_type: str,
        passed_validation: bool,
    ):
        """Record whether document passed validation."""
        self._record_metric(
            MetricType.VALIDATION_PASS_RATE,
            tenant_id,
            doc_type,
            1.0 if passed_validation else 0.0,
        )

    def record_manual_correction(
        self,
        tenant_id: str,
        doc_type: str,
        required_correction: bool,
    ):
        """Record whether document required manual correction."""
        self._record_metric(
            MetricType.MANUAL_CORRECTION_RATE,
            tenant_id,
            doc_type,
            1.0 if required_correction else 0.0,
        )

    def record_promotion_attempt(
        self,
        tenant_id: str,
        doc_type: str,
        succeeded: bool,
    ):
        """Record promotion (next stage) attempt."""
        self._record_metric(
            MetricType.PROMOTION_SUCCESS_RATE,
            tenant_id,
            doc_type,
            1.0 if succeeded else 0.0,
        )

    def _record_metric(
        self,
        metric_type: MetricType,
        tenant_id: str,
        doc_type: str,
        value: float,
    ):
        """Internal method to record a metric."""
        if metric_type not in self.metrics:
            self.metrics[metric_type] = {}

        if tenant_id not in self.metrics[metric_type]:
            self.metrics[metric_type][tenant_id] = {}

        if doc_type not in self.metrics[metric_type][tenant_id]:
            self.metrics[metric_type][tenant_id][doc_type] = QualityTimeline(metric_type)

        timeline = self.metrics[metric_type][tenant_id][doc_type]

        # Create metric (will be aggregated into timeline)
        metric = QualityMetric(
            metric_type=metric_type,
            value=value,
            sample_size=1,
            tenant_id=tenant_id,
            doc_type=doc_type,
        )
        timeline.add_metric(metric)

    def get_metric_summary(
        self,
        tenant_id: str,
        doc_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Get summary of quality metrics for a tenant/doc_type.

        Returns:
            {
                "parser_accuracy": {"value": 0.95, "trend": "improving", ...},
                "doc_type_accuracy": {...},
                ...
            }
        """
        summary = {}

        for metric_type, tenants in self.metrics.items():
            if tenant_id not in tenants:
                continue

            doc_types = tenants[tenant_id]

            # Filter by doc_type if specified
            if doc_type:
                if doc_type not in doc_types:
                    continue
                timelines = {doc_type: doc_types[doc_type]}
            else:
                timelines = doc_types

            # Aggregate across doc_types
            all_values = []
            for timeline in timelines.values():
                if timeline.data_points:
                    all_values.extend([m.value for m in timeline.data_points])

            if not all_values:
                continue

            avg = sum(all_values) / len(all_values)

            summary[metric_type.value] = {
                "value": avg,
                "sample_size": len(all_values),
                "min": min(all_values),
                "max": max(all_values),
            }

        return summary

    def get_accuracy_by_doc_type(
        self,
        tenant_id: str,
    ) -> dict[str, dict[str, float]]:
        """
        Get accuracy metrics broken down by document type.

        Returns:
            {
                "sales_invoice": {
                    "parser_accuracy": 0.95,
                    "doc_type_accuracy": 0.92,
                    ...
                },
                "expense": {...},
            }
        """
        result = {}

        # Collect all doc_types for this tenant
        doc_types_set = set()
        for metric_type, tenants in self.metrics.items():
            if tenant_id in tenants:
                doc_types_set.update(tenants[tenant_id].keys())

        # For each doc_type, collect its metrics
        for doc_type in doc_types_set:
            result[doc_type] = {}

            for metric_type, tenants in self.metrics.items():
                if tenant_id not in tenants:
                    continue
                if doc_type not in tenants[tenant_id]:
                    continue

                timeline = tenants[tenant_id][doc_type]
                if timeline.data_points:
                    avg = timeline.get_average()
                    result[doc_type][metric_type.value] = avg

        return result

    def get_trend_analysis(
        self,
        tenant_id: str,
    ) -> dict[str, str]:
        """
        Get trend analysis (improving/declining/stable) for each metric.

        Returns:
            {
                "parser_accuracy": "improving",
                "doc_type_accuracy": "stable",
                ...
            }
        """
        trends = {}

        for metric_type, tenants in self.metrics.items():
            if tenant_id not in tenants:
                continue

            # Get trend across all doc_types for this metric
            all_timelines = tenants[tenant_id].values()

            if not all_timelines:
                continue

            # Combine trends (if most are improving, say improving)
            trend_counts = {"improving": 0, "declining": 0, "stable": 0}

            for timeline in all_timelines:
                trend = timeline.get_trend()
                if trend:
                    trend_counts[trend] += 1

            # Determine overall trend
            total = sum(trend_counts.values())
            if total == 0:
                overall_trend = "unknown"
            else:
                overall_trend = max(trend_counts, key=trend_counts.get)

            trends[metric_type.value] = overall_trend

        return trends


# Global collector instance
quality_telemetry = QualityTelemetryCollector()
