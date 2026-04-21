"""
Telemetry and logging utilities for catalog operations.
Provides structured logging and metrics collection for monitoring and debugging.
"""

import json
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from typing import Any

from fastapi import Request


class TelemetryEvent:
    """Structured telemetry event for catalog operations."""

    def __init__(
        self,
        event_type: str,
        entity_type: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        operation: str | None = None,
        entity_id: str | None = None,
        duration_ms: float | None = None,
        status: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.event_id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.event_type = event_type  # 'catalog_operation', 'performance', 'error'
        self.entity_type = entity_type  # 'BusinessType', 'EmployeeDepartment', etc.
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.operation = operation  # 'create', 'read', 'update', 'delete', 'list'
        self.entity_id = entity_id
        self.duration_ms = duration_ms
        self.status = status  # 'success', 'error', 'warning'
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for logging."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "entity_id": self.entity_id,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }


class CatalogTelemetry:
    """Telemetry collector for catalog operations."""

    def __init__(self, service_name: str = "catalog_service"):
        self.service_name = service_name
        self._events: list[TelemetryEvent] = []
        self._start_times: dict[str, float] = {}

    def start_operation(self, operation_id: str) -> None:
        """Start timing an operation."""
        self._start_times[operation_id] = time.time()

    def end_operation(self, operation_id: str) -> float | None:
        """End timing an operation and return duration."""
        start_time = self._start_times.pop(operation_id, None)
        if start_time:
            return (time.time() - start_time) * 1000  # Convert to ms
        return None

    def log_operation(
        self,
        entity_type: str,
        operation: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        entity_id: str | None = None,
        duration_ms: float | None = None,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a catalog operation event."""
        event = TelemetryEvent(
            event_type="catalog_operation",
            entity_type=entity_type,
            tenant_id=tenant_id,
            user_id=user_id,
            operation=operation,
            entity_id=entity_id,
            duration_ms=duration_ms,
            status=status,
            error=error,
            metadata=metadata,
        )

        self._events.append(event)
        self._write_event(event)

    def log_performance(
        self,
        entity_type: str,
        operation: str,
        duration_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a performance event."""
        event = TelemetryEvent(
            event_type="performance",
            entity_type=entity_type,
            operation=operation,
            duration_ms=duration_ms,
            status="success",
            metadata=metadata,
        )

        self._events.append(event)
        self._write_event(event)

    def log_error(
        self,
        entity_type: str,
        operation: str,
        error: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an error event."""
        event = TelemetryEvent(
            event_type="error",
            entity_type=entity_type,
            tenant_id=tenant_id,
            user_id=user_id,
            operation=operation,
            entity_id=entity_id,
            status="error",
            error=error,
            metadata=metadata,
        )

        self._events.append(event)
        self._write_event(event)

    def _write_event(self, event: TelemetryEvent) -> None:
        """Write event to logging system."""
        # In production, this would send to your telemetry system
        # For now, we'll just log to console
        event_data = event.to_dict()

        print(f"TELEMETRY: {json.dumps(event_data, indent=2)}")

        # You could also send to:
        # - Elasticsearch
        # - CloudWatch
        # - DataDog
        # - Custom telemetry service

    def get_metrics(self) -> dict[str, Any]:
        """Get summary metrics from collected events."""
        if not self._events:
            return {}

        # Calculate metrics
        total_operations = len([e for e in self._events if e.event_type == "catalog_operation"])
        successful_operations = len(
            [
                e
                for e in self._events
                if e.event_type == "catalog_operation" and e.status == "success"
            ]
        )
        error_operations = len(
            [e for e in self._events if e.event_type == "catalog_operation" and e.status == "error"]
        )

        # Performance metrics
        performance_events = [e for e in self._events if e.event_type == "performance"]
        avg_duration = 0
        if performance_events:
            avg_duration = sum(e.duration_ms for e in performance_events) / len(performance_events)

        # Entity breakdown
        entity_counts = {}
        for event in self._events:
            entity_type = event.entity_type
            if entity_type not in entity_counts:
                entity_counts[entity_type] = {"operations": 0, "errors": 0}
            entity_counts[entity_type]["operations"] += 1
            if event.status == "error":
                entity_counts[entity_type]["errors"] += 1

        return {
            "service_name": self.service_name,
            "total_events": len(self._events),
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "error_operations": error_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "avg_operation_duration_ms": avg_duration,
            "entity_breakdown": entity_counts,
            "time_range": {
                "start": min(e.timestamp for e in self._events),
                "end": max(e.timestamp for e in self._events),
            },
        }


# Global telemetry instance
telemetry = CatalogTelemetry()


def extract_user_context(request: Request) -> dict[str, str]:
    """Extract user context from request for telemetry."""
    context = {}

    # Extract tenant_id
    if hasattr(request.state, "access_claims"):
        claims = getattr(request.state, "access_claims", {})
        if claims.get("tenant_id"):
            context["tenant_id"] = str(claims["tenant_id"])
        if claims.get("user_id"):
            context["user_id"] = str(claims["user_id"])

    # Extract session info
    if hasattr(request.state, "session"):
        session = getattr(request.state, "session", {})
        if session.get("tenant_user_id"):
            context["user_id"] = str(session["tenant_user_id"])

    return context


def telemetry_operation(entity_type: str, operation: str, include_duration: bool = True):
    """Decorator for automatic telemetry logging of catalog operations."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation_id = str(uuid.uuid4())
            telemetry.start_operation(operation_id)

            # Extract context
            request = None
            tenant_id = None
            user_id = None
            entity_id = None

            # Find request in args/kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                elif key in ["tenant_id", "user_id", "id", "entity_id"]:
                    if key == "id" or key == "entity_id":
                        entity_id = str(value) if value else None
                    else:
                        locals()[key] = str(value) if value else None

            if request:
                context = extract_user_context(request)
                tenant_id = context.get("tenant_id")
                user_id = context.get("user_id")

            # Execute function
            try:
                result = func(*args, **kwargs)

                # Log successful operation
                duration_ms = telemetry.end_operation(operation_id) if include_duration else None
                telemetry.log_operation(
                    entity_type=entity_type,
                    operation=operation,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    entity_id=entity_id,
                    duration_ms=duration_ms,
                    status="success",
                )

                return result

            except Exception as e:
                # Log error
                duration_ms = telemetry.end_operation(operation_id) if include_duration else None
                telemetry.log_error(
                    entity_type=entity_type,
                    operation=operation,
                    error=str(e),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    entity_id=entity_id,
                )
                raise

        return wrapper

    return decorator


@contextmanager
def catalog_operation_context(
    entity_type: str, operation: str, tenant_id: str | None = None, user_id: str | None = None
):
    """Context manager for catalog operations with automatic telemetry."""
    operation_id = str(uuid.uuid4())
    telemetry.start_operation(operation_id)

    try:
        yield telemetry
    except Exception as e:
        telemetry.log_error(
            entity_type=entity_type,
            operation=operation,
            error=str(e),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        raise
    finally:
        duration_ms = telemetry.end_operation(operation_id)
        telemetry.log_operation(
            entity_type=entity_type,
            operation=operation,
            tenant_id=tenant_id,
            user_id=user_id,
            duration_ms=duration_ms,
            status="success",
        )


# Example usage:
#
# @telemetry_operation(entity_type="BusinessType", operation="create")
# def create_business_type(request: Request, business_type_data: dict, db: Session):
#     # Function logic here
#     business_type = BusinessType(**business_type_data)
#     db.add(business_type)
#     db.commit()
#     return business_type
#
# @telemetry_operation(entity_type="BusinessType", operation="list")
# def list_business_types(request: Request, db: Session):
#     # Function logic here
#     query = db.query(BusinessType)
#     return query.all()
#
# # Context manager usage:
# def update_business_type(request: Request, business_type_id: str, data: dict, db: Session):
#     context = extract_user_context(request)
#
#     with catalog_operation_context(
#         entity_type="BusinessType",
#         operation="update",
#         tenant_id=context.get('tenant_id'),
#         user_id=context.get('user_id')
#     ):
#         # Function logic here
#         business_type = db.query(BusinessType).filter(
#             BusinessType.id == business_type_id
#         ).first()
#         if business_type:
#             for key, value in data.items():
#                 setattr(business_type, key, value)
#             db.commit()
#             return business_type
#         else:
#             raise ValueError("BusinessType not found")
