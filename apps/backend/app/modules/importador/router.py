"""API endpoints for Importador Contable Universal."""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

from . import crud, recipe_crud
from .api_lifecycle import mark_legacy_processing_endpoint
from .ai_classifier import CONFIDENCE_THRESHOLD, analyze_document
from .analysis_normalizer import _normalize_analysis_output
from .auto_recipe import (
    get_snapshot_learning,
    get_snapshot_learning_version,
    remember_snapshot_learning,
    resolve_auto_recipe,
    resolve_auto_recipe_from_text,
    should_reprocess_existing_document,
)
from .canonical_document import build_document_projection
from .document_fields import (
    detect_document_date,
    detect_document_payment_method,
    detect_document_subtotal,
    detect_document_tax,
    detect_document_total,
    get_data_value,
    safe_floatish,
)
from .field_alias_loader import get_canonical_fields, get_field_aliases
from .ocr_service import detect_file_type, extract_text_from_file, iter_zip_entries
from .product_import_service import (
    build_product_candidates,
    looks_like_product_document,
    save_product_candidates,
)
from .processing_service import process_import_document
from .recipe_sync import get_available_recipe_sheets, upsert_recipe_from_import
from .runtime_config import (
    load_doc_type_patterns,
    load_file_support_config,
    load_product_sheet_detection_config,
    load_prompt_config,
)
from .schemas import (
    BatchDetailOut,
    BatchSummaryOut,
    BulkStagingPatch,
    ConfirmRequest,
    DashboardStats,
    DocumentLineMatchesResponse,
    DocumentoDetailOut,
    DocumentoListOut,
    DocumentoOut,
    EditFieldsRequest,
    FieldAnalysisResponse,
    IterationOut,
    IterationResultOut,
    IterationScopeIn,
    ReviewSessionCreate,
    ReviewSessionOut,
    RunIterationRequest,
    SaveDailyLogRequest,
    SaveDailyLogResponse,
    SaveDocumentLineMatch,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SaveProductsFromDocumentRequest,
    SaveProductsFromDocumentResponse,
    StagingLineOut,
    StagingLinePatch,
    StagingLineSummary,
    SyncRecipeResponse,
    SyncRecipeSheetResponse,
    SyncRecipesResponse,
    UploadResponse,
)
from .services.iteration_service import (
    build_field_analysis,
    count_lines_for_scope,
    count_staging_lines,
    fetch_lines_for_scope,
    load_error_affected_fields,
    run_iteration,
    upsert_staging_lines_from_extraction,
)
from .services.document_routing_agent import (
    build_document_routing_decision,
)
from .services.document_routing_feedback_service import record_routing_signal
from .services.document_model_learning_service import (
    build_signal_learning_recipe_config,
    summarize_learning_rerun,
)
from .services.product_matching import (
    _append_import_alias,
    _build_document_line_matches,
    _find_product_by_id,
    _get_line_values,
    _infer_pack_conversion_factor,
    _norm_import_text,
    _strip_pack_tokens,
)
from .snapshot_learning import (
    bootstrap_learning_from_existing_document,
    build_snapshot_review_hints,
    learn_from_confirmed_payload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importador", tags=["Importador"])
protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]


def _json_safe(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def _tenant_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", None) or {}
    tid = claims.get("tenant_id") or getattr(request.state, "tenant_id", None)
    if not tid:
        raise HTTPException(status_code=401, detail="tenant_id no disponible")
    return UUID(str(tid)) if not isinstance(tid, UUID) else tid


def _user_id(request: Request) -> str:
    claims = getattr(request.state, "access_claims", None) or {}
    return str(claims.get("user_id", "unknown"))


def _get_doc_import_data(doc) -> dict:
    data = doc.datos_confirmados or doc.datos_extraidos or {}
    return data if isinstance(data, dict) else {}


def _get_confirmed_doc_import_data(doc) -> dict:
    data = doc.datos_confirmados or {}
    return data if isinstance(data, dict) else {}


def _build_routing_source_data(doc) -> dict:
    data = dict(_get_doc_import_data(doc))
    if not isinstance(data, dict):
        data = {}
    if "vendor" not in data and getattr(doc, "proveedor_detectado", None):
        data["vendor"] = doc.proveedor_detectado
    if "vendor_tax_id" not in data and getattr(doc, "ruc_detectado", None):
        data["vendor_tax_id"] = doc.ruc_detectado
    if "total_amount" not in data and getattr(doc, "monto_total", None) is not None:
        data["total_amount"] = doc.monto_total
    if "issue_date" not in data and getattr(doc, "fecha_documento", None):
        data["issue_date"] = doc.fecha_documento
    if "currency" not in data and getattr(doc, "moneda", None):
        data["currency"] = doc.moneda
    return data


def _get_raw_ai_payload(doc) -> dict:
    payload = getattr(doc, "raw_ai_json", None)
    return payload if isinstance(payload, dict) else {}


def _get_canonical_document(doc) -> dict:
    canonical_document = _get_raw_ai_payload(doc).get("canonical_document")
    return canonical_document if isinstance(canonical_document, dict) else {}


def _resolve_document_routing(doc, db: Session):
    from .category_loader import get_doc_categories

    return build_document_routing_decision(
        source_doc_type=getattr(doc, "tipo_documento_detectado", None),
        ai_confidence=getattr(doc, "confianza_clasificacion", None),
        extracted_data=_build_routing_source_data(doc),
        canonical_document=_get_canonical_document(doc),
        category_keywords=get_doc_categories(db),
        requires_review=bool(getattr(doc, "requiere_revision", False)),
        db=db,
        tenant_id=getattr(doc, "tenant_id", None),
    )


def _attach_document_routing(doc, db: Session):
    doc.routing_decision = _resolve_document_routing(doc, db)
    return doc.routing_decision


def _attach_document_review_hints(doc, db: Session):
    snapshot_id = getattr(doc, "recipe_snapshot_id", None)
    if not snapshot_id:
        doc.review_hints = []
        return doc.review_hints

    snapshot = recipe_crud.get_snapshot(db, snapshot_id)
    canonical_fields = get_canonical_fields(db, tenant_id=getattr(doc, "tenant_id", None))
    routing = getattr(doc, "routing_decision", None) or _resolve_document_routing(doc, db)
    missing_fields = routing.missing_fields if routing else []
    doc.review_hints = build_snapshot_review_hints(
        snapshot,
        missing_fields=missing_fields,
        canonical_fields=canonical_fields,
        limit=5,
    )
    return doc.review_hints


def _normalize_payload_for_audit(value):
    if isinstance(value, dict):
        return {
            str(key): _normalize_payload_for_audit(item)
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, list):
        return [_normalize_payload_for_audit(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def _derive_confirmation_mode(doc, datos_confirmados: dict) -> str:
    detected = getattr(doc, "datos_extraidos", None)
    detected_payload = detected if isinstance(detected, dict) else {}
    confirmed_payload = datos_confirmados if isinstance(datos_confirmados, dict) else {}
    if _normalize_payload_for_audit(detected_payload) == _normalize_payload_for_audit(confirmed_payload):
        return "accepted_as_detected"
    return "corrected_by_user"


def _attach_document_activity_meta(doc):
    logs = sorted((getattr(doc, "logs", []) or []), key=lambda log: log.created_at or datetime.datetime.min)
    doc.last_processing_reason = None
    doc.last_learning_reprocess_at = None
    doc.last_confirmation_mode = None
    for log in reversed(logs):
        detail = log.detalle if isinstance(log.detalle, dict) else {}
        if log.accion == "REPROCESS" and doc.last_processing_reason is None:
            reason = str(detail.get("reason") or "").strip()
            doc.last_processing_reason = reason or None
            if reason == "learning_update":
                doc.last_learning_reprocess_at = log.created_at
        if log.accion == "CONFIRM" and doc.last_confirmation_mode is None:
            mode = str(detail.get("confirmation_mode") or "").strip()
            doc.last_confirmation_mode = mode or None
        if (
            doc.last_processing_reason is not None
            and doc.last_confirmation_mode is not None
            and doc.last_learning_reprocess_at is not None
        ):
            break
    return doc


def _resolve_destination_routing(doc, db: Session, destination: str):
    from .category_loader import get_doc_categories

    return build_document_routing_decision(
        source_doc_type=getattr(doc, "tipo_documento_detectado", None),
        ai_confidence=getattr(doc, "confianza_clasificacion", None),
        extracted_data=_build_routing_source_data(doc),
        canonical_document=_get_canonical_document(doc),
        category_keywords=get_doc_categories(db),
        requires_review=bool(getattr(doc, "requiere_revision", False)),
        destination_override=destination,
        db=db,
        tenant_id=getattr(doc, "tenant_id", None),
    )


def _build_routing_conflict_detail(doc, db: Session, destination: str) -> dict:
    decision = _resolve_destination_routing(doc, db, destination)
    return {
        "code": "document_routing_review_required",
        "document_type": decision.document_type,
        "suggested_destination": decision.suggested_destination,
        "required_fields_ok": decision.required_fields_ok,
        "missing_fields": decision.missing_fields,
        "needs_human_review": decision.needs_human_review,
        "reason": decision.reason,
    }


def _require_routing_ready(doc, db: Session, destination: str) -> None:
    decision = _resolve_destination_routing(doc, db, destination)
    if decision.required_fields_ok:
        return
    raise HTTPException(status_code=409, detail=_build_routing_conflict_detail(doc, db, destination))


def _capture_routing_signal(doc, db: Session, user_id: str, *, event: str, changed_fields=None) -> None:
    record_routing_signal(
        db,
        doc,
        user_id=user_id,
        event=event,
        changed_fields=list(changed_fields or []),
    )


def _require_confirmed_doc_import_data(doc, destination: str) -> dict:
    data = _get_confirmed_doc_import_data(doc)
    if data:
        return data
    raise HTTPException(
        status_code=409,
        detail=("Debes confirmar el documento antes de guardarlo en " f"{destination}."),
    )


def _extract_document_line_items(data: dict, aliases: list[str] | None = None) -> list[dict]:
    keys = aliases or []
    raw = get_data_value(data, *keys) if keys else None
    if not isinstance(raw, list):
        raw = data.get("line_items") or data.get("lineas") or data.get("items")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _get_synced_sheet_map(db: Session, doc) -> dict[str, dict]:
    from app.models.recipes import Recipe

    synced: dict[str, dict] = {}
    candidate_ids: list[UUID] = []
    logs = sorted(
        (getattr(doc, "logs", []) or []), key=lambda log: log.created_at or datetime.datetime.min
    )
    for log in logs:
        detail = log.detalle or {}
        if log.accion != "SYNC_PRODUCTION" or not isinstance(detail, dict):
            continue
        raw_id = str(detail.get("recipe_id") or "").strip()
        if not raw_id:
            continue
        try:
            candidate_ids.append(UUID(raw_id))
        except ValueError:
            continue

    existing_recipe_ids = (
        {
            str(row[0])
            for row in db.query(Recipe.id)
            .filter(Recipe.tenant_id == doc.tenant_id, Recipe.id.in_(candidate_ids))
            .all()
        }
        if candidate_ids
        else set()
    )

    for log in logs:
        if log.accion != "SYNC_PRODUCTION":
            continue
        detail = log.detalle or {}
        if not isinstance(detail, dict):
            continue
        sheet_name = str(detail.get("sheet_used") or "").strip()
        if not sheet_name:
            continue
        raw_recipe_id = str(detail.get("recipe_id") or "").strip()
        if not raw_recipe_id:
            continue
        try:
            recipe_id = str(UUID(raw_recipe_id))
        except ValueError:
            continue
        if recipe_id not in existing_recipe_ids:
            continue
        # Siempre actualizamos con el log más reciente para esta hoja.
        # Múltiples hojas pueden compartir el mismo recipe_id (nombre de receta
        # idéntico entre hojas) — ambas deben mostrarse como guardadas.
        synced[sheet_name] = {
            "recipe_id": recipe_id,
            "recipe_name": str(detail.get("recipe_name") or "") or None,
            "created_at": log.created_at,
        }
    return synced


def _first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        return value
    return None


def _get_document_payment_method(data: dict, aliases: list[str] | None = None) -> str | None:
    detected = detect_document_payment_method(data, aliases=aliases)
    if detected:
        return detected
    direct_value = data.get("payment_method")
    if direct_value is not None:
        text = str(direct_value).strip()
        if text:
            return text
    save_meta = data.get("_save")
    if isinstance(save_meta, dict):
        saved_method = save_meta.get("payment_method")
        if saved_method is not None:
            text = str(saved_method).strip()
            if text:
                return text
    return None


def _coerce_user_uuid(user_id: str):
    import uuid

    try:
        return UUID(str(user_id))
    except (TypeError, ValueError):
        return uuid.uuid4()


def _infer_save_destination(doc, db: Session) -> str:
    routing_decision = _resolve_document_routing(doc, db)
    if routing_decision.suggested_destination:
        return routing_decision.suggested_destination

    from .category_loader import classify_doc_type, get_doc_categories

    tipo = str(doc.tipo_documento_detectado or "").strip().upper()
    data = _get_doc_import_data(doc)
    cats = get_doc_categories(db)

    category = classify_doc_type(tipo, cats)
    if category == "recipe":
        return "recipe"
    if isinstance(data.get("filas"), list) and category == "other":
        return "recipe"
    if category == "receipt":
        return "expense"
    if category == "invoice":
        return "supplier_invoice"
    if doc.proveedor_detectado or doc.ruc_detectado or doc.monto_total is not None:
        return "supplier_invoice"
    return "expense"


def _normalize_payment_details(total: float | None, body: SaveDocumentRequest) -> dict:
    status = body.payment_status or "pending"
    paid_amount = _safe_float(body.paid_amount)
    pending_amount = _safe_float(body.pending_amount)

    if status == "paid":
        paid_amount = paid_amount if paid_amount is not None else total
        pending_amount = 0.0
    elif status == "pending":
        paid_amount = 0.0
        pending_amount = pending_amount if pending_amount is not None else total
    else:
        if paid_amount is None and pending_amount is None:
            raise HTTPException(
                status_code=400,
                detail="Para pagos parciales debes indicar el monto pagado o el pendiente.",
            )
        if total is not None:
            if paid_amount is None:
                paid_amount = max(total - float(pending_amount or 0), 0.0)
            if pending_amount is None:
                pending_amount = max(total - float(paid_amount or 0), 0.0)
            if (paid_amount or 0.0) + (pending_amount or 0.0) > total + 0.01:
                raise HTTPException(
                    status_code=400,
                    detail="La suma de pagado y pendiente no puede superar el total del documento.",
                )
        elif paid_amount is None or pending_amount is None:
            raise HTTPException(
                status_code=400,
                detail="Sin total detectado, un pago parcial requiere monto pagado y pendiente.",
            )

    return {
        "status": status,
        "paid_amount": round(float(paid_amount), 2) if paid_amount is not None else None,
        "pending_amount": round(float(pending_amount), 2) if pending_amount is not None else None,
    }


def _lookup_supplier(
    db: Session, tenant_id: UUID, doc, data: dict
) -> tuple[UUID | None, str | None]:
    from app.models.suppliers.supplier import Supplier

    fa = get_field_aliases(db, tenant_id=tenant_id)
    supplier_name = _first_non_empty(
        doc.proveedor_detectado,
        get_data_value(data, *(fa.get("vendor") or [])),
    )
    supplier_tax_id = _first_non_empty(
        doc.ruc_detectado,
        get_data_value(data, *(fa.get("vendor_tax_id") or [])),
    )

    supplier = None
    if supplier_tax_id:
        supplier = (
            db.query(Supplier)
            .filter(
                Supplier.tenant_id == tenant_id,
                func.lower(Supplier.tax_id) == str(supplier_tax_id).strip().lower(),
            )
            .first()
        )
    if not supplier and supplier_name:
        supplier = (
            db.query(Supplier)
            .filter(
                Supplier.tenant_id == tenant_id,
                func.lower(Supplier.name) == str(supplier_name).strip().lower(),
            )
            .first()
        )

    if not supplier and supplier_name:
        supplier = Supplier(
            tenant_id=tenant_id,
            name=str(supplier_name).strip(),
            tax_id=str(supplier_tax_id).strip() if supplier_tax_id else None,
        )
        db.add(supplier)
        db.flush()
        logger.info("Auto-created supplier '%s' for tenant %s", supplier.name, tenant_id)

    return (
        supplier.id if supplier else None,
        str(supplier_name).strip() if supplier_name else None,
    )


def _compose_expense_notes(
    doc,
    destination: str,
    supplier_name: str | None,
    payment: dict,
    payment_method: str | None,
    paid_at: str | None,
    extra_notes: str | None,
) -> str:
    lines = []
    if extra_notes:
        lines.append(str(extra_notes).strip())
    lines.append(f"Documento origen: {doc.nombre_archivo}")
    if supplier_name:
        lines.append(f"Proveedor detectado: {supplier_name}")
    lines.append(
        "Tipo guardado: Factura proveedor"
        if destination == "supplier_invoice"
        else "Tipo guardado: Gasto"
    )
    lines.append(f"Estado de pago: {payment['status']}")
    if payment.get("paid_amount") is not None:
        lines.append(f"Monto pagado: {payment['paid_amount']:.2f}")
    if payment.get("pending_amount") is not None:
        lines.append(f"Monto pendiente: {payment['pending_amount']:.2f}")
    if payment_method:
        lines.append(f"Metodo de pago: {payment_method}")
    if paid_at:
        lines.append(f"Fecha de pago: {paid_at}")
    return "\n".join(line for line in lines if line)


def _get_document_total(doc, aliases: list[str] | None = None) -> float | None:
    data = _get_doc_import_data(doc)
    return _first_non_empty(doc.monto_total, detect_document_total(data, aliases=aliases))


def _parse_document_date(value) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    raw = str(value or "").strip()
    if not raw:
        return datetime.date.today()
    for candidate in (raw[:10], raw):
        try:
            return datetime.date.fromisoformat(candidate)
        except ValueError:
            continue
    return datetime.date.today()


def _resolve_payment_method(
    db: Session,
    tenant_id: UUID,
    payment_method_id: UUID | str | None = None,
    payment_method: str | None = None,
):
    from difflib import SequenceMatcher

    from app.models.accounting.pos_settings import PaymentMethod

    try:
        tenant_id = UUID(str(tenant_id))
    except (TypeError, ValueError):
        return None, None

    methods = (
        db.query(PaymentMethod)
        .filter(
            PaymentMethod.tenant_id == tenant_id,
            PaymentMethod.is_active == True,  # noqa: E712
        )
        .order_by(PaymentMethod.name.asc())
        .all()
    )
    if not methods:
        legacy_value = str(payment_method or "").strip()
        if legacy_value:
            try:
                UUID(legacy_value)
            except (TypeError, ValueError):
                return legacy_value, None
        return None, None

    if payment_method_id:
        try:
            wanted_id = UUID(str(payment_method_id))
        except (TypeError, ValueError):
            wanted_id = None
        if wanted_id:
            for method in methods:
                if method.id == wanted_id:
                    return method.name, method.id

    raw = str(payment_method or "").strip()
    if not raw:
        return None, None

    raw = re.sub(
        r"^(payment\s*(method|type|terms?)|metodo\s+de\s+pago|forma\s+de\s+pago|tipo\s+de\s+pago|medio\s+de\s+pago|condiciones?\s+de\s+pago)\s*[:\-]\s*",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()
    raw_norm = _norm_import_text(raw)
    if not raw_norm:
        return None, None

    best_method = None
    best_score = 0.0
    for method in methods:
        name_norm = _norm_import_text(method.name)
        description_norm = _norm_import_text(method.description or "")
        score = 0.0

        if raw_norm == name_norm:
            score = 1.0
        elif description_norm and raw_norm == description_norm:
            score = 0.96
        elif name_norm and (raw_norm in name_norm or name_norm in raw_norm):
            score = 0.9
        elif description_norm and (raw_norm in description_norm or description_norm in raw_norm):
            score = 0.84
        else:
            candidate_text = " ".join(part for part in [name_norm, description_norm] if part)
            similarity = SequenceMatcher(None, raw_norm, candidate_text).ratio()
            if similarity >= 0.62:
                score = min(similarity, 0.79)

        if score > best_score:
            best_score = score
            best_method = method

    if best_method and best_score >= 0.78:
        return best_method.name, best_method.id
    return None, None


def _save_document_to_expense(
    db: Session,
    tenant_id: UUID,
    user_id: str,
    doc,
    body: SaveDocumentRequest,
) -> SaveDocumentResponse:
    from app.models.expenses.expense import Expense
    from app.modules.expenses.infrastructure.repositories import ExpenseRepo

    fa = get_field_aliases(db, tenant_id=tenant_id)
    data = _get_doc_import_data(doc)
    total = _get_document_total(doc, aliases=fa.get("total_amount"))
    vat = detect_document_tax(data, aliases=fa.get("tax_amount")) or 0.0
    subtotal = detect_document_subtotal(data, aliases=fa.get("subtotal"))

    if subtotal is None and total is not None:
        subtotal = max(total - vat, 0.0)
    if subtotal is None and total is None:
        raise HTTPException(
            status_code=422,
            detail="No se detecto un monto suficiente para guardar este documento como gasto.",
        )
    if total is None:
        total = round(float(subtotal or 0.0) + float(vat or 0.0), 2)

    payment = _normalize_payment_details(total, body)
    detected_payment_method = _get_document_payment_method(data, aliases=fa.get("payment_method"))
    payment_method, _payment_method_id = _resolve_payment_method(
        db,
        tenant_id,
        getattr(body, "payment_method_id", None),
        body.payment_method or detected_payment_method,
    )

    supplier_id, supplier_name = _lookup_supplier(db, tenant_id, doc, data)
    invoice_number = _first_non_empty(
        get_data_value(data, *(fa.get("doc_number") or [])),
    )
    concept = _first_non_empty(
        get_data_value(data, *(fa.get("concept") or [])),
    )
    if not concept:
        prefix = "Factura proveedor" if body.destination == "supplier_invoice" else "Gasto"
        concept = f"{prefix} {supplier_name or doc.nombre_archivo}"
    concept = str(concept)[:255]

    expense_date = _parse_document_date(
        _first_non_empty(
            doc.fecha_documento,
            detect_document_date(data, aliases=fa.get("issue_date")),
            datetime.date.today().isoformat(),
        )
    )
    category = str(
        _first_non_empty(
            "supplier_invoice" if body.destination == "supplier_invoice" else None,
            get_data_value(data, *(fa.get("category") or [])),
            "expense",
        )
    )[:50]
    notes = _compose_expense_notes(
        doc,
        body.destination or "expense",
        supplier_name,
        payment,
        payment_method,
        body.paid_at,
        body.notes or get_data_value(data, *(fa.get("concept") or [])),
    )

    existing_expense = None
    if invoice_number:
        q = db.query(Expense).filter(
            Expense.tenant_id == tenant_id,
            func.lower(Expense.invoice_number) == str(invoice_number).strip().lower(),
        )
        if supplier_id:
            q = q.filter(Expense.supplier_id == supplier_id)
        existing_expense = q.first()
    if not existing_expense:
        existing_expense = (
            db.query(Expense)
            .filter(
                Expense.tenant_id == tenant_id,
                Expense.date == expense_date,
                func.lower(Expense.concept) == concept.lower(),
                Expense.total == float(total),
            )
            .first()
        )
    if existing_expense:
        return SaveDocumentResponse(
            target="expenses",
            destination=body.destination or "expense",
            status="skipped",
            record_id=str(existing_expense.id),
            message="El gasto ya existia y no se duplico.",
        )

    expense = ExpenseRepo(db).create(
        tenant_id,
        date=expense_date,
        supplier_id=supplier_id,
        amount=float(subtotal or 0.0),
        concept=concept,
        category=category,
        payment_method=payment_method,
        invoice_number=str(invoice_number) if invoice_number else None,
        status=payment["status"],
        paid_amount=payment.get("paid_amount"),
        pending_amount=payment.get("pending_amount"),
        notes=notes,
        vat=float(vat),
        total=float(total),
        user_id=_coerce_user_uuid(user_id),
    )
    db.flush()
    return SaveDocumentResponse(
        target="expenses",
        destination=body.destination or "expense",
        status="created",
        record_id=str(expense.id),
        message="Documento guardado en gastos.",
    )


def _save_document_to_purchase(
    db: Session,
    tenant_id: UUID,
    user_id: str,
    doc,
    *,
    warehouse_id: UUID | None = None,
    notes: str | None = None,
    update_stock: bool = True,
    line_matches: list[SaveDocumentLineMatch] | None = None,
) -> dict:
    """Core purchase creation logic for document saves to purchases."""
    from decimal import ROUND_HALF_UP, Decimal

    from app.models.inventory.stock import StockItem, StockMove
    from app.models.inventory.warehouse import Warehouse
    from app.models.purchases.purchase import Purchase, PurchaseLine
    from app.services.inventory_costing import InventoryCostingService

    fa = get_field_aliases(db, tenant_id=tenant_id)
    data = _get_doc_import_data(doc)
    line_items = _extract_document_line_items(data, aliases=fa.get("line_items"))
    line_match_map = {
        int(match.line_index): match
        for match in (line_matches or [])
        if match.product_id is not None
    }

    logger.info(
        "save_purchase: tenant=%s update_stock=%s line_items=%d warehouse_id=%s",
        tenant_id,
        update_stock,
        len(line_items),
        warehouse_id,
    )

    # Warehouse resolution
    warehouse = None
    if update_stock:
        if warehouse_id:
            warehouse = (
                db.query(Warehouse)
                .filter(
                    Warehouse.tenant_id == str(tenant_id),
                    Warehouse.id == str(warehouse_id),
                    Warehouse.is_active.is_(True),
                )
                .first()
            )
        else:
            warehouse = (
                db.query(Warehouse)
                .filter(
                    Warehouse.tenant_id == str(tenant_id),
                    Warehouse.is_active.is_(True),
                )
                .first()
            )

    logger.info("save_purchase: warehouse=%s", warehouse.id if warehouse else None)

    doc_number = str(
        _first_non_empty(get_data_value(data, *(fa.get("doc_number") or []))) or doc.nombre_archivo
    )[:50]
    purchase_date = _parse_document_date(
        _first_non_empty(
            doc.fecha_documento,
            detect_document_date(data, aliases=fa.get("issue_date")),
        )
    )
    supplier_id, supplier_name = _lookup_supplier(db, tenant_id, doc, data)
    total = _get_document_total(doc, aliases=fa.get("total_amount")) or 0.0
    vat = detect_document_tax(data, aliases=fa.get("tax_amount")) or 0.0
    subtotal = detect_document_subtotal(data, aliases=fa.get("subtotal"))
    if subtotal is None:
        subtotal = max(total - vat, 0.0)

    # Idempotency: check for existing purchase
    existing = db.query(Purchase).filter(
        Purchase.tenant_id == tenant_id,
        Purchase.number == doc_number,
        Purchase.total == float(total),
    )
    if supplier_id:
        existing = existing.filter(Purchase.supplier_id == supplier_id)
    existing = existing.first()
    stock_only = False
    logger.info(
        "save_purchase: existing=%s update_stock=%s warehouse=%s",
        existing.id if existing else None,
        update_stock,
        warehouse.id if warehouse else None,
    )
    if existing:
        # If stock update requested but no moves exist yet, allow stock-only pass
        if update_stock and warehouse:
            has_moves = (
                db.query(StockMove)
                .filter(StockMove.ref_type == "purchase", StockMove.ref_id == str(existing.id))
                .first()
            )
            if not has_moves:
                stock_only = True
                purchase = existing
        if not stock_only:
            return {
                "purchase_id": existing.id,
                "status": "skipped",
                "lines_created": 0,
                "lines_matched": 0,
                "unmatched_descriptions": [],
                "warehouse_id": None,
                "message": "La compra ya existía y no se duplicó.",
            }

    if not stock_only:
        purchase = Purchase(
            tenant_id=tenant_id,
            number=doc_number,
            supplier_id=supplier_id,
            date=purchase_date,
            subtotal=float(subtotal),
            taxes=float(vat),
            total=float(total),
            status="received",
            notes=notes or f"Importado desde: {doc.nombre_archivo}",
            user_id=_coerce_user_uuid(user_id),
        )
        db.add(purchase)
        db.flush()

    costing = InventoryCostingService(db) if warehouse else None
    lines_created = 0
    lines_matched = 0
    unmatched: list[str] = []

    def _dec(v) -> Decimal:
        return Decimal(str(v or 0)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    for line_index, item in enumerate(line_items):
        description, qty, unit_price = _get_line_values(item)
        total_price = float(
            item.get("total_price") or item.get("total") or item.get("importe") or qty * unit_price
        )
        if not description or qty <= 0:
            continue

        selected_match = line_match_map.get(line_index)
        if selected_match:
            product = _find_product_by_id(db, tenant_id, selected_match.product_id)
            conv_factor = (
                _infer_pack_conversion_factor(description, getattr(product, "unit", None))
                if product
                else 1.0
            )
        else:
            product, conv_factor = _match_product(db, tenant_id, description)
        stock_qty = qty * conv_factor  # convert invoice qty to inventory units
        logger.info(
            "save_purchase line: index=%s desc='%s' qty=%s matched=%s conv=%s stock_only=%s",
            line_index,
            description,
            qty,
            product.name if product else None,
            conv_factor,
            stock_only,
        )

        if product and warehouse and costing and update_stock:
            qty_dec = _dec(stock_qty)
            cost_dec = _dec(unit_price / conv_factor if conv_factor else unit_price)

            stock_row = (
                db.query(StockItem)
                .filter(
                    StockItem.warehouse_id == str(warehouse.id),
                    StockItem.product_id == str(product.id),
                )
                .with_for_update()
                .first()
            )
            if not stock_row:
                stock_row = StockItem(
                    tenant_id=str(tenant_id),
                    warehouse_id=str(warehouse.id),
                    product_id=str(product.id),
                    qty=0,
                )
                db.add(stock_row)
                db.flush()

            costing.apply_inbound(
                str(tenant_id),
                str(warehouse.id),
                str(product.id),
                qty=qty_dec,
                unit_cost=cost_dec,
                initial_qty=_dec(stock_row.qty),
                initial_avg_cost=cost_dec,
            )
            stock_row.qty = float(stock_row.qty or 0) + float(qty_dec)
            db.add(stock_row)

            product.stock = float(product.stock or 0) + float(qty_dec)
            db.add(product)

            db.add(
                StockMove(
                    tenant_id=str(tenant_id),
                    product_id=str(product.id),
                    warehouse_id=str(warehouse.id),
                    qty=float(qty_dec),
                    kind="receipt",
                    tentative=False,
                    posted=True,
                    ref_type="purchase",
                    ref_id=str(purchase.id),
                    unit_cost=float(cost_dec),
                    total_cost=float(cost_dec * qty_dec),
                )
            )
            lines_matched += 1
            if selected_match and selected_match.persist_alias:
                _append_import_alias(
                    product, description, conv_factor, getattr(product, "unit", None)
                )
                db.add(product)
        else:
            if description and product is None:
                unmatched.append(description)

        if not stock_only:
            db.add(
                PurchaseLine(
                    purchase_id=purchase.id,
                    product_id=product.id if product else None,
                    description=description,
                    quantity=qty,
                    unit_price=unit_price,
                    tax_rate=0,
                    total=total_price,
                )
            )
            lines_created += 1

    db.flush()
    logger.info(
        "save_purchase RESULT: stock_only=%s lines_created=%d lines_matched=%d unmatched=%s",
        stock_only,
        lines_created,
        lines_matched,
        unmatched,
    )

    # Build a clear stock status message
    if not update_stock:
        stock_msg = ""
    elif warehouse is None:
        stock_msg = (
            " ⚠️ No se actualizó el stock: no hay almacén activo configurado para este tenant."
        )
    elif lines_matched == 0 and unmatched:
        stock_msg = f" ⚠️ No se actualizó el stock: sin producto coincidente para: {unmatched}."
    elif lines_matched == 0 and line_items:
        stock_msg = " ⚠️ No se actualizó el stock: los productos de la factura no coincidieron con ningún producto del catálogo."
    else:
        stock_msg = f" ✓ {lines_matched} producto(s) actualizados en stock."

    return {
        "purchase_id": purchase.id,
        "status": "stock_updated" if stock_only else "created",
        "lines_created": lines_created,
        "lines_matched": lines_matched,
        "unmatched_descriptions": unmatched,
        "warehouse_id": str(warehouse.id) if warehouse else None,
        "message": (
            f"Stock actualizado para compra existente.{stock_msg}"
            if stock_only
            else f"Compra registrada.{stock_msg}"
        ),
    }


@router.post(
    "/upload",
    response_model=list[UploadResponse],
    dependencies=protected,
    deprecated=True,
)
async def upload_files(
    request: Request,
    response: Response,
    files: list[UploadFile] = File(...),
    force: bool = Query(
        default=False, description="Si true, fuerza reprocesar aunque exista duplicado"
    ),
    db: Session = Depends(get_db),
):
    """Legacy sync upload path. Prefer /importador/run-async for the production flow."""
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    mark_legacy_processing_endpoint(response)
    logger.info("Legacy importador endpoint used: /upload tenant=%s", tenant_id)
    results = []

    async def _process_single(file_bytes: bytes, filename: str, tipo_archivo: str | None = None):
        nonlocal db, tenant_id, user_id, results
        tipo_archivo = tipo_archivo or detect_file_type(filename, db)
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        response_action: Literal["CREATED", "REUSED", "REPROCESS"] = "CREATED"
        response_message = "Se creo un nuevo documento para esta importacion."

        existing = crud.find_existing_documento(db, tenant_id, filename, len(file_bytes), file_hash)
        exact_hash_match = bool(existing and existing.hash_sha256 == file_hash)
        learning_reprocess_needed = False
        if existing and isinstance(getattr(existing, "datos_confirmados", None), dict) and existing.datos_confirmados:
            bootstrap_learning_from_existing_document(db, existing, user_id)
        if existing:
            learning_reprocess_needed = bool(
                exact_hash_match
                and existing.estado in ("CONFIRMED", "REVIEW")
                and should_reprocess_existing_document(db, existing)
            )
        reuse_existing = bool(
            existing
            and (
                existing.estado in ("PENDING", "PROCESSING")
                or (
                    existing.estado in ("CONFIRMED", "REVIEW")
                    and not force
                    and not learning_reprocess_needed
                )
            )
        )
        if reuse_existing:
            crud.add_log(
                db, existing.id, "SKIP_DUPLICATE", user_id, {"reason": "same hash_or_name"}
            )
            db.commit()
            routing_decision = _attach_document_routing(existing, db)
            review_hints = _attach_document_review_hints(existing, db)
            results.append(
                UploadResponse(
                    id=existing.id,
                    estado=existing.estado,
                    tipo_documento_detectado=existing.tipo_documento_detectado,
                    confianza_clasificacion=existing.confianza_clasificacion,
                    requiere_revision=existing.requiere_revision,
                    datos_extraidos=existing.datos_extraidos,
                    routing_decision=routing_decision,
                    review_hints=review_hints,
                    action="REUSED",
                    message=(
                        "Documento ya existente; se reutilizo el resultado actual porque no habia aprendizaje nuevo pendiente. "
                        "Usa reimportacion limpia si quieres forzar otro analisis."
                    ),
                )
            )
            return

        predecessor = None
        if (
            exact_hash_match
            and existing
            and (
                existing.estado == "FAILED"
                or (existing.estado in ("CONFIRMED", "REVIEW") and force)
                or (existing.estado == "REVIEW" and not reuse_existing)
            )
        ):
            doc = existing
            response_action = "REPROCESS"
            rerun_reason = "learning_update" if learning_reprocess_needed and not force else "manual"
            response_message = (
                "Se reanalizo el mismo documento para aplicar aprendizaje confirmado reciente."
                if rerun_reason == "learning_update"
                else "Se reproceso el mismo documento sobre el registro existente."
            )
            crud.reset_documento_for_reprocess(
                db,
                doc,
                estado="PROCESSING",
                clear_recipe_snapshot=True,
            )
            crud.add_log(
                db,
                doc.id,
                "REPROCESS",
                user_id,
                {
                    "filename": filename,
                    "size": len(file_bytes),
                    "mode": "in_place",
                    "reason": rerun_reason,
                },
            )
        else:
            predecessor = crud.find_latest_documento_by_name(
                db,
                tenant_id,
                filename,
                exclude_hash_sha256=file_hash,
            )
            doc = crud.create_documento(
                db,
                {
                    "tenant_id": tenant_id,
                    "nombre_archivo": filename,
                    "tipo_archivo": tipo_archivo,
                    "tamanio_bytes": len(file_bytes),
                    "hash_sha256": file_hash,
                    "estado": "PROCESSING",
                    "usuario_id": user_id,
                },
            )
            if predecessor and predecessor.id != doc.id:
                crud.link_documento_successor(db, predecessor.id, doc.id)
            crud.add_log(
                db,
                doc.id,
                "UPLOAD",
                user_id,
                {"filename": filename, "size": len(file_bytes)},
            )
        db.commit()

        try:
            result = await process_import_document(
                mode="upload",
                db=db,
                doc=doc,
                tenant_id=tenant_id,
                user_id=user_id,
                file_bytes=file_bytes,
                filename=filename,
                tipo_archivo=tipo_archivo,
                force=force,
                extract_text_fn=extract_text_from_file,
                analyze_document_fn=analyze_document,
            )
            db.commit()
            results.append(
                UploadResponse(
                    id=doc.id,
                    estado=doc.estado,
                    tipo_documento_detectado=result.tipo_documento_detectado,
                    confianza_clasificacion=result.confianza_clasificacion,
                    requiere_revision=result.requiere_revision,
                    datos_extraidos=result.datos_extraidos,
                    routing_decision=result.routing_decision,
                    review_hints=result.review_hints,
                    action=response_action,
                    message=response_message,
                )
            )
        except Exception as exc:
            logger.error("Error processing %s: %s", filename, exc)
            crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": str(exc)})
            crud.add_log(db, doc.id, "EXTRACT", user_id, {"error": str(exc)})
            db.commit()
            results.append(
                UploadResponse(
                    id=doc.id,
                    estado="FAILED",
                    action=response_action,
                    message=response_message,
                )
            )

    for file in files:
        file_bytes = await file.read()
        filename = file.filename or "sin_nombre"
        tipo_archivo = detect_file_type(filename, db)

        if tipo_archivo == "ZIP":
            entries = list(iter_zip_entries(file_bytes, db=db))
            if not entries:
                doc = crud.create_documento(
                    db,
                    {
                        "tenant_id": tenant_id,
                        "nombre_archivo": filename,
                        "tipo_archivo": tipo_archivo,
                        "tamanio_bytes": len(file_bytes),
                        "estado": "FAILED",
                        "usuario_id": user_id,
                        "error_detalle": "ZIP vacío o sin ficheros soportados",
                    },
                )
                crud.add_log(
                    db, doc.id, "UPLOAD", user_id, {"filename": filename, "size": len(file_bytes)}
                )
                crud.add_log(
                    db, doc.id, "ERROR", user_id, {"error": "ZIP vacío o sin ficheros soportados"}
                )
                db.commit()
                results.append(
                    UploadResponse(
                        id=doc.id,
                        estado="FAILED",
                        datos_extraidos={"error": "ZIP vacío o sin ficheros soportados"},
                        action="CREATED",
                        message="No se pudo procesar el archivo comprimido.",
                    )
                )
                continue
            for inner_name, inner_bytes in entries:
                await _process_single(
                    inner_bytes, f"{filename}::{inner_name}", detect_file_type(inner_name, db)
                )
        else:
            await _process_single(file_bytes, filename, tipo_archivo)

    return results


@router.get("/documents", response_model=list[DocumentoListOut], dependencies=protected)
def list_documents(
    request: Request,
    estado: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    documents = crud.list_documentos(db, tenant_id, estado=estado, limit=limit, offset=offset)
    for document in documents:
        _attach_document_activity_meta(document)
    return documents


@router.get("/documents/{doc_id}", response_model=DocumentoDetailOut, dependencies=protected)
def get_document(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    from app.models.recipes import Recipe

    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    # Si synced_recipe_id apunta a una receta que ya no existe, limpiar la referencia
    if doc.synced_recipe_id:
        exists = db.query(Recipe.id).filter(Recipe.id == doc.synced_recipe_id).first()
        if not exists:
            doc.synced_recipe_id = None
            db.commit()
    doc.synced_sheets = _get_synced_sheet_map(db, doc)
    doc.version_links = crud.list_documento_versions(db, doc.id)
    _attach_document_routing(doc, db)
    _attach_document_review_hints(doc, db)
    _attach_document_activity_meta(doc)
    return doc


class SyncRecipeRequest(BaseModel):
    sheet_usada: str | None = None
    force: bool = False


class SyncRecipesRequest(BaseModel):
    force: bool = False


def _learn_from_confirmation(db: Session, doc, datos_confirmados: dict, user_id: str) -> None:
    """Persist learned hints from a confirmed document into its snapshot."""
    learn_from_confirmed_payload(db, doc, datos_confirmados, user_id)


@router.post("/documents/{doc_id}/confirm", response_model=DocumentoOut, dependencies=protected)
def confirm_document(
    doc_id: UUID, body: ConfirmRequest, request: Request, db: Session = Depends(get_db)
):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.estado == "CONFIRMED":
        raise HTTPException(status_code=400, detail="Documento ya confirmado")

    confirmation_mode = _derive_confirmation_mode(doc, body.datos_confirmados)

    crud.update_documento(db, doc, {"datos_confirmados": body.datos_confirmados, "estado": "CONFIRMED"})
    _capture_routing_signal(
        doc,
        db,
        user_id,
        event="confirm",
        changed_fields=list(body.datos_confirmados.keys()),
    )
    _sync_batch_projection(db, doc.id, "CONFIRMED")
    crud.add_log(
        db,
        doc.id,
        "CONFIRM",
        user_id,
        {
            "datos_confirmados": body.datos_confirmados,
            "confirmation_mode": confirmation_mode,
        },
    )

    _learn_from_confirmation(db, doc, body.datos_confirmados, user_id)

    db.commit()
    _attach_document_routing(doc, db)
    _attach_document_review_hints(doc, db)
    _attach_document_activity_meta(doc)
    return doc


@router.post(
    "/documents/{doc_id}/sync_recipe", response_model=SyncRecipeResponse, dependencies=protected
)
def sync_recipe(
    doc_id: UUID, body: SyncRecipeRequest | None, request: Request, db: Session = Depends(get_db)
):
    from app.models.recipes import Recipe

    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    data = _get_doc_import_data(doc)
    available_sheets = get_available_recipe_sheets(data)
    sheet_override = body.sheet_usada if body else None
    force = bool(body.force) if body else False
    sheet_name = (
        sheet_override
        or data.get("sheet_usada")
        or (available_sheets[0] if available_sheets else None)
    )
    synced_sheets = _get_synced_sheet_map(db, doc)

    if sheet_name and sheet_name in synced_sheets and not force:
        raise HTTPException(status_code=409, detail=f"La hoja '{sheet_name}' ya fue sincronizada.")

    recipe_id, was_new = upsert_recipe_from_import(doc, db, sheet_override=sheet_override)
    if not recipe_id:
        raise HTTPException(
            status_code=422,
            detail="No se pudo extraer una receta del documento. Verifique que sea un documento de costeo con filas de ingredientes.",
        )

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    # Guardar referencia en el documento
    doc.synced_recipe_id = recipe_id
    crud.mark_document_staging_imported(
        db,
        doc.id,
        target_table="recipes",
        target_id=recipe_id,
    )
    crud.add_log(
        db,
        doc.id,
        "SYNC_PRODUCTION",
        user_id,
        {
            "recipe_id": str(recipe_id),
            "recipe_name": recipe.name if recipe else None,
            "sheet_used": sheet_name,
            "was_new": was_new,
        },
    )
    db.commit()

    return SyncRecipeResponse(
        recipe_id=recipe_id,
        recipe_name=recipe.name if recipe else "Receta",
        was_new=was_new,
        total_cost=float(recipe.total_cost) if recipe and recipe.total_cost else 0.0,
        ingredients_count=len(recipe.ingredients) if recipe else 0,
    )


@router.post(
    "/documents/{doc_id}/sync_recipes", response_model=SyncRecipesResponse, dependencies=protected
)
def sync_recipes(
    doc_id: UUID, body: SyncRecipesRequest | None, request: Request, db: Session = Depends(get_db)
):
    from app.models.recipes import Recipe

    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    data = _get_doc_import_data(doc)
    available_sheets = get_available_recipe_sheets(data)
    if not available_sheets:
        raise HTTPException(
            status_code=422, detail="El documento no contiene hojas separadas para sincronizar."
        )

    force = bool(body.force) if body else False
    synced_sheets = _get_synced_sheet_map(db, doc)
    processed_count = 0
    skipped_count = 0
    processed_sheet_names: list[str] = []
    results: list[SyncRecipeSheetResponse] = []

    for sheet_name in available_sheets:
        previous_sync = synced_sheets.get(sheet_name)
        if previous_sync and not force:
            skipped_count += 1
            results.append(
                SyncRecipeSheetResponse(
                    sheet_name=sheet_name,
                    status="skipped",
                    recipe_id=(
                        UUID(previous_sync["recipe_id"]) if previous_sync.get("recipe_id") else None
                    ),
                    recipe_name=previous_sync.get("recipe_name"),
                    message="Hoja ya sincronizada",
                )
            )
            continue

        recipe_id, was_new = upsert_recipe_from_import(doc, db, sheet_override=sheet_name)
        if not recipe_id:
            results.append(
                SyncRecipeSheetResponse(
                    sheet_name=sheet_name,
                    status="error",
                    message="No se pudo extraer una receta valida de esta hoja.",
                )
            )
            continue

        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        doc.synced_recipe_id = recipe_id
        crud.add_log(
            db,
            doc.id,
            "SYNC_PRODUCTION",
            user_id,
            {
                "recipe_id": str(recipe_id),
                "recipe_name": recipe.name if recipe else None,
                "sheet_used": sheet_name,
                "was_new": was_new,
                "batch": True,
            },
        )

        processed_count += 1
        processed_sheet_names.append(sheet_name)
        results.append(
            SyncRecipeSheetResponse(
                sheet_name=sheet_name,
                status="created" if was_new else "updated",
                recipe_id=recipe_id,
                recipe_name=recipe.name if recipe else sheet_name,
                was_new=was_new,
                total_cost=float(recipe.total_cost) if recipe and recipe.total_cost else 0.0,
                ingredients_count=len(recipe.ingredients) if recipe else 0,
            )
        )

    crud.add_log(
        db,
        doc.id,
        "SYNC_PRODUCTION_BATCH",
        user_id,
        {
            "processed_count": processed_count,
            "skipped_count": skipped_count,
            "sheet_count": len(available_sheets),
            "sheets": processed_sheet_names,
            "force": force,
        },
    )
    primary_recipe_id = None
    for item in results:
        if item.recipe_id:
            primary_recipe_id = item.recipe_id
            break
    crud.mark_document_staging_imported(
        db,
        doc.id,
        target_table="recipes",
        target_id=primary_recipe_id,
    )
    db.commit()

    return SyncRecipesResponse(
        total_sheets=len(available_sheets),
        processed_count=processed_count,
        skipped_count=skipped_count,
        results=results,
    )


@router.get(
    "/documents/{doc_id}/line-match-candidates",
    response_model=DocumentLineMatchesResponse,
    dependencies=protected,
)
def get_document_line_match_candidates(
    doc_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    tenant_id = _tenant_id(request)
    return DocumentLineMatchesResponse(lines=_build_document_line_matches(db, tenant_id, doc))


@router.post(
    "/documents/{doc_id}/save", response_model=SaveDocumentResponse, dependencies=protected
)
def save_document(
    doc_id: UUID,
    body: SaveDocumentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    destination = body.destination or _infer_save_destination(doc, db)
    doc_import_data = (
        _require_confirmed_doc_import_data(doc, destination)
        if destination in ("expense", "supplier_invoice")
        else _get_doc_import_data(doc)
    )
    _require_routing_ready(doc, db, destination)

    if destination == "recipe":
        data = doc_import_data
        available_sheets = get_available_recipe_sheets(data)
        if not available_sheets:
            raise HTTPException(
                status_code=422,
                detail="Este documento no contiene una receta o costeo sincronizable.",
            )
        if len(available_sheets) > 1:
            sync_result = sync_recipes(doc_id, SyncRecipesRequest(force=False), request, db)
            record_ids = [str(item.recipe_id) for item in sync_result.results if item.recipe_id]
            result = SaveDocumentResponse(
                target="recipes",
                destination="recipe",
                status="created" if sync_result.processed_count > 0 else "skipped",
                record_id=record_ids[-1] if record_ids else None,
                record_ids=record_ids,
                message=(
                    f"Se guardaron {sync_result.processed_count} hojas en recetas."
                    if sync_result.processed_count > 0
                    else "Todas las hojas ya estaban sincronizadas."
                ),
            )
        else:
            sync_result = sync_recipe(doc_id, SyncRecipeRequest(force=False), request, db)
            result = SaveDocumentResponse(
                target="recipes",
                destination="recipe",
                status="created" if sync_result.was_new else "updated",
                record_id=str(sync_result.recipe_id),
                record_ids=[str(sync_result.recipe_id)],
                message=f"Receta guardada: {sync_result.recipe_name}",
            )
    elif destination == "supplier_invoice":
        purchase_result = _save_document_to_purchase(
            db=db,
            tenant_id=doc.tenant_id,
            user_id=user_id,
            doc=doc,
            warehouse_id=body.warehouse_id,
            notes=body.notes,
            update_stock=body.update_stock,
            line_matches=body.line_matches,
        )
        # Also create expense record for payment tracking
        expense_result = _save_document_to_expense(
            db=db,
            tenant_id=doc.tenant_id,
            user_id=user_id,
            doc=doc,
            body=SaveDocumentRequest(
                destination="supplier_invoice",
                payment_status=body.payment_status,
                paid_amount=body.paid_amount,
                pending_amount=body.pending_amount,
                payment_method=body.payment_method,
                payment_method_id=body.payment_method_id,
                paid_at=body.paid_at,
                notes=body.notes,
            ),
        )
        record_ids = [str(purchase_result["purchase_id"])]
        if expense_result.record_id:
            record_ids.append(expense_result.record_id)
        purchase_message = purchase_result.get("message", "Compra registrada.")
        expense_message = (
            f"Gasto creado ({body.payment_status})."
            if expense_result.status == "created"
            else "El gasto ya existia y no se duplico."
        )
        result = SaveDocumentResponse(
            target="purchases",
            destination="supplier_invoice",
            status=purchase_result["status"],
            record_id=str(purchase_result["purchase_id"]),
            record_ids=record_ids,
            message=f"{purchase_message} {expense_message}".strip(),
        )
    else:
        result = _save_document_to_expense(
            db=db,
            tenant_id=doc.tenant_id,
            user_id=user_id,
            doc=doc,
            body=SaveDocumentRequest(
                destination=destination,
                payment_status=body.payment_status,
                paid_amount=body.paid_amount,
                pending_amount=body.pending_amount,
                payment_method=body.payment_method,
                payment_method_id=body.payment_method_id,
                paid_at=body.paid_at,
                notes=body.notes,
            ),
        )

    resolved_payment_method = None
    resolved_payment_method_id = None
    if destination != "recipe":
        detected_payment_method = _get_document_payment_method(doc_import_data)
        resolved_payment_method, resolved_payment_method_id = _resolve_payment_method(
            db,
            doc.tenant_id,
            body.payment_method_id,
            body.payment_method or detected_payment_method,
        )

    payment_snapshot = (
        _normalize_payment_details(_get_document_total(doc), body)
        if destination != "recipe"
        else {"status": None, "paid_amount": None, "pending_amount": None}
    )
    confirmed = dict(doc_import_data)
    confirmed["_save"] = {
        "destination": destination,
        "target": result.target,
        "status": result.status,
        "record_id": result.record_id,
        "record_ids": result.record_ids,
        "payment_status": payment_snapshot.get("status"),
        "paid_amount": payment_snapshot.get("paid_amount"),
        "pending_amount": payment_snapshot.get("pending_amount"),
        "payment_method": resolved_payment_method,
        "payment_method_id": (
            str(resolved_payment_method_id) if resolved_payment_method_id else None
        ),
        "paid_at": body.paid_at,
        "notes": body.notes,
        "line_matches": [
            {
                "line_index": match.line_index,
                "product_id": str(match.product_id) if match.product_id else None,
                "persist_alias": bool(match.persist_alias),
            }
            for match in body.line_matches
        ],
        "saved_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    primary_target_id = None
    if result.record_id:
        try:
            primary_target_id = UUID(str(result.record_id))
        except (TypeError, ValueError):
            primary_target_id = None
    new_estado = "CONFIRMED" if destination == "recipe" else "IMPORTED"
    update_fields: dict = {
        "datos_confirmados": confirmed,
        "estado": new_estado,
    }
    if destination != "recipe":
        update_fields["saved_as"] = destination
        update_fields["saved_record_id"] = primary_target_id
        update_fields["saved_at"] = datetime.datetime.now(datetime.UTC)
    crud.update_documento(db, doc, update_fields)
    crud.mark_document_staging_imported(
        db,
        doc.id,
        target_table=result.target,
        target_id=primary_target_id,
    )
    _sync_batch_projection(db, doc.id, new_estado)
    crud.add_log(
        db,
        doc.id,
        "SAVE_DESTINATION",
        user_id,
        {
            "destination": destination,
            "target": result.target,
            "status": result.status,
            "record_id": result.record_id,
            "record_ids": result.record_ids,
            "payment_status": payment_snapshot.get("status"),
            "paid_amount": payment_snapshot.get("paid_amount"),
            "pending_amount": payment_snapshot.get("pending_amount"),
            "payment_method": resolved_payment_method,
            "payment_method_id": (
                str(resolved_payment_method_id) if resolved_payment_method_id else None
            ),
            "paid_at": body.paid_at,
        },
    )
    record_routing_signal(
        db,
        doc,
        user_id=user_id,
        event="save",
        chosen_destination=destination,
        payload={
            "target": result.target,
            "status": result.status,
            "record_id": result.record_id,
            "record_ids": result.record_ids,
            "payment_status": payment_snapshot.get("status"),
            "paid_amount": payment_snapshot.get("paid_amount"),
            "pending_amount": payment_snapshot.get("pending_amount"),
        },
    )
    db.commit()
    return result


@router.patch("/documents/{doc_id}/edit", response_model=DocumentoOut, dependencies=protected)
def edit_document_fields(
    doc_id: UUID, body: EditFieldsRequest, request: Request, db: Session = Depends(get_db)
):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Merge with existing extracted data and rebuild the document projection so
    # edited scalar fields affect both the detail payload and the summary fields.
    current = doc.datos_extraidos or {}
    previous: dict[str, object | None] = {}
    if isinstance(current, dict):
        previous = {k: current.get(k) for k in body.campos}
        current.update(body.campos)

    tenant_id = _tenant_id(request)
    aliases = get_field_aliases(db, tenant_id=tenant_id)
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    canonical_document, projection = build_document_projection(
        current,
        doc_type=doc.tipo_documento_detectado,
        source_format=doc.tipo_archivo,
        field_aliases=aliases,
        canonical_fields=canonical_fields,
    )

    raw_ai_json = dict(doc.raw_ai_json) if isinstance(doc.raw_ai_json, dict) else {}
    raw_ai_json["canonical_document"] = canonical_document

    update_payload = {
        "datos_extraidos": current,
        "raw_ai_json": _json_safe(raw_ai_json),
        **projection,
    }
    crud.update_documento(db, doc, update_payload)
    _capture_routing_signal(
        doc,
        db,
        user_id,
        event="edit",
        changed_fields=list(body.campos.keys()),
    )
    crud.add_log(
        db,
        doc.id,
        "EDIT",
        user_id,
        {"campos_modificados": body.campos, "valores_anteriores": previous},
    )
    db.commit()
    _attach_document_routing(doc, db)
    _attach_document_review_hints(doc, db)
    _attach_document_activity_meta(doc)
    return doc


@router.post("/documents/{doc_id}/reject", response_model=DocumentoOut, dependencies=protected)
def reject_document(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    crud.update_documento(db, doc, {"estado": "FAILED"})
    _sync_batch_projection(db, doc.id, "FAILED")
    crud.add_log(db, doc.id, "REJECT", user_id)
    db.commit()
    _attach_document_routing(doc, db)
    _attach_document_review_hints(doc, db)
    return doc


@router.post(
    "/documents/{doc_id}/save-as-products",
    response_model=SaveProductsFromDocumentResponse,
    dependencies=protected,
)
def save_document_as_products(
    doc_id: UUID,
    body: SaveProductsFromDocumentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    data = _get_doc_import_data(doc)
    candidates, resolved_sheet = build_product_candidates(
        data,
        sheet_name=body.sheet_name,
        row_indexes=body.row_indexes,
        default_category_name=body.category_name,
        detection_config=load_product_sheet_detection_config(db),
    )
    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="No se encontraron filas validas para crear productos.",
        )

    result = save_product_candidates(
        db=db,
        tenant_id=doc.tenant_id,
        candidates=candidates,
        source_document_id=doc_id,
    )

    save_meta = {
        "destination": "products",
        "target": "products",
        "status": (
            "created"
            if result["created"] > 0
            else ("updated" if result.get("updated", 0) > 0 else "skipped")
        ),
        "record_ids": result["product_ids"],
        "sheet_name": resolved_sheet,
        "category_name": body.category_name,
        "saved_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    confirmed = dict(data)
    confirmed["_save"] = save_meta

    crud.update_documento(
        db,
        doc,
        {
            "datos_confirmados": confirmed,
            "estado": "IMPORTED",
            "tipo_documento_detectado": "PRODUCTS",
            "confianza_clasificacion": 1.0,
            "requiere_revision": False,
            "saved_as": "products",
            "saved_record_id": None,
            "saved_at": datetime.datetime.now(datetime.UTC),
        },
    )
    primary_product_id = None
    if result["product_ids"]:
        try:
            primary_product_id = UUID(str(result["product_ids"][0]))
        except (TypeError, ValueError):
            primary_product_id = None
    crud.mark_document_staging_imported(
        db,
        doc.id,
        target_table="products",
        target_id=primary_product_id,
    )
    _sync_batch_projection(db, doc.id, "IMPORTED")
    crud.add_log(
        db,
        doc.id,
        "SAVE_PRODUCTS",
        user_id,
        {
            **save_meta,
            "created": result["created"],
            "updated": result.get("updated", 0),
            "skipped_existing": result["skipped_existing"],
            "skipped_invalid": result["skipped_invalid"],
            "skipped_names": result["skipped_names"],
            "selected_rows": body.row_indexes,
        },
    )
    db.commit()

    return SaveProductsFromDocumentResponse(
        sheet_name=resolved_sheet,
        category_name=body.category_name,
        created=result["created"],
        updated=result.get("updated", 0),
        skipped_existing=result["skipped_existing"],
        skipped_invalid=result["skipped_invalid"],
        product_ids=result["product_ids"],
        skipped_names=result["skipped_names"],
    )


@router.get("/doc-categories", dependencies=protected)
def get_doc_categories(db: Session = Depends(get_db)):
    """Returns the doc_type→category keyword map from DB for client-side use."""
    from .category_loader import get_doc_categories

    return get_doc_categories(db)


@router.get("/file-support", dependencies=protected)
def get_file_support(db: Session = Depends(get_db)):
    return load_file_support_config(db)


@router.get("/product-sheet-config", dependencies=protected)
def get_product_sheet_config(db: Session = Depends(get_db)):
    return load_product_sheet_detection_config(db)


@router.get("/dashboard", response_model=DashboardStats, dependencies=protected)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id(request)
    counts = crud.count_documentos(db, tenant_id)
    return DashboardStats(
        total=sum(counts.values()),
        pendientes=counts.get("PENDING", 0) + counts.get("PROCESSING", 0),
        en_revision=counts.get("REVIEW", 0),
        confirmados=counts.get("CONFIRMED", 0),
        fallidos=counts.get("FAILED", 0),
    )


@router.get("/batches", response_model=list[BatchSummaryOut], dependencies=protected)
def list_batches(
    request: Request,
    active_only: bool = Query(default=False),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    tenant_id = _tenant_id(request)
    batches = crud.list_batches(db, tenant_id, active_only=active_only, limit=limit)
    return [BatchSummaryOut(**crud.summarize_batch(db, batch)) for batch in batches]


@router.get("/batches/{batch_id}", response_model=BatchDetailOut, dependencies=protected)
def get_batch(batch_id: UUID, request: Request, db: Session = Depends(get_db)):
    tenant_id = _tenant_id(request)
    batch = crud.get_batch(db, batch_id, tenant_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    return BatchDetailOut(**crud.serialize_batch_detail(db, batch))


@router.get("/batches/{batch_id}/stream")
async def batch_status_stream(
    batch_id: UUID,
    request: Request,
    token: str = Query(..., description="JWT de acceso para EventSource"),
):
    import asyncio
    import json

    import redis.asyncio as aioredis  # type: ignore
    from fastapi.responses import StreamingResponse

    from app.config.database import SessionLocal
    from app.core.jwt_provider import get_token_service

    try:
        claims = get_token_service().decode_and_validate(token, expected_type="access")
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")

    tenant_raw = claims.get("tenant_id")
    if not tenant_raw:
        raise HTTPException(status_code=401, detail="tenant_id ausente en token")

    tenant_id = UUID(str(tenant_raw))
    terminal_states = {"COMPLETED", "FAILED", "PARTIAL"}
    channel = f"imp:batch:{batch_id}"
    redis_url = os.getenv("REDIS_URL") or os.getenv("DEV_REDIS_URL") or "redis://localhost:6379/0"

    async def event_generator():
        pubsub = None
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)

            with SessionLocal() as db_session:
                batch = crud.get_batch(db_session, batch_id, tenant_id)
                if batch is None:
                    yield 'event: error\ndata: {"detail":"not_found"}\n\n'
                    return
                initial_payload = crud.serialize_batch_detail(db_session, batch)

            yield f"data: {json.dumps(_json_safe(initial_payload))}\n\n"
            if initial_payload["estado"] in terminal_states:
                return

            max_wait_seconds = float(os.getenv("IMPORTADOR_BATCH_STREAM_MAX_WAIT_SECONDS", "7200"))
            loop = asyncio.get_running_loop()
            deadline = loop.time() + max_wait_seconds

            while True:
                if await request.is_disconnected():
                    return

                remaining = deadline - loop.time()
                if remaining <= 0:
                    yield 'event: timeout\ndata: {"detail":"timeout"}\n\n'
                    return

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=min(15.0, remaining),
                )
                if message and message.get("type") == "message":
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8", errors="ignore")
                    yield f"data: {data}\n\n"
                    try:
                        parsed = json.loads(data)
                    except Exception:
                        parsed = None
                    if isinstance(parsed, dict) and parsed.get("estado") in terminal_states:
                        return

                yield ": keep-alive\n\n"
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                except Exception:
                    pass
                try:
                    await pubsub.close()
                except Exception:
                    pass
            try:
                await redis_client.aclose()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sync_batch_projection(
    db: Session, doc_id: UUID, estado: str, error_detalle: str | None = None
) -> None:
    from .tasks import publish_batch_update

    for batch_id in crud.touch_batch_items_for_document(
        db,
        doc_id,
        estado=estado,
        error_detalle=error_detalle,
    ):
        crud.refresh_batch_status(db, batch_id)
        publish_batch_update(db, batch_id)


def _safe_float(val) -> float | None:
    return safe_floatish(val)


@router.post(
    "/documents/{doc_id}/save-as-daily-log",
    response_model=SaveDailyLogResponse,
    dependencies=protected,
)
async def save_as_daily_log(
    doc_id: UUID,
    body: SaveDailyLogRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Guarda la hoja REGISTRO del documento como historial diario de producción.
    La fecha se infiere del nombre del archivo (DD-MM-YY) o se puede pasar en el body.
    No afecta el stock actual — es solo historial analítico.
    """
    from datetime import date as date_type

    from .daily_log_service import _parse_date_from_filename, resolve_registro_rows, save_daily_log

    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="documento_no_encontrado")

    # Resolver fecha
    log_date: date_type | None = None
    if body.log_date:
        try:
            log_date = date_type.fromisoformat(body.log_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="fecha_invalida (usar YYYY-MM-DD)")
    else:
        log_date = _parse_date_from_filename(doc.nombre_archivo)

    if not log_date:
        raise HTTPException(
            status_code=400,
            detail="no_se_pudo_inferir_fecha — incluye log_date en el body (YYYY-MM-DD)",
        )

    rows = await resolve_registro_rows(db, tenant_id, doc, user_id=user_id)
    if not rows:
        raise HTTPException(
            status_code=422,
            detail="sin_filas_registro — el documento no tiene una hoja REGISTRO con datos válidos",
        )

    result = save_daily_log(
        db=db,
        tenant_id=tenant_id,
        document_id=doc_id,
        log_date=log_date,
        rows=rows,
    )
    crud.mark_document_staging_imported(
        db,
        doc.id,
        target_table="daily_production_logs",
        target_id=None,
    )
    db.commit()
    return SaveDailyLogResponse(**result)


def _match_product(db: Session, tenant_id: UUID, description: str):
    """Fuzzy product lookup by description → (Product, conversion_factor) or (None, 1).

    import_aliases format on Product:
      [{"name": "HARINA TRADICION PREMIUM 50 KG", "factor": 50, "unit": "kg"}, ...]
    factor = how many inventory-units per 1 invoice-unit.
    """
    from app.models.core.products import Product

    desc_norm = _norm_import_text(description)
    desc_core = _strip_pack_tokens(description)
    if not desc_norm:
        return None, 1.0

    products = (
        db.query(Product)
        .filter(Product.tenant_id == str(tenant_id), Product.active == True)  # noqa: E712
        .all()
    )

    # 1) Check import_aliases first (exact or substring)
    for p in products:
        aliases = p.import_aliases or []
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if not isinstance(alias, dict):
                continue
            alias_name = _norm_import_text(str(alias.get("name") or ""))
            if not alias_name:
                continue
            if alias_name == desc_norm or alias_name in desc_norm or desc_norm in alias_name:
                factor = float(alias.get("factor") or 1)
                return p, factor

    # 2) Exact name match
    for p in products:
        if _norm_import_text(p.name) == desc_norm:
            factor = _infer_pack_conversion_factor(description, getattr(p, "unit", None))
            return p, factor

    # 3) Substring match
    for p in products:
        pn = _norm_import_text(p.name)
        if desc_norm in pn or pn in desc_norm:
            factor = _infer_pack_conversion_factor(description, getattr(p, "unit", None))
            return p, factor

    # 4) Core-name match ignoring presentation tokens like "50 KG"
    if desc_core:
        for p in products:
            pn_core = _strip_pack_tokens(p.name)
            if not pn_core:
                continue
            if desc_core == pn_core or desc_core in pn_core or pn_core in desc_core:
                factor = _infer_pack_conversion_factor(description, getattr(p, "unit", None))
                return p, factor

    return None, 1.0


# ---------------------------------------------------------------------------
# Async upload via Celery (run-async)
# ---------------------------------------------------------------------------
class RunAsyncResponse(BaseModel):
    id: UUID
    batch_id: UUID
    batch_item_id: UUID
    estado: str
    nombre_archivo: str
    action: Literal["CREATED", "REUSED", "REPROCESS"] = "CREATED"
    message: str | None = None


@router.post("/run-async", response_model=list[RunAsyncResponse], dependencies=protected)
async def run_async(
    request: Request,
    files: list[UploadFile] = File(...),
    force: bool = Query(default=False),
    recipe_snapshot_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Encola los archivos para procesamiento asincrono via Celery y batch tracking."""
    from .batch_service import enqueue_async_batch

    return await enqueue_async_batch(
        files=files,
        tenant_id=_tenant_id(request),
        user_id=_user_id(request),
        force=force,
        recipe_snapshot_id=recipe_snapshot_id,
        db=db,
    )


# ---------------------------------------------------------------------------
# Purge all importador history (tenant-scoped)
# ---------------------------------------------------------------------------
@router.delete("/purge-all", dependencies=protected)
def purge_all_importador(request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text as sql_text

    tenant_id = _tenant_id(request)
    tid = str(tenant_id)

    tenant_tables = [
        "imp_batch_item",
        "imp_batch_import",
        "icu_recipe_snapshot",
        "icu_recipe_draft",
        "imp_documento",
        "icu_recipe",
        "import_items",
        "import_resolutions",
        "posting_registry",
        "import_ocr_jobs",
        "import_batches",
        "import_mappings",
        "import_column_mappings",
    ]
    fk_tables = [
        ("imp_log_cambios", "documento_id", "SELECT id FROM imp_documento WHERE tenant_id = :tid"),
        ("import_attachments", "item_id", "SELECT id FROM import_items WHERE tenant_id = :tid"),
        (
            "import_item_corrections",
            "item_id",
            "SELECT id FROM import_items WHERE tenant_id = :tid",
        ),
        ("import_lineage", "item_id", "SELECT id FROM import_items WHERE tenant_id = :tid"),
    ]

    deleted: dict[str, int] = {}

    for table_name, fk_column, subquery in fk_tables:
        try:
            result = db.execute(
                sql_text(f"DELETE FROM {table_name} WHERE {fk_column} IN ({subquery})"),
                {"tid": tid},
            )
            if result.rowcount:
                deleted[table_name] = result.rowcount
        except Exception:
            logger.debug("purge skip %s (may not exist)", table_name, exc_info=True)

    for table_name in tenant_tables:
        try:
            result = db.execute(
                sql_text(f"DELETE FROM {table_name} WHERE tenant_id = :tid"),
                {"tid": tid},
            )
            if result.rowcount:
                deleted[table_name] = result.rowcount
        except Exception:
            logger.debug("purge skip %s (may not exist)", table_name, exc_info=True)

    db.commit()
    total = sum(deleted.values())
    logger.info("purge_all_importador tenant=%s deleted=%s", tenant_id, deleted)
    return {"deleted_total": total, "tables": deleted}


# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE REPROCESADO ITERATIVO
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/documents/{doc_id}/staging/summary",
    response_model=StagingLineSummary,
    dependencies=protected,
)
def get_staging_summary(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Estado actual de todas las líneas de staging de un documento."""
    _tenant_id(request)  # verifica acceso
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return count_staging_lines(db, doc_id)


@router.get(
    "/documents/{doc_id}/staging",
    response_model=list[StagingLineOut],
    dependencies=protected,
)
def list_staging_lines(
    doc_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    estado: list[str] = Query(default=[]),
    error_code: str | None = Query(default=None),
    sheet: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Lista líneas de staging con filtros. Base para la tabla de revisión."""
    _tenant_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    from sqlalchemy import select

    from app.models.importador import ImpStagingLine

    q = select(ImpStagingLine).where(ImpStagingLine.documento_id == doc_id)
    if estado:
        q = q.where(ImpStagingLine.estado.in_(estado))
    if error_code:
        q = q.where(ImpStagingLine.error_code == error_code)
    if sheet:
        q = q.where(ImpStagingLine.sheet_name == sheet)
    q = q.order_by(ImpStagingLine.line_number).limit(limit).offset(offset)
    return list(db.scalars(q).all())


@router.get(
    "/documents/{doc_id}/staging/field-analysis",
    response_model=FieldAnalysisResponse,
    dependencies=protected,
)
def get_field_analysis(
    doc_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    estados: list[str] = Query(default=["INVALID", "PENDING", "REVIEW"]),
    error_codes: list[str] = Query(default=[]),
    sheet: str | None = Query(default=None),
):
    """
    Analiza qué campos tienen problemas en las líneas indicadas.
    Paso previo OBLIGATORIO antes de elegir qué campos reprocesar.
    Muestra al usuario el estado real de sus datos — no una lista genérica.
    """
    _tenant_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    scope = IterationScopeIn(
        mode="SELECTIVE",
        filter_estados=estados,
        filter_error_codes=error_codes,
        filter_sheet=sheet,
    )
    lines = fetch_lines_for_scope(db, doc_id, scope)
    error_map = load_error_affected_fields(db)
    analysis = build_field_analysis(lines, error_map)
    return analysis


@router.get(
    "/documents/{doc_id}/iterations",
    response_model=list[IterationOut],
    dependencies=protected,
)
def list_iterations(doc_id: UUID, request: Request, db: Session = Depends(get_db)):
    """Historial de todas las iteraciones de un documento."""
    _tenant_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    from sqlalchemy import select

    from app.models.importador import ImpIteration

    return list(
        db.scalars(
            select(ImpIteration)
            .where(ImpIteration.documento_id == doc_id)
            .order_by(ImpIteration.iteration_num)
        ).all()
    )


@router.post(
    "/documents/{doc_id}/iterate",
    response_model=IterationResultOut,
    dependencies=protected,
)
def iterate_document(
    doc_id: UUID,
    body: RunIterationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Ejecuta una iteración de reprocesado sobre el documento.
    Solo procesa las líneas que corresponden al scope.
    Solo modifica los campos seleccionados — preserva todo lo demás.
    """
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    aliases = get_field_aliases(db, tenant_id=tenant_id)
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    result = run_iteration(db, doc, tenant_id, user_id, body.scope, aliases, canonical_fields)
    db.commit()
    return result


@router.post(
    "/documents/{doc_id}/review-session",
    response_model=ReviewSessionOut,
    dependencies=protected,
)
def create_review_session(
    doc_id: UUID,
    body: ReviewSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Crea una sesión de revisión selectiva.
    Calcula preview_count: cuántas líneas afecta el scope antes de ejecutar.
    El usuario puede revisar el impacto antes de confirmar.
    """
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    scope = IterationScopeIn(
        mode=(
            "SELECTIVE"
            if any(
                [
                    body.filter_estados,
                    body.filter_error_codes,
                    body.filter_campos,
                    body.filter_columns,
                    body.filter_lines,
                    body.filter_sheet,
                ]
            )
            else "ALL"
        ),
        filter_estados=body.filter_estados,
        filter_error_codes=body.filter_error_codes,
        filter_campos=body.filter_campos,
        filter_columns=body.filter_columns,
        filter_lines=body.filter_lines,
        filter_sheet=body.filter_sheet,
    )
    preview_count = count_lines_for_scope(db, doc_id, scope)

    from app.models.importador import ImpReviewSession

    session = ImpReviewSession(
        tenant_id=tenant_id,
        documento_id=doc_id,
        initiated_by=user_id,
        filter_estados=body.filter_estados,
        filter_error_codes=body.filter_error_codes,
        filter_campos=body.filter_campos,
        filter_columns=body.filter_columns,
        filter_lines=body.filter_lines,
        filter_sheet=body.filter_sheet,
        preview_count=preview_count,
        estado="PENDING",
    )
    db.add(session)
    db.flush()
    db.commit()
    return session


@router.post(
    "/documents/{doc_id}/review-session/{session_id}/run",
    response_model=IterationResultOut,
    dependencies=protected,
)
def run_review_session(
    doc_id: UUID,
    session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Ejecuta la iteración definida por la sesión de revisión."""
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    doc = crud.get_documento(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    from sqlalchemy import select

    from app.models.importador import ImpReviewSession

    session = db.scalars(
        select(ImpReviewSession).where(
            ImpReviewSession.id == session_id,
            ImpReviewSession.documento_id == doc_id,
        )
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de revisión no encontrada")
    if session.estado != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"La sesión ya fue ejecutada (estado: {session.estado})",
        )

    scope = IterationScopeIn(
        mode=(
            "SELECTIVE"
            if any(
                [
                    session.filter_estados,
                    session.filter_error_codes,
                    session.filter_campos,
                    session.filter_columns,
                    session.filter_lines,
                    session.filter_sheet,
                ]
            )
            else "ALL"
        ),
        filter_estados=list(session.filter_estados or []),
        filter_error_codes=list(session.filter_error_codes or []),
        filter_campos=list(session.filter_campos or []),
        filter_columns=list(session.filter_columns or []),
        filter_lines=list(session.filter_lines or []),
        filter_sheet=session.filter_sheet,
    )

    aliases = get_field_aliases(db, tenant_id=tenant_id)
    canonical_fields = get_canonical_fields(db, tenant_id=tenant_id)
    session.estado = "RUNNING"
    db.flush()

    result = run_iteration(db, doc, tenant_id, user_id, scope, aliases, canonical_fields)

    session.estado = "DONE"
    session.linked_iteration_id = result.iteration_id
    db.commit()
    return result


@router.patch(
    "/documents/{doc_id}/staging/{line_id}",
    response_model=StagingLineOut,
    dependencies=protected,
)
def patch_staging_line(
    doc_id: UUID,
    line_id: UUID,
    body: StagingLinePatch,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    El usuario corrige una línea individual manualmente.
    Puede cambiar el estado, los campos en revisión, o los datos normalizados.
    """
    _tenant_id(request)
    from sqlalchemy import select

    from app.models.importador import ImpStagingLine

    line = db.scalars(
        select(ImpStagingLine).where(
            ImpStagingLine.id == line_id,
            ImpStagingLine.documento_id == doc_id,
        )
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Línea de staging no encontrada")

    if body.estado is not None:
        line.estado = body.estado
    if body.campos_revision is not None:
        line.campos_revision = body.campos_revision
    if body.normalized_data is not None:
        existing = dict(line.normalized_data or {})
        existing.update(body.normalized_data)
        line.normalized_data = existing

    db.flush()
    db.commit()
    return line


@router.patch(
    "/documents/{doc_id}/staging/bulk",
    response_model=dict,
    dependencies=protected,
)
def bulk_patch_staging_lines(
    doc_id: UUID,
    body: BulkStagingPatch,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Marca múltiples líneas para reprocesar/revisar/omitir en bloque.
    El usuario selecciona líneas en la tabla y aplica una acción.
    """
    _tenant_id(request)
    from sqlalchemy import select

    from app.models.importador import ImpStagingLine

    lines = list(
        db.scalars(
            select(ImpStagingLine).where(
                ImpStagingLine.documento_id == doc_id,
                ImpStagingLine.id.in_([str(lid) for lid in body.line_ids]),
            )
        ).all()
    )

    updated = 0
    for line in lines:
        line.estado = body.estado
        if body.campos_revision is not None:
            line.campos_revision = body.campos_revision
        updated += 1

    db.flush()
    db.commit()
    return {"updated": updated, "estado": body.estado}
