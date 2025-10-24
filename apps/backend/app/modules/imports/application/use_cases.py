from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
import os
from fastapi import UploadFile  #

from sqlalchemy.orm import Session
import logging
from uuid import UUID, uuid4

from app.modules.imports.application.use_utils import apply_mapping
from app.modules.imports.application.status import ImportItemStatus, ImportBatchStatus
from app.modules.imports.domain.handlers import BankHandler, ExpenseHandler, InvoiceHandler
from app.modules.imports.infrastructure.repositories import ImportsRepository
from app.modules.imports.validators import validate_bank, validate_expenses, validate_invoices, validate_panaderia_diario
from app.models.core.modelsimport import (
    ImportBatch,
    ImportItem,
    ImportItemCorrection,
    ImportLineage,
    ImportAttachment,
)
from app.modules.imports.application.photo_utils import (
    exif_auto_orienta,
    guardar_adjunto_bytes,
    ocr_texto,
    parse_texto_factura,
    parse_texto_banco,
    parse_texto_recibo,
)

# --- helpers -----------------------------------------------------------------

def _to_uuid(v) -> UUID:
    return v if isinstance(v, UUID) else UUID(str(v))

def _idempotency_key(empresa_id: int | str, file_key: Optional[str], idx: int) -> str:
    base = f"{str(empresa_id)}:{file_key or ''}:{idx}"
    return hashlib.sha256(base.encode()).hexdigest()

def _validate_by_type(source_type: str, normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Feature flags simples vía env
    validate_currency = (os.getenv("IMPORTS_VALIDATE_CURRENCY", "true").lower() in ("1", "true", "yes"))
    # Activado por defecto: puede desactivarse con IMPORTS_REQUIRE_CATEGORIES=false
    require_categories = (os.getenv("IMPORTS_REQUIRE_CATEGORIES", "true").lower() in ("1", "true", "yes"))

    if source_type == "invoices":
        return validate_invoices(normalized, enable_currency_rule=validate_currency)
    if source_type == "bank":
        return validate_bank(normalized)
    if source_type in ("expenses", "receipts"):
        return validate_expenses(normalized, require_categories=require_categories)
    if source_type == "panaderia_diario":
        return validate_panaderia_diario(normalized)
    return []

def _dedupe_hash(source_type: str, data: Dict[str, Any], *, keys: Optional[List[str]] = None) -> str:
    def g(*ks):
        for k in ks:
            if k in data and data[k] is not None:
                return str(data[k])
        return ""

    if keys:
        parts = [str(data.get(k) or "") for k in keys]
    elif source_type == "invoices":
        parts = [
            g("issuer_tax_id", "issuer", "supplier_tax_id"),
            g("invoice_number", "invoice", "number"),
            g("invoice_date", "date"),
            g("total_amount", "total"),
        ]
    elif source_type == "bank":
        parts = [
            g("statement_id"),
            g("entry_ref", "reference"),
            g("transaction_date", "date"),
            g("amount", "importe"),
            g("description", "concept", "concepto"),
        ]
    elif source_type == "panaderia_diario":
        parts = [
            g("fecha", "date"),
            g("producto", "product"),
            g("cantidad_producida", "cantidad", "qty"),
        ]
    else:  # expenses/receipts
        parts = [
            g("expense_date", "date"),
            g("amount", "importe"),
            g("category", "categoria"),
            g("description", "concept", "concepto"),
        ]

    payload = "|".join(parts)
    return hashlib.sha256(payload.encode()).hexdigest()


def _merge_src(raw: Dict[str, Any] | None, normalized: Dict[str, Any] | None) -> Dict[str, Any]:
    """Devuelve raw sobreescrito por normalized cuando exista."""
    raw = raw or {}
    normalized = normalized or {}
    if not normalized:
        return raw
    merged = dict(raw)
    merged.update(normalized)
    return merged

# --- use cases ---------------------------------------------------------------

def create_batch(db: Session, empresa_id: int, user_id: Any, dto: Dict[str, Any]) -> ImportBatch:
    # created_by se guarda como String (UUID en string si es posible)
    try:
        created_by_uuid = user_id if isinstance(user_id, UUID) else _to_uuid(user_id)
        created_by = str(created_by_uuid)
    except Exception:
        created_by = str(uuid4())

    batch = ImportBatch(
        empresa_id=empresa_id,                 # <-- INT (como en tus modelos)
        source_type=dto["source_type"],
        origin=dto.get("origin") or "api",
        file_key=dto.get("file_key"),
        mapping_id=dto.get("mapping_id"),     # esto es UUID o None según tu modelo
        status="PENDING",
        created_by=created_by,                # columna String
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch

def ingest_rows(
    db: Session,
    empresa_id: int,
    batch: ImportBatch,
    rows: Iterable[Dict[str, Any]],
    mappings: Optional[Dict[str, str]] = None,
    transforms: Optional[Dict[str, Any]] = None,
    defaults: Optional[Dict[str, Any]] = None,
    dedupe_keys: Optional[List[str]] = None,
):
    t0 = datetime.utcnow()
    repo = ImportsRepository()
    created: List[Dict[str, Any]] = []
    for idx, raw in enumerate(rows):
        normalized = apply_mapping(raw, mappings, transforms, defaults) if mappings else None
        src = _merge_src(raw, normalized)
        errors = _validate_by_type(batch.source_type, src)
        status = ImportItemStatus.OK if not errors else ImportItemStatus.ERROR_VALIDATION
        dedupe = _dedupe_hash(batch.source_type, src, keys=dedupe_keys)
        idem = _idempotency_key(empresa_id, batch.file_key, idx)
        created.append({
            "idx": idx,
            "raw": raw,
            "normalized": normalized,
            "status": status,
            "errors": errors,
            "idempotency_key": idem,
            "dedupe_hash": dedupe,
        })
    if created:
        repo.bulk_add_items(db, empresa_id, batch.id, created)  # empresa_id INT
        batch.status = ImportBatchStatus.READY
        db.add(batch)
        db.commit()
        db.refresh(batch)
    t1 = datetime.utcnow()
    try:
        logging.getLogger("imports").info(
            "ingest_rows",
            extra={
                "tenant": empresa_id,
                "batch_id": str(batch.id),
                "items_total": len(created),
                "t_parse_ms": int((t1 - t0).total_seconds() * 1000),
            },
        )
    except Exception:
        pass
    return repo.list_items(db, empresa_id, batch.id)

def revalidate_batch(db: Session, empresa_id: int, batch_id: UUID | str):
    batch_uuid = _to_uuid(batch_id)
    repo = ImportsRepository()
    batch = repo.get_batch(db, empresa_id, batch_uuid)   # empresa_id INT, batch_id UUID
    if not batch:
        return []
    items = repo.list_items(db, empresa_id, batch_uuid)
    for it in items:
        src = _merge_src(it.raw, it.normalized)
        errors = _validate_by_type(batch.source_type, src)
        it.errors = errors
        it.status = ImportItemStatus.OK if not errors else ImportItemStatus.ERROR_VALIDATION
        db.add(it)
    db.commit()
    out = repo.list_items(db, empresa_id, batch_uuid)
    # Update batch status: VALIDATED if all OK, PARTIAL if mixed, READY if no items
    total = len(out)
    oks = sum(1 for x in out if x.status == ImportItemStatus.OK)
    errs = sum(1 for x in out if x.status == ImportItemStatus.ERROR_VALIDATION)
    if total > 0:
        if errs == 0 and oks == total:
            batch.status = ImportBatchStatus.VALIDATED
        elif oks > 0 and errs > 0:
            batch.status = ImportBatchStatus.PARTIAL
        else:
            batch.status = ImportBatchStatus.READY
        db.add(batch)
        db.commit()
    try:
        logging.getLogger("imports").info(
            "revalidate_batch",
            extra={
                "tenant": empresa_id,
                "batch_id": str(batch_uuid),
                "items_total": len(out),
                "items_ok": sum(1 for x in out if x.status == "OK"),
                "items_error": sum(1 for x in out if x.status and x.status.startswith("ERROR")),
            },
        )
    except Exception:
        pass
    return out

def patch_item(db: Session, empresa_id: int, user_id: Any, batch_id, item_id, field: str, value: Any):
    batch_uuid = _to_uuid(batch_id)
    item_uuid  = _to_uuid(item_id)

    repo = ImportsRepository()
    batch = repo.get_batch(db, empresa_id, batch_uuid)
    if not batch:
        return None

    from sqlalchemy import and_
    it = (
        db.query(ImportItem)
        .join(ImportBatch, ImportItem.batch_id == ImportBatch.id)
        .filter(and_(ImportItem.id == item_uuid, ImportBatch.empresa_id == empresa_id))
        .first()
    )
    if not it:
        return None

    # 👇 CLAVE: partir de todos los campos disponibles
    base = it.normalized or it.raw or {}
    normalized = dict(base)
    old_value = normalized.get(field)
    normalized[field] = value
    it.normalized = normalized

    # revalidar con el payload completo ya actualizado
    src = _merge_src(it.raw, it.normalized)
    errors = _validate_by_type(batch.source_type, src)
    it.errors = errors
    it.status = "OK" if not errors else "ERROR_VALIDATION"
    db.add(it)

    # corrección (user_id → UUID si puedes; si no, genera uno)
    try:
        uid = user_id if isinstance(user_id, UUID) else _to_uuid(user_id)
    except Exception:
        uid = uuid4()

    corr = ImportItemCorrection(
        empresa_id=empresa_id,
        item_id=item_uuid,
        user_id=uid,
        field=field,
        old_value=old_value,
        new_value=value,
    )
    db.add(corr)
    db.commit()
    db.refresh(it)
    return it

def promote_batch(db: Session, empresa_id: int, batch_id):
    batch_uuid = _to_uuid(batch_id)

    repo = ImportsRepository()
    batch = repo.get_batch(db, empresa_id, batch_uuid)
    if not batch:
        return {"created": 0, "skipped": 0, "failed": 0}

    # Consider all items; we'll count already promoted as skipped to make idempotency visible
    items = repo.list_items(db, empresa_id, batch_uuid)
    created = skipped = failed = 0
    handler = {
        "invoices": InvoiceHandler,
        "bank": BankHandler,
        "receipts": ExpenseHandler,
        "expenses": ExpenseHandler,
    }.get(batch.source_type, ExpenseHandler)

    t0 = datetime.utcnow()
    promoted_hashes: set[str] = set()
    for it in items:
        # Already promoted: count as skipped (idempotent)
        if it.status == ImportItemStatus.PROMOTED:
            skipped += 1
            continue
        # Only attempt to promote valid items
        if it.status != ImportItemStatus.OK:
            continue
        try:
            if it.dedupe_hash and (repo.exists_promoted_hash(db, empresa_id, it.dedupe_hash) or it.dedupe_hash in promoted_hashes):
                skipped += 1
                continue
            res = handler.promote(it.normalized or it.raw or {}, it.promoted_id)
            if res.skipped:
                skipped += 1
                continue
            it.promoted_to = batch.source_type
            it.promoted_id = None
            it.promoted_at = datetime.utcnow()
            it.status = ImportItemStatus.PROMOTED
            db.add(it)
            if it.dedupe_hash:
                promoted_hashes.add(it.dedupe_hash)

            lineage = ImportLineage(
                empresa_id=empresa_id,   # INT
                item_id=it.id,           # UUID
                promoted_to=batch.source_type,
                promoted_ref=res.domain_id or "",
            )
            db.add(lineage)
            created += 1
        except Exception:
            it.status = ImportItemStatus.ERROR_PROMOTION
            db.add(it)
            failed += 1
    db.commit()
    t1 = datetime.utcnow()
    try:
        logging.getLogger("imports").info(
            "promote_batch",
            extra={
                "tenant": empresa_id,
                "batch_id": str(batch_uuid),
                "items_total": len(items),
                "items_ok": created,
                "items_error": failed,
                "t_promote_ms": int((t1 - t0).total_seconds() * 1000),
            },
        )
    except Exception:
        pass
    return {"created": created, "skipped": skipped, "failed": failed}


def _detectar_tipo_por_texto(txt: str) -> str:
    t = txt.lower()
    if "iban" in t or "saldo" in t or "transferencia" in t: return "bank"
    if "factura" in t or "n° factura" in t or "invoice" in t: return "invoices"
    return "receipts"

def ingest_photo(db: Session, empresa_id: str, user_id: str, batch: ImportBatch, file: UploadFile) -> ImportItem:
    # 1) leer bytes y normalizar orientación
    content = file.file.read()
    content = exif_auto_orienta(content)

    # 2) guardar adjunto (devuelve file_key y sha256)
    file_key, sha256 = guardar_adjunto_bytes(empresa_id, content, filename=file.filename or "foto.jpg")

    # 3) OCR
    texto = ocr_texto(content)  # devuelve str

    # 4) detectar tipo y extraer campos
    tipo = _detectar_tipo_por_texto(texto)
    if tipo == "invoices":
        raw = parse_texto_factura(texto)
    elif tipo == "bank":
        raw = parse_texto_banco(texto)
    else:
        raw = parse_texto_recibo(texto)

    # 5) mapping (si el batch tiene mapping asociado) → normalized
    normalized = apply_mapping(raw, mappings={}, transforms={}, defaults={})  # si usas ImportMapping, pásalo aquí

    # 6) crear item + adjunto
    idx = (db.query(ImportItem).filter(ImportItem.batch_id==batch.id).count() or 0) + 1
    item = ImportItem(
        batch_id=batch.id, idx=idx, raw=raw, normalized=normalized,
        idempotency_key=_idempotency_key(empresa_id, batch.file_key or file_key, idx)
    )
    src = _merge_src(item.raw, item.normalized)
    errors = _validate_by_type(batch.source_type, src)
    item.errors = errors
    item.status = "OK" if not errors else "ERROR_VALIDATION"
    db.add(item); db.flush()

    att = ImportAttachment(item_id=item.id, file_key=file_key, kind="photo", sha256=sha256, ocr_text=texto)
    db.add(att); db.commit(); db.refresh(item)
    return item

def attach_photo_and_reocr(db: Session, empresa_id: str, user_id: str, item: ImportItem, file: UploadFile) -> ImportItem:
    content = file.file.read()
    content = exif_auto_orienta(content)
    file_key, sha256 = guardar_adjunto_bytes(empresa_id, content, filename=file.filename or "foto.jpg")
    texto = ocr_texto(content)

    # Re-extraer valores "inteligentes" (NO pisa raw original; añade sugerencias)
    tipo = item.batch.source_type or _detectar_tipo_por_texto(texto)
    if tipo == "invoices":
        suger = parse_texto_factura(texto)
    elif tipo == "bank":
        suger = parse_texto_banco(texto)
    else:
        suger = parse_texto_recibo(texto)

    # **No sobrescribas**: aplica sugerencias como parches si los campos están vacíos
    norm = dict(item.normalized or {})
    for k, v in suger.items():
        if k not in norm or norm[k] in (None, "", 0):
            norm[k] = v
    item.normalized = norm
    src = _merge_src(item.raw, item.normalized)
    errors = _validate_by_type(item.batch.source_type if hasattr(item, 'batch') else 'receipts', src)
    item.errors = errors
    item.status = "OK" if not errors else "ERROR_VALIDATION"

    att = ImportAttachment(item_id=item.id, file_key=file_key, kind="photo", sha256=sha256, ocr_text=texto)
    db.add(att); db.commit(); db.refresh(item)
    return item
