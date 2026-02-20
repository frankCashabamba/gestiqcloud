"""
Complete audit trail for import operations.
Tracks: who imported, parser version, rules applied, manual changes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class AuditEventType(str, Enum):
    """Type of audit event."""

    IMPORT_STARTED = "import_started"
    FILE_UPLOADED = "file_uploaded"
    FILE_ANALYZED = "file_analyzed"
    FILE_PARSED = "file_parsed"
    ITEM_CREATED = "item_created"
    ITEM_VALIDATED = "item_validated"
    ITEM_CORRECTED = "item_corrected"
    ITEM_APPROVED = "item_approved"
    ITEM_PROMOTED = "item_promoted"
    BATCH_COMPLETED = "batch_completed"
    BATCH_FAILED = "batch_failed"


@dataclass
class AuditEvent:
    """Single audit event."""

    event_type: AuditEventType
    tenant_id: UUID
    user_id: UUID | None = None
    batch_id: UUID | None = None
    item_id: UUID | None = None

    # Event details
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)

    # Context for traceability
    parser_version: str | None = None
    schema_version: str | None = None
    rules_applied: list[str] = field(default_factory=list)

    # Changes
    old_value: Any | None = None
    new_value: Any | None = None

    # Status
    success: bool = True
    error_message: str | None = None


@dataclass
class AuditTrail:
    """Complete audit trail for a batch/import."""

    id: UUID
    tenant_id: UUID
    batch_id: UUID
    events: list[AuditEvent] = field(default_factory=list)

    # Summary
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    total_items: int = 0
    promoted_items: int = 0
    failed_items: int = 0

    def add_event(self, event: AuditEvent):
        """Add event to audit trail."""
        self.events.append(event)

    def get_events_for_item(self, item_id: UUID) -> list[AuditEvent]:
        """Get all events for specific item."""
        return [e for e in self.events if e.item_id == item_id]

    def get_events_by_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        """Get all events of specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_timeline(self) -> list[dict[str, Any]]:
        """Get chronological timeline of all events."""
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "event": e.event_type.value,
                "user_id": str(e.user_id) if e.user_id else None,
                "item_id": str(e.item_id) if e.item_id else None,
                "details": e.details,
            }
            for e in sorted(self.events, key=lambda e: e.timestamp)
        ]

    def get_changes_for_field(self, item_id: UUID, field: str) -> list[dict]:
        """Get all changes for a specific field of an item."""
        changes = []
        for event in self.get_events_for_item(item_id):
            if event.event_type == AuditEventType.ITEM_CORRECTED:
                if event.details.get("field") == field:
                    changes.append(
                        {
                            "timestamp": event.timestamp.isoformat(),
                            "old_value": event.old_value,
                            "new_value": event.new_value,
                            "user_id": str(event.user_id) if event.user_id else None,
                            "reason": event.details.get("reason"),
                        }
                    )
        return changes


class AuditLogger:
    """Logs all import operations for audit trail."""

    def __init__(self):
        # In-memory storage (will be persisted to DB)
        self.trails = {}

    def create_trail(self, tenant_id: UUID, batch_id: UUID) -> AuditTrail:
        """Create new audit trail for batch."""
        trail = AuditTrail(
            id=UUID(int=0),  # Will be set by DB
            tenant_id=tenant_id,
            batch_id=batch_id,
        )
        self.trails[batch_id] = trail
        return trail

    def log_import_started(
        self,
        trail: AuditTrail,
        filename: str,
        user_id: UUID | None = None,
    ):
        """Log import started."""
        event = AuditEvent(
            event_type=AuditEventType.IMPORT_STARTED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            user_id=user_id,
            details={
                "filename": filename,
            },
        )
        trail.add_event(event)

    def log_file_analyzed(
        self,
        trail: AuditTrail,
        parser: str,
        doc_type: str,
        confidence: float,
        headers_count: int,
        rows_count: int,
    ):
        """Log file analysis."""
        event = AuditEvent(
            event_type=AuditEventType.FILE_ANALYZED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            parser_version="1.0",  # Should come from parser
            details={
                "parser": parser,
                "doc_type": doc_type,
                "confidence": confidence,
                "headers_count": headers_count,
                "rows_count": rows_count,
            },
        )
        trail.add_event(event)

    def log_item_validated(
        self,
        trail: AuditTrail,
        item_id: UUID,
        is_valid: bool,
        error_count: int = 0,
    ):
        """Log item validation."""
        event = AuditEvent(
            event_type=AuditEventType.ITEM_VALIDATED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            item_id=item_id,
            success=is_valid,
            details={
                "is_valid": is_valid,
                "error_count": error_count,
            },
        )
        trail.add_event(event)

    def log_item_correction(
        self,
        trail: AuditTrail,
        item_id: UUID,
        field: str,
        old_value: Any,
        new_value: Any,
        user_id: UUID,
        reason: str | None = None,
    ):
        """Log manual item correction."""
        event = AuditEvent(
            event_type=AuditEventType.ITEM_CORRECTED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            item_id=item_id,
            user_id=user_id,
            old_value=old_value,
            new_value=new_value,
            details={
                "field": field,
                "reason": reason,
            },
        )
        trail.add_event(event)

    def log_item_promoted(
        self,
        trail: AuditTrail,
        item_id: UUID,
        promoted_to: str,
        promoted_id: UUID,
        user_id: UUID | None = None,
    ):
        """Log item promotion to next stage."""
        event = AuditEvent(
            event_type=AuditEventType.ITEM_PROMOTED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            item_id=item_id,
            user_id=user_id,
            details={
                "promoted_to": promoted_to,
                "promoted_id": str(promoted_id),
            },
        )
        trail.add_event(event)
        trail.promoted_items += 1

    def log_batch_completed(
        self,
        trail: AuditTrail,
        total_items: int,
        promoted_count: int,
    ):
        """Log batch completion."""
        event = AuditEvent(
            event_type=AuditEventType.BATCH_COMPLETED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            details={
                "total_items": total_items,
                "promoted_items": promoted_count,
                "success_rate": promoted_count / max(total_items, 1),
            },
        )
        trail.add_event(event)
        trail.completed_at = datetime.utcnow()
        trail.total_items = total_items
        trail.promoted_items = promoted_count

    def log_batch_failed(
        self,
        trail: AuditTrail,
        error: str,
    ):
        """Log batch failure."""
        event = AuditEvent(
            event_type=AuditEventType.BATCH_FAILED,
            tenant_id=trail.tenant_id,
            batch_id=trail.batch_id,
            success=False,
            error_message=error,
        )
        trail.add_event(event)
        trail.completed_at = datetime.utcnow()

    def get_trail(self, batch_id: UUID) -> AuditTrail | None:
        """Get audit trail for batch."""
        return self.trails.get(batch_id)

    def get_full_report(self, batch_id: UUID) -> dict[str, Any]:
        """Get complete audit report for batch."""
        trail = self.get_trail(batch_id)
        if not trail:
            return {}

        return {
            "batch_id": str(trail.batch_id),
            "tenant_id": str(trail.tenant_id),
            "created_at": trail.created_at.isoformat(),
            "completed_at": trail.completed_at.isoformat() if trail.completed_at else None,
            "summary": {
                "total_items": trail.total_items,
                "promoted_items": trail.promoted_items,
                "failed_items": trail.failed_items,
                "success_rate": trail.promoted_items / max(trail.total_items, 1),
            },
            "timeline": trail.get_timeline(),
            "corrections": self._get_all_corrections(trail),
        }

    def _get_all_corrections(self, trail: AuditTrail) -> dict[str, list]:
        """Get all manual corrections in audit trail."""
        corrections_by_item = {}
        for event in trail.get_events_by_type(AuditEventType.ITEM_CORRECTED):
            item_id = str(event.item_id)
            if item_id not in corrections_by_item:
                corrections_by_item[item_id] = []
            corrections_by_item[item_id].append(
                {
                    "field": event.details.get("field"),
                    "old_value": event.old_value,
                    "new_value": event.new_value,
                    "user_id": str(event.user_id) if event.user_id else None,
                    "timestamp": event.timestamp.isoformat(),
                }
            )
        return corrections_by_item


# Global audit logger
audit_logger = AuditLogger()
