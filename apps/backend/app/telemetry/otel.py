from __future__ import annotations

import os
from typing import Optional


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes")


def init_fastapi(app) -> None:
    """Initialize OpenTelemetry for FastAPI and SQLAlchemy if enabled by env.

    Env:
      - OTEL_ENABLED=1
      - OTEL_EXPORTER_OTLP_ENDPOINT (e.g., http://collector:4317)
      - OTEL_SERVICE_NAME
    """
    if not _bool_env("OTEL_ENABLED", False):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        # engine may be missing at import-time in some tests
        try:
            from app.config.database import engine
        except Exception:
            engine = None

        service_name = os.getenv("OTEL_SERVICE_NAME", "gestiqcloud-api")
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        trace.set_tracer_provider(provider)
        exporter = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Instrument frameworks
        FastAPIInstrumentor.instrument_app(app)
        if engine is not None:
            SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception:
        # Avoid breaking app if OTEL init fails
        pass


def init_celery() -> None:
    if not _bool_env("OTEL_ENABLED", False):
        return
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
    except Exception:
        pass

