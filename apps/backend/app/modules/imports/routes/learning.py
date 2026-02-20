from fastapi import APIRouter, HTTPException

from app.modules.imports.infrastructure.learning_store import InMemoryLearningStore

router = APIRouter(prefix="/learning", tags=["learning"])

learning_store = InMemoryLearningStore()


@router.post("/correction/{batch_id}/{item_idx}")
async def record_correction(
    batch_id: str,
    item_idx: int,
    original_doc_type: str,
    corrected_doc_type: str,
    confidence_was: float,
):
    from app.modules.imports.domain.interfaces import DocType

    try:
        original = DocType(original_doc_type)
        corrected = DocType(corrected_doc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid doc type")

    learning_store.record_correction(
        batch_id,
        item_idx,
        original,
        corrected,
        confidence_was,
    )

    return {
        "recorded": True,
        "batch_id": batch_id,
        "item_idx": item_idx,
    }


@router.get("/stats/misclassifications")
async def get_misclassification_stats():
    stats = learning_store.get_misclassification_stats()

    return {
        "misclassifications": stats,
        "total": sum(stats.values()),
    }


@router.get("/dataset/fingerprints")
async def get_fingerprint_dataset():
    dataset = learning_store.get_fingerprint_dataset()

    return {
        "count": len(dataset),
        "fingerprints": dataset,
    }


@router.get("/corrections/{batch_id}")
async def get_corrections_by_batch(batch_id: str):
    corrections = learning_store.get_corrections_by_batch(batch_id)

    return {
        "batch_id": batch_id,
        "corrections": corrections,
        "count": len(corrections),
    }


@router.post("/fingerprint")
async def record_fingerprint(
    fingerprint: str,
    doc_type: str,
    raw_data: dict,
):
    from app.modules.imports.domain.interfaces import DocType

    try:
        doc_type_enum = DocType(doc_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid doc type")

    learning_store.record_fingerprint(fingerprint, doc_type_enum, raw_data)

    return {
        "recorded": True,
        "fingerprint": fingerprint,
    }
