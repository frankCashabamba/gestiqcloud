"""Prometheus metrics for observability."""
from __future__ import annotations

import os
import time
from functools import wraps
from typing import Callable

# Lazy imports to avoid breaking if prometheus_client not installed
_client = None
_REQUEST_COUNT = None
_REQUEST_LATENCY = None
_ACTIVE_REQUESTS = None
_DB_QUERY_COUNT = None
_DB_QUERY_LATENCY = None


def _ensure_metrics():
    """Lazily initialize Prometheus metrics."""
    global _client, _REQUEST_COUNT, _REQUEST_LATENCY, _ACTIVE_REQUESTS
    global _DB_QUERY_COUNT, _DB_QUERY_LATENCY
    
    if _client is not None:
        return True
    
    try:
        import prometheus_client as pc
        _client = pc
        
        _REQUEST_COUNT = pc.Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"]
        )
        _REQUEST_LATENCY = pc.Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        _ACTIVE_REQUESTS = pc.Gauge(
            "http_requests_active",
            "Active HTTP requests",
            ["method"]
        )
        _DB_QUERY_COUNT = pc.Counter(
            "db_queries_total",
            "Total database queries",
            ["operation"]
        )
        _DB_QUERY_LATENCY = pc.Histogram(
            "db_query_duration_seconds",
            "Database query latency",
            ["operation"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        return True
    except ImportError:
        return False


def record_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record an HTTP request metric."""
    if not _ensure_metrics():
        return
    _REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    _REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_db_query(operation: str, duration: float) -> None:
    """Record a database query metric."""
    if not _ensure_metrics():
        return
    _DB_QUERY_COUNT.labels(operation=operation).inc()
    _DB_QUERY_LATENCY.labels(operation=operation).observe(duration)


def get_metrics() -> str:
    """Generate Prometheus metrics output."""
    if not _ensure_metrics():
        return "# prometheus_client not installed\n"
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest().decode("utf-8")


def get_content_type() -> str:
    """Get the Prometheus content type."""
    if not _ensure_metrics():
        return "text/plain"
    from prometheus_client import CONTENT_TYPE_LATEST
    return CONTENT_TYPE_LATEST
