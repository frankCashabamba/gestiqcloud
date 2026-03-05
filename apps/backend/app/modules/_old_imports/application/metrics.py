"""Métricas Prometheus para imports pipeline."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

items_processed_total = Counter(
    "imports_items_processed_total",
    "Total items procesados",
    ["tenant_id", "doc_type", "status"],
)

items_current = Gauge(
    "imports_items_current",
    "Items actualmente en pipeline",
    ["queue", "tenant_id"],
)

task_duration_seconds = Histogram(
    "imports_task_duration_seconds",
    "Duración de tasks por etapa",
    ["task_name", "tenant_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

ocr_latency_seconds = Histogram(
    "imports_ocr_latency_seconds",
    "Latencia específica de OCR",
    ["tenant_id"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 180.0],
)

errors_total = Counter(
    "imports_errors_total",
    "Total errores por etapa",
    ["task_name", "tenant_id", "error_type"],
)

batch_progress = Gauge(
    "imports_batch_progress",
    "Progreso de batches activos",
    ["batch_id", "tenant_id"],
)


def record_item_processed(tenant_id: str, doc_type: str, status: str) -> None:
    items_processed_total.labels(
        tenant_id=tenant_id,
        doc_type=doc_type,
        status=status,
    ).inc()


def record_task_duration(task_name: str, tenant_id: str, duration: float) -> None:
    task_duration_seconds.labels(
        task_name=task_name,
        tenant_id=tenant_id,
    ).observe(duration)


def record_ocr_latency(tenant_id: str, duration: float) -> None:
    ocr_latency_seconds.labels(tenant_id=tenant_id).observe(duration)


def record_error(task_name: str, tenant_id: str, error_type: str) -> None:
    errors_total.labels(
        task_name=task_name,
        tenant_id=tenant_id,
        error_type=error_type,
    ).inc()
