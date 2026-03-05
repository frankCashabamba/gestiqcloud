from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Metric:
    name: str
    value: float
    timestamp: str
    tags: dict = field(default_factory=dict)


@dataclass
class MetricsBucket:
    doc_type: str
    total_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_confidence: float = 0.0
    avg_processing_time_ms: float = 0.0
    errors_by_reason: dict = field(default_factory=dict)


class MetricsCollector:
    def __init__(self):
        self.metrics: list[Metric] = []
        self.buckets: dict[str, MetricsBucket] = {}

    def record_metric(self, name: str, value: float, tags: dict | None = None) -> None:
        self.metrics.append(
            Metric(
                name=name,
                value=value,
                timestamp=datetime.utcnow().isoformat(),
                tags=tags or {},
            )
        )

    def record_classification(
        self,
        doc_type: str,
        confidence: float,
        processing_time_ms: float,
        success: bool,
        error_reason: str | None = None,
    ) -> None:
        if doc_type not in self.buckets:
            self.buckets[doc_type] = MetricsBucket(doc_type=doc_type)

        bucket = self.buckets[doc_type]
        bucket.total_processed += 1

        if success:
            bucket.success_count += 1
            bucket.avg_confidence = (
                bucket.avg_confidence * (bucket.success_count - 1) + confidence
            ) / bucket.success_count
        else:
            bucket.error_count += 1
            if error_reason:
                bucket.errors_by_reason[error_reason] = (
                    bucket.errors_by_reason.get(error_reason, 0) + 1
                )

        bucket.avg_processing_time_ms = (
            bucket.avg_processing_time_ms * (bucket.total_processed - 1) + processing_time_ms
        ) / bucket.total_processed

    def get_metrics_summary(self) -> dict:
        return {
            "total_metrics_recorded": len(self.metrics),
            "doc_types_tracked": len(self.buckets),
            "buckets": {
                doc_type: {
                    "total_processed": bucket.total_processed,
                    "success_count": bucket.success_count,
                    "error_count": bucket.error_count,
                    "success_rate": (
                        bucket.success_count / bucket.total_processed
                        if bucket.total_processed > 0
                        else 0.0
                    ),
                    "avg_confidence": bucket.avg_confidence,
                    "avg_processing_time_ms": bucket.avg_processing_time_ms,
                    "errors_by_reason": bucket.errors_by_reason,
                }
                for doc_type, bucket in self.buckets.items()
            },
        }

    def get_metrics_by_doc_type(self, doc_type: str) -> dict | None:
        if doc_type not in self.buckets:
            return None

        bucket = self.buckets[doc_type]
        return {
            "doc_type": doc_type,
            "total_processed": bucket.total_processed,
            "success_count": bucket.success_count,
            "error_count": bucket.error_count,
            "success_rate": (
                bucket.success_count / bucket.total_processed if bucket.total_processed > 0 else 0.0
            ),
            "avg_confidence": bucket.avg_confidence,
            "avg_processing_time_ms": bucket.avg_processing_time_ms,
            "errors_by_reason": bucket.errors_by_reason,
        }

    def export_metrics(self) -> list[dict]:
        return [
            {
                "name": m.name,
                "value": m.value,
                "timestamp": m.timestamp,
                "tags": m.tags,
            }
            for m in self.metrics
        ]


class RollbackManager:
    def __init__(self):
        self.versions = {}
        self.current_version = None
        self.rollback_history = []

    def save_version(self, version_name: str, classifier, timestamp: str) -> None:
        self.versions[version_name] = {
            "classifier": classifier,
            "timestamp": timestamp,
            "active": False,
        }

    def set_active_version(self, version_name: str) -> bool:
        if version_name not in self.versions:
            return False

        if self.current_version:
            self.versions[self.current_version]["active"] = False

        self.versions[version_name]["active"] = True
        self.current_version = version_name
        return True

    def rollback_to_version(self, version_name: str) -> bool:
        if version_name not in self.versions:
            return False

        self.rollback_history.append(
            {
                "from_version": self.current_version,
                "to_version": version_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return self.set_active_version(version_name)

    def get_available_versions(self) -> list[str]:
        return list(self.versions.keys())

    def get_rollback_history(self) -> list[dict]:
        return self.rollback_history.copy()
