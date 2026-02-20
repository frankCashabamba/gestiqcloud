import os
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

router = APIRouter(prefix="/imports", tags=["imports-analysis"])


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    hinted_doc_type: str | None = Query(None),
    show_explanation: bool = Query(False),
):
    from app.modules.imports.application.smart_router import SmartRouter

    router_instance = SmartRouter()

    suffix = Path(file.filename or "upload.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        parse_result = router_instance.ingest(temp_path, hinted_doc_type=hinted_doc_type)
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    if not parse_result.items:
        return {
            "status": "empty",
            "doc_type": parse_result.doc_type.value,
            "errors": parse_result.parse_errors,
        }

    classify_result = router_instance.classify(
        parse_result.items[0] if parse_result.items else {}, parse_result.doc_type.value
    )

    response = {
        "doc_type": classify_result.doc_type.value,
        "confidence": classify_result.confidence.value,
        "confidence_score": classify_result.confidence_score,
        "errors": parse_result.parse_errors,
    }

    if show_explanation:
        response["all_scores"] = classify_result.metadata.get("all_scores", {})
        response["fingerprint"] = classify_result.fingerprint

    return response


@router.post("/batch/{batch_id}/classify")
async def classify_batch_items(batch_id: UUID):
    from app.modules.imports.application.ingest_service import IngestService

    service = IngestService()

    batch_items = service.get_batch_items(str(batch_id))

    if not batch_items:
        return {"error": "batch_not_found"}

    from app.modules.imports.application.smart_router import SmartRouter

    router_instance = SmartRouter()

    results = []
    for item in batch_items:
        if item["raw"]:
            classify_result = router_instance.classify(item["raw"], item.get("doc_type", "generic"))
            results.append(
                {
                    "item_id": item["id"],
                    "doc_type": classify_result.doc_type.value,
                    "confidence": classify_result.confidence.value,
                    "confidence_score": classify_result.confidence_score,
                }
            )

            service.update_item_after_classify(item["id"], classify_result)

    return {
        "batch_id": str(batch_id),
        "classified_count": len(results),
        "results": results,
    }


@router.post("/batch/{batch_id}/map")
async def map_batch_items(batch_id: UUID):
    from app.modules.imports.application.ingest_service import IngestService
    from app.modules.imports.application.smart_router import SmartRouter

    service = IngestService()
    router_instance = SmartRouter()

    batch_items = service.get_batch_items(str(batch_id))

    if not batch_items:
        return {"error": "batch_not_found"}

    results = []
    for item in batch_items:
        if item["raw"]:
            doc_type_str = item.get("classified_doc_type", "generic")
            from app.modules.imports.domain.interfaces import DocType

            try:
                doc_type = DocType(doc_type_str)
            except ValueError:
                doc_type = DocType.GENERIC

            map_result = router_instance.map(item["raw"], doc_type)
            results.append(
                {
                    "item_id": item["id"],
                    "mapped_fields": map_result.mapped_fields,
                    "unmapped_fields": map_result.unmapped_fields,
                    "validation_errors": map_result.validation_errors,
                }
            )

            service.update_item_after_map(item["id"], map_result)

    return {
        "batch_id": str(batch_id),
        "mapped_count": len(results),
        "results": results,
    }


@router.post("/batch/{batch_id}/promote")
async def promote_batch_items(batch_id: UUID, item_ids: list[str] | None = None):
    from app.modules.imports.application.ingest_service import IngestService
    from app.modules.imports.application.smart_router import SmartRouter

    service = IngestService()
    router_instance = SmartRouter()

    batch_items = service.get_batch_items(str(batch_id))

    if not batch_items:
        return {"error": "batch_not_found"}

    promoted_count = 0
    needs_review_count = 0
    failed_count = 0

    for item in batch_items:
        if item_ids and item["id"] not in item_ids:
            continue

        if item.get("classified_doc_type"):
            from app.modules.imports.domain.interfaces import AnalyzeResult, DocType

            doc_type = DocType(item["classified_doc_type"])
            analyze_result = AnalyzeResult(
                doc_type=doc_type,
                confidence=AnalyzeResult.confidence,
                confidence_score=item.get("classification_confidence", 0.0),
                raw_data=item.get("raw", {}),
                errors=[],
                metadata={},
            )

            from app.modules.imports.domain.interfaces import MappingResult

            mapping_result = MappingResult(
                normalized_data=item.get("normalized", {}),
                doc_type=doc_type,
                mapped_fields=item.get("mapped_fields", {}),
                unmapped_fields=item.get("unmapped_fields", []),
                validation_errors=item.get("validation_errors", []),
                warnings=item.get("warnings", []),
            )

            can_promote, reason = router_instance.promote(analyze_result, mapping_result)

            if can_promote:
                promoted_count += 1
                service.update_item_after_classify(
                    item["id"],
                    AnalyzeResult(
                        doc_type=doc_type,
                        confidence=analyze_result.confidence,
                        confidence_score=analyze_result.confidence_score,
                        raw_data=analyze_result.raw_data,
                        errors=analyze_result.errors,
                        metadata=analyze_result.metadata,
                    ),
                )
            elif reason == "needs_review":
                needs_review_count += 1
                service.set_item_needs_review(item["id"], reason)
            else:
                failed_count += 1

    service.update_batch_after_promote(str(batch_id), promoted_count, failed_count)

    return {
        "batch_id": str(batch_id),
        "promoted": promoted_count,
        "needs_review": needs_review_count,
        "failed": failed_count,
    }
