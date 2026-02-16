"""Posting Registry Service — Idempotency for imports"""
import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core.modelsimport import ImportResolution, PostingRegistry

logger = logging.getLogger(__name__)


class PostingService:
    """Handles idempotent posting of imported data to domain tables."""

    def __init__(self, db: Session):
        self.db = db

    def compute_posting_key(
        self,
        tenant_id: UUID,
        import_job_id: UUID,
        entity_type: str,
        normalized_data: dict[str, Any],
    ) -> str:
        """Compute a deterministic posting key from normalized data."""
        # Build a canonical representation for hashing
        key_parts = {
            "tenant_id": str(tenant_id),
            "import_job_id": str(import_job_id),
            "entity_type": entity_type,
        }
        # Include key fields based on entity type
        if entity_type == "invoice":
            for f in ("invoice_number", "vendor_name", "total", "invoice_date"):
                if f in normalized_data:
                    key_parts[f] = str(normalized_data[f])
        elif entity_type == "product":
            for f in ("sku", "name"):
                if f in normalized_data:
                    key_parts[f] = str(normalized_data[f])
        elif entity_type in ("expense", "bank_txn"):
            for f in ("date", "amount", "description", "reference"):
                if f in normalized_data:
                    key_parts[f] = str(normalized_data[f])
        elif entity_type == "sale_item":
            for f in ("date", "product_name_raw", "sold_qty", "unit_price"):
                if f in normalized_data:
                    key_parts[f] = str(normalized_data[f])
        else:
            # Generic: hash entire normalized data
            key_parts["data_hash"] = hashlib.sha256(
                json.dumps(normalized_data, sort_keys=True, default=str).encode()
            ).hexdigest()

        canonical = json.dumps(key_parts, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def check_and_register(
        self,
        tenant_id: UUID,
        import_job_id: UUID,
        posting_key: str,
        entity_type: str,
        entity_id: UUID | None = None,
    ) -> tuple[bool, PostingRegistry | None]:
        """
        Check if posting_key exists. If yes, return (True, existing_record).
        If not, register it and return (False, new_record).
        """
        existing = (
            self.db.query(PostingRegistry)
            .filter(
                PostingRegistry.tenant_id == tenant_id,
                PostingRegistry.posting_key == posting_key,
            )
            .first()
        )
        if existing:
            logger.info(
                "Posting key already exists: %s (entity: %s/%s)",
                posting_key[:16],
                existing.entity_type,
                existing.entity_id,
            )
            return True, existing

        record = PostingRegistry(
            tenant_id=tenant_id,
            import_job_id=import_job_id,
            posting_key=posting_key,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        self.db.add(record)
        self.db.flush()
        return False, record

    def is_duplicate(self, tenant_id: UUID, posting_key: str) -> bool:
        """Quick check if a posting key already exists."""
        return (
            self.db.query(PostingRegistry)
            .filter(
                PostingRegistry.tenant_id == tenant_id,
                PostingRegistry.posting_key == posting_key,
            )
            .first()
            is not None
        )

    # --- Import Resolution persistence ---

    def save_resolution(
        self,
        tenant_id: UUID,
        import_job_id: UUID,
        entity_type: str,
        raw_value: str,
        resolved_id: UUID | None = None,
        status: str = "pending",
        confidence: float | None = None,
        resolved_by: str | None = None,
    ) -> ImportResolution:
        """Persist an import resolution (mapping)."""
        # Check for existing
        existing = (
            self.db.query(ImportResolution)
            .filter(
                ImportResolution.import_job_id == import_job_id,
                ImportResolution.entity_type == entity_type,
                ImportResolution.raw_value == raw_value,
            )
            .first()
        )
        if existing:
            # Update
            if resolved_id is not None:
                existing.resolved_id = resolved_id
            if status:
                existing.status = status
            if confidence is not None:
                existing.confidence = confidence
            if resolved_by:
                existing.resolved_by = resolved_by
            self.db.flush()
            return existing

        resolution = ImportResolution(
            tenant_id=tenant_id,
            import_job_id=import_job_id,
            entity_type=entity_type,
            raw_value=raw_value,
            resolved_id=resolved_id,
            status=status,
            confidence=confidence,
            resolved_by=resolved_by,
        )
        self.db.add(resolution)
        self.db.flush()
        return resolution

    def get_resolutions(
        self,
        tenant_id: UUID,
        import_job_id: UUID,
    ) -> list[ImportResolution]:
        """Get all resolutions for an import job."""
        return (
            self.db.query(ImportResolution)
            .filter(
                ImportResolution.tenant_id == tenant_id,
                ImportResolution.import_job_id == import_job_id,
            )
            .all()
        )

    def find_previous_resolution(
        self,
        tenant_id: UUID,
        entity_type: str,
        raw_value: str,
    ) -> ImportResolution | None:
        """Find a previous resolution for the same raw_value (for suggestion reuse)."""
        return (
            self.db.query(ImportResolution)
            .filter(
                ImportResolution.tenant_id == tenant_id,
                ImportResolution.entity_type == entity_type,
                ImportResolution.raw_value == raw_value,
                ImportResolution.status == "resolved",
            )
            .order_by(ImportResolution.created_at.desc())
            .first()
        )
