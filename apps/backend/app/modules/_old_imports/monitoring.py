"""OCR Worker Monitoring Module.

Provides metrics collection and exposure for the OCR job processing pipeline.
Tracks queue depths, processing times, success/failure rates, and job statistics.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import session_scope
from app.models.core.modelsimport import ImportOCRJob


@dataclass
class ProcessingMetric:
    """Single job processing metric."""

    job_id: str
    duration_ms: float
    status: str  # 'done' | 'failed'
    timestamp: float = field(default_factory=time.time)


class OCRMetricsCollector:
    """Thread-safe collector for OCR processing metrics.

    Keeps a sliding window of recent job metrics for percentile calculations.
    """

    def __init__(self, window_size: int = 1000, retention_seconds: float = 3600):
        self._metrics: deque[ProcessingMetric] = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._retention = retention_seconds
        self._total_processed = 0
        self._total_failed = 0
        self._start_time = time.time()

    def record(self, job_id: str, duration_ms: float, status: str) -> None:
        """Record a completed job metric."""
        with self._lock:
            self._metrics.append(
                ProcessingMetric(
                    job_id=job_id,
                    duration_ms=duration_ms,
                    status=status,
                )
            )
            self._total_processed += 1
            if status == "failed":
                self._total_failed += 1

    def _prune_old(self) -> list[ProcessingMetric]:
        """Get recent metrics within retention window."""
        cutoff = time.time() - self._retention
        return [m for m in self._metrics if m.timestamp >= cutoff]

    def get_processing_times(self) -> dict[str, float | None]:
        """Calculate p50, p95, p99 processing times in ms."""
        with self._lock:
            recent = self._prune_old()
            durations = [m.duration_ms for m in recent if m.status == "done"]

        if not durations:
            return {"p50_ms": None, "p95_ms": None, "p99_ms": None}

        durations_sorted = sorted(durations)
        n = len(durations_sorted)

        return {
            "p50_ms": round(durations_sorted[int(n * 0.50)], 2) if n > 0 else None,
            "p95_ms": round(
                durations_sorted[int(n * 0.95)] if n >= 20 else durations_sorted[-1], 2
            ),
            "p99_ms": round(
                durations_sorted[int(n * 0.99)] if n >= 100 else durations_sorted[-1], 2
            ),
        }

    def get_rates(self) -> dict[str, float]:
        """Calculate success/error rates from recent metrics."""
        with self._lock:
            recent = self._prune_old()

        if not recent:
            return {
                "success_rate": 1.0,
                "error_rate": 0.0,
                "jobs_per_minute": 0.0,
            }

        done = sum(1 for m in recent if m.status == "done")
        failed = sum(1 for m in recent if m.status == "failed")
        total = done + failed

        # Calculate jobs per minute
        if len(recent) >= 2:
            time_span = recent[-1].timestamp - recent[0].timestamp
            jobs_per_minute = (total / time_span) * 60 if time_span > 0 else 0.0
        else:
            jobs_per_minute = 0.0

        return {
            "success_rate": round(done / total, 4) if total > 0 else 1.0,
            "error_rate": round(failed / total, 4) if total > 0 else 0.0,
            "jobs_per_minute": round(jobs_per_minute, 2),
        }

    def get_totals(self) -> dict[str, int | float]:
        """Get lifetime totals."""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "total_processed": self._total_processed,
                "total_failed": self._total_failed,
                "uptime_seconds": round(uptime, 0),
            }


# Global collector instance
_collector = OCRMetricsCollector()


def record_job_completion(job_id: str | UUID, duration_ms: float, status: str) -> None:
    """Record a job completion metric. Call this after OCR job finishes."""
    _collector.record(str(job_id), duration_ms, status)


def get_queue_metrics(db: Session | None = None) -> dict[str, Any]:
    """Get current queue state from database.

    Args:
        db: Optional SQLAlchemy session. If None, creates new session.

    Returns:
        Dict with pending, running, done, failed job counts and age metrics.
    """

    def _query(session: Session) -> dict[str, Any]:
        # Count by status
        counts = (
            session.execute(
                func.count(ImportOCRJob.id).label("total"),
            ).scalar()
            or 0
        )

        status_counts = (
            session.query(
                ImportOCRJob.status,
                func.count(ImportOCRJob.id).label("count"),
            )
            .group_by(ImportOCRJob.status)
            .all()
        )

        status_map = {row.status: row.count for row in status_counts}

        # Oldest pending job age
        oldest_pending = (
            session.query(func.min(ImportOCRJob.created_at))
            .filter(ImportOCRJob.status == "pending")
            .scalar()
        )

        oldest_pending_age_seconds = None
        if oldest_pending:
            age = datetime.utcnow() - oldest_pending.replace(tzinfo=None)
            oldest_pending_age_seconds = round(age.total_seconds(), 0)

        # Average time in pending state for recently completed jobs
        # (jobs done in last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        avg_wait = (
            session.query(
                func.avg(
                    func.extract("epoch", ImportOCRJob.updated_at)
                    - func.extract("epoch", ImportOCRJob.created_at)
                )
            )
            .filter(
                ImportOCRJob.status == "done",
                ImportOCRJob.updated_at >= cutoff,
            )
            .scalar()
        )

        return {
            "pending": status_map.get("pending", 0),
            "running": status_map.get("running", 0),
            "done": status_map.get("done", 0),
            "failed": status_map.get("failed", 0),
            "total": counts,
            "oldest_pending_age_seconds": oldest_pending_age_seconds,
            "avg_wait_time_seconds": round(avg_wait, 2) if avg_wait else None,
        }

    if db is not None:
        return _query(db)

    with session_scope() as session:
        return _query(session)


def get_processing_metrics() -> dict[str, Any]:
    """Get processing time percentiles from in-memory collector."""
    return _collector.get_processing_times()


def get_rate_metrics() -> dict[str, Any]:
    """Get success/error rates from in-memory collector."""
    return _collector.get_rates()


def get_total_metrics() -> dict[str, Any]:
    """Get lifetime totals from in-memory collector."""
    return _collector.get_totals()


def get_all_metrics(db: Session | None = None) -> dict[str, Any]:
    """Aggregate all OCR metrics into a single response.

    Returns:
        Dict with queue, processing, rates, and totals sections.
    """
    queue = get_queue_metrics(db)
    processing = get_processing_metrics()
    rates = get_rate_metrics()
    totals = get_total_metrics()

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "queue": queue,
        "processing_times": processing,
        "rates": rates,
        "totals": totals,
        "health": {
            "queue_healthy": queue["pending"] < 100,
            "error_rate_healthy": rates["error_rate"] < 0.1,
            "backlog_age_healthy": (
                queue["oldest_pending_age_seconds"] is None
                or queue["oldest_pending_age_seconds"] < 300
            ),
        },
    }


def get_tenant_metrics(db: Session, tenant_id: UUID | str) -> dict[str, Any]:
    """Get OCR metrics scoped to a specific tenant.

    Args:
        db: SQLAlchemy session
        tenant_id: Tenant UUID

    Returns:
        Dict with tenant-specific queue counts and recent job stats.
    """
    tid = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    # Count by status for this tenant
    status_counts = (
        db.query(
            ImportOCRJob.status,
            func.count(ImportOCRJob.id).label("count"),
        )
        .filter(ImportOCRJob.tenant_id == tid)
        .group_by(ImportOCRJob.status)
        .all()
    )

    status_map = {row.status: row.count for row in status_counts}

    # Recent jobs (last 24h)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent = (
        db.query(
            ImportOCRJob.status,
            func.count(ImportOCRJob.id).label("count"),
        )
        .filter(
            ImportOCRJob.tenant_id == tid,
            ImportOCRJob.created_at >= cutoff,
        )
        .group_by(ImportOCRJob.status)
        .all()
    )

    recent_map = {row.status: row.count for row in recent}

    return {
        "tenant_id": tid,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "all_time": {
            "pending": status_map.get("pending", 0),
            "running": status_map.get("running", 0),
            "done": status_map.get("done", 0),
            "failed": status_map.get("failed", 0),
        },
        "last_24h": {
            "pending": recent_map.get("pending", 0),
            "running": recent_map.get("running", 0),
            "done": recent_map.get("done", 0),
            "failed": recent_map.get("failed", 0),
        },
    }
