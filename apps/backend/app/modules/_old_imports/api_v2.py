from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.modules.imports.routes.analysis import router as analysis_router
from app.modules.imports.routes.country import router as country_router
from app.modules.imports.routes.learning import router as learning_router

router = APIRouter(prefix="/api/v2/imports", tags=["imports-v2"])

router.include_router(analysis_router)
router.include_router(country_router)
router.include_router(learning_router)


@router.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0"}


@router.post("/ingest/batch")
async def create_ingest_batch(
    source_type: str = Query(...),
    origin: str = Query(...),
    file_key: str | None = Query(None),
):
    from app.modules.imports.application.ingest_service import IngestService

    service = IngestService()

    batch_id = service.create_batch(
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        source_type=source_type,
        origin=origin,
        file_key=file_key,
    )

    return {
        "batch_id": batch_id,
        "status": "pending",
    }


@router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: UUID):
    from app.modules.imports.application.ingest_service import IngestService

    service = IngestService()

    status = service.get_batch_status(str(batch_id))

    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")

    return status


@router.post("/batch/{batch_id}/ingest")
async def ingest_file_to_batch(
    batch_id: UUID,
    file: UploadFile = File(...),
    hinted_doc_type: str | None = Query(None),
):
    import tempfile

    from app.modules.imports.application.ingest_service import IngestService
    from app.modules.imports.application.smart_router import SmartRouter

    try:
        service = IngestService()
        router_instance = SmartRouter()

        with tempfile.NamedTemporaryFile(suffix=file.filename, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        parse_result = router_instance.ingest(tmp_path, hinted_doc_type=hinted_doc_type)

        item_ids = service.ingest_parse_result(str(batch_id), parse_result)

        return {
            "batch_id": str(batch_id),
            "items_ingested": len(item_ids),
            "item_ids": item_ids,
            "parse_errors": parse_result.parse_errors,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch/{batch_id}/process")
async def process_batch(
    batch_id: UUID,
    classify: bool = Query(True),
    map_fields: bool = Query(True),
):
    from app.modules.imports.application.ingest_service import IngestService
    from app.modules.imports.application.smart_router import SmartRouter

    service = IngestService()
    router_instance = SmartRouter()

    batch_items = service.get_batch_items(str(batch_id))

    if not batch_items:
        raise HTTPException(status_code=404, detail="Batch not found")

    results = {
        "batch_id": str(batch_id),
        "classified": 0,
        "mapped": 0,
    }

    for item in batch_items:
        if classify and item["raw"]:
            classify_result = router_instance.classify(item["raw"], item.get("doc_type", "generic"))
            service.update_item_after_classify(item["id"], classify_result)
            results["classified"] += 1

        if map_fields and item["raw"]:
            from app.modules.imports.domain.interfaces import DocType

            doc_type_str = item.get("classified_doc_type", "generic")
            try:
                doc_type = DocType(doc_type_str)
            except ValueError:
                doc_type = DocType.GENERIC

            map_result = router_instance.map(item["raw"], doc_type)
            service.update_item_after_map(item["id"], map_result)
            results["mapped"] += 1

    return results


@router.get("/stats")
async def get_global_stats():
    from app.modules.imports.infrastructure.learning_store import InMemoryLearningStore

    store = InMemoryLearningStore()

    return {
        "misclassifications": store.get_misclassification_stats(),
        "fingerprints_tracked": len(store.get_fingerprint_dataset()),
    }
