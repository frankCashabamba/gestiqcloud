from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import Optional

router = APIRouter(prefix="/batch-migration", tags=["batch-migration"])


@router.post("/legacy/{old_batch_id}/migrate")
async def migrate_legacy_batch(old_batch_id: str):
    from app.modules.imports.application.ingest_service import IngestService

    service = IngestService()

    new_batch_id = service.create_batch(
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        source_type="generic",
        origin="legacy_migration",
        file_key=old_batch_id,
    )

    return {
        "old_batch_id": old_batch_id,
        "new_batch_id": new_batch_id,
        "status": "migrated",
    }


@router.get("/compatibility-check")
async def check_legacy_compatibility():
    return {
        "legacy_support": True,
        "auto_migration": True,
        "warning": "Legacy parsers will be wrapped in adapter interface",
    }


@router.post("/validate-format/{batch_id}")
async def validate_batch_format(batch_id: UUID):
    from app.modules.imports.application.ingest_service import IngestService

    service = IngestService()

    batch_items = service.get_batch_items(str(batch_id))

    if not batch_items:
        raise HTTPException(status_code=404, detail="Batch not found")

    issues = []

    for item in batch_items:
        if not item.get("raw"):
            issues.append(f"Item {item['id']} has empty raw data")

        if not item.get("status"):
            issues.append(f"Item {item['id']} has no status")

    return {
        "batch_id": str(batch_id),
        "valid": len(issues) == 0,
        "issues": issues,
    }
