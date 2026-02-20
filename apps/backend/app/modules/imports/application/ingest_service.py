from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

from app.modules.imports.domain.interfaces import (
    ItemStatus,
    ParseResult,
    DocType,
)


class BatchStatus(str, Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    CLASSIFIED = "classified"
    MAPPED = "mapped"
    PROMOTED = "promoted"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class IngestService:
    def __init__(self):
        self.batches: dict[str, dict] = {}
        self.items: dict[str, dict] = {}

    def create_batch(
        self,
        tenant_id: UUID,
        source_type: str,
        origin: str,
        file_key: str = None,
        mapping_id: UUID = None,
    ) -> str:
        batch_id = str(uuid4())
        self.batches[batch_id] = {
            "id": batch_id,
            "tenant_id": str(tenant_id),
            "source_type": source_type,
            "origin": origin,
            "file_key": file_key,
            "mapping_id": str(mapping_id) if mapping_id else None,
            "status": BatchStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "items": [],
            "classification_confidence": None,
            "suggested_parser": None,
            "ai_enhanced": False,
            "ai_provider": None,
        }
        return batch_id

    def ingest_parse_result(
        self, batch_id: str, parse_result: ParseResult
    ) -> list[str]:
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")

        batch = self.batches[batch_id]
        item_ids = []

        for idx, item_data in enumerate(parse_result.items):
            item_id = str(uuid4())
            self.items[item_id] = {
                "id": item_id,
                "batch_id": batch_id,
                "idx": idx,
                "status": ItemStatus.PENDING.value,
                "raw": item_data,
                "normalized": None,
                "errors": parse_result.parse_errors,
                "promoted_to": None,
                "promoted_id": None,
                "promoted_at": None,
                "lineage": [],
                "last_correction": None,
                "created_at": datetime.utcnow().isoformat(),
            }
            item_ids.append(item_id)
            batch["items"].append(item_id)

        batch["status"] = BatchStatus.INGESTED.value
        return item_ids

    def update_item_after_classify(
        self, item_id: str, classify_result
    ) -> None:
        if item_id not in self.items:
            raise ValueError(f"Item {item_id} not found")

        item = self.items[item_id]
        item["classified_doc_type"] = classify_result.doc_type.value
        item["classification_confidence"] = classify_result.confidence_score
        item["classification_metadata"] = classify_result.metadata

    def update_item_after_map(
        self, item_id: str, map_result
    ) -> None:
        if item_id not in self.items:
            raise ValueError(f"Item {item_id} not found")

        item = self.items[item_id]
        item["normalized"] = map_result.normalized_data
        item["mapped_fields"] = map_result.mapped_fields
        item["unmapped_fields"] = map_result.unmapped_fields
        item["validation_errors"] = map_result.validation_errors
        item["warnings"] = map_result.warnings
        item["status"] = ItemStatus.VALIDATED.value

    def update_batch_after_promote(
        self, batch_id: str, promoted_count: int, failed_count: int
    ) -> None:
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")

        batch = self.batches[batch_id]
        if promoted_count > 0:
            batch["status"] = BatchStatus.PROMOTED.value
        elif failed_count > 0:
            batch["status"] = BatchStatus.NEEDS_REVIEW.value

    def set_item_needs_review(self, item_id: str, reason: str) -> None:
        if item_id not in self.items:
            raise ValueError(f"Item {item_id} not found")

        self.items[item_id]["status"] = ItemStatus.NEEDS_REVIEW.value
        self.items[item_id]["review_reason"] = reason

    def record_correction(
        self,
        item_id: str,
        field: str,
        old_value,
        new_value,
    ) -> None:
        if item_id not in self.items:
            raise ValueError(f"Item {item_id} not found")

        item = self.items[item_id]
        if item["last_correction"] is None:
            item["last_correction"] = {}

        item["last_correction"][field] = {
            "old": old_value,
            "new": new_value,
            "timestamp": datetime.utcnow().isoformat(),
        }

        item["lineage"].append({
            "operation": "correction",
            "field": field,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_batch_items(self, batch_id: str) -> list[dict]:
        if batch_id not in self.batches:
            return []

        batch = self.batches[batch_id]
        return [self.items[item_id] for item_id in batch["items"] if item_id in self.items]

    def get_batch_status(self, batch_id: str) -> dict:
        if batch_id not in self.batches:
            return {}

        batch = self.batches[batch_id]
        items = self.get_batch_items(batch_id)

        status_counts = {}
        for item in items:
            status = item["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "total_items": len(items),
            "item_statuses": status_counts,
            "created_at": batch["created_at"],
        }
