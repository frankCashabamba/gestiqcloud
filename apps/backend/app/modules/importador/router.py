"""API endpoints for Importador Contable Universal."""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

from . import crud
from .ai_classifier import CONFIDENCE_THRESHOLD, analyze_document
from .auto_recipe import resolve_auto_recipe
from .document_fields import (
    detect_document_currency,
    detect_document_date,
    detect_document_subtotal,
    detect_document_tax,
    detect_document_total,
    get_data_value,
    safe_floatish,
)
from .ocr_service import detect_file_type, extract_text_from_file, iter_zip_entries
from .product_import_service import build_product_candidates, save_product_candidates
from .recipe_sync import get_available_recipe_sheets, upsert_recipe_from_import
from .schemas import (
    BatchDetailOut,
    BatchSummaryOut,
    ConfirmRequest,
    DashboardStats,
    DocumentoDetailOut,
    DocumentoListOut,
    DocumentoOut,
    EditFieldsRequest,
    SaveDailyLogRequest,
    SaveDailyLogResponse,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SaveProductsFromDocumentRequest,
    SaveProductsFromDocumentResponse,
    SyncRecipeResponse,
    SyncRecipeSheetResponse,
    SyncRecipesResponse,
    UploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/importador", tags=["Importador"])
protected = [Depends(with_access_claims), Depends(require_scope("tenant"))]
SUPPORTED_PAYMENT_METHODS = {
    "bank",
    "cash",
    "card",
    "transfer",
    "direct_debit",
    "check",
    "other",
}


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


def _get_synced_sheet_map(db: Session, doc) -> dict[str, dict]:
    from app.models.recipes import Recipe

    synced: dict[str, dict] = {}
    recipe_to_sheet: dict[str, str] = {}
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
        existing_sheet = recipe_to_sheet.get(recipe_id)
        if existing_sheet and existing_sheet != sheet_name:
            continue
        recipe_to_sheet[recipe_id] = sheet_name
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


def _coerce_user_uuid(user_id: str):
    import uuid

    try:
        return UUID(str(user_id))
    except (TypeError, ValueError):
        return uuid.uuid4()


def _infer_save_destination(doc, db: Session) -> str:
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

    supplier_name = _first_non_empty(
        doc.proveedor_detectado,
        get_data_value(data, "proveedor", "vendor_name", "vendor", "supplier", "emisor", "issuer"),
    )
    supplier_tax_id = _first_non_empty(
        doc.ruc_detectado,
        get_data_value(data, "ruc", "tax_id", "vendor_tax_id", "supplier_tax_id", "ruc_proveedor"),
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


def _get_document_total(doc) -> float | None:
    data = _get_doc_import_data(doc)
    return _first_non_empty(doc.monto_total, detect_document_total(data))


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


def _save_document_to_expense(
    db: Session,
    tenant_id: UUID,
    user_id: str,
    doc,
    body: SaveDocumentRequest,
) -> SaveDocumentResponse:
    from app.models.expenses.expense import Expense
    from app.modules.expenses.infrastructure.repositories import ExpenseRepo

    data = _get_doc_import_data(doc)
    total = _get_document_total(doc)
    vat = detect_document_tax(data) or 0.0
    subtotal = detect_document_subtotal(data)

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
    payment_method = (
        body.payment_method.strip().lower()
        if body.payment_method and body.payment_method.strip().lower() in SUPPORTED_PAYMENT_METHODS
        else None
    )

    supplier_id, supplier_name = _lookup_supplier(db, tenant_id, doc, data)
    invoice_number = _first_non_empty(
        get_data_value(
            data,
            "numero_factura",
            "invoice_number",
            "invoice_no",
            "numero",
            "factura",
            "comprobante",
        ),
    )
    concept = _first_non_empty(
        get_data_value(
            data, "concepto", "descripcion", "detalle", "description", "notes", "productos"
        ),
    )
    if not concept:
        prefix = "Factura proveedor" if body.destination == "supplier_invoice" else "Gasto"
        concept = f"{prefix} {supplier_name or doc.nombre_archivo}"
    concept = str(concept)[:255]

    expense_date = _parse_document_date(
        _first_non_empty(
            doc.fecha_documento,
            detect_document_date(data),
            datetime.date.today().isoformat(),
        )
    )
    category = str(
        _first_non_empty(
            "supplier_invoice" if body.destination == "supplier_invoice" else None,
            get_data_value(data, "category", "categoria"),
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
        body.notes or get_data_value(data, "notes", "nota", "observaciones"),
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
) -> dict:
    """Core purchase creation logic for document saves to purchases."""
    from decimal import ROUND_HALF_UP, Decimal

    from app.models.inventory.stock import StockItem, StockMove
    from app.models.inventory.warehouse import Warehouse
    from app.models.purchases.purchase import Purchase, PurchaseLine
    from app.services.inventory_costing import InventoryCostingService

    data = _get_doc_import_data(doc)
    line_items = data.get("line_items") or data.get("lineas") or data.get("items") or []
    if not line_items or not isinstance(line_items, list):
        line_items = []

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
        _first_non_empty(
            get_data_value(data, "doc_number", "numero_factura", "invoice_number", "invoice_no")
        )
        or doc.nombre_archivo
    )[:50]
    purchase_date = _parse_document_date(
        _first_non_empty(doc.fecha_documento, detect_document_date(data))
    )
    supplier_id, supplier_name = _lookup_supplier(db, tenant_id, doc, data)
    total = _get_document_total(doc) or 0.0
    vat = detect_document_tax(data) or 0.0
    subtotal = detect_document_subtotal(data)
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

    for item in line_items:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description") or item.get("descripcion") or "").strip()
        qty = float(item.get("quantity") or item.get("cantidad") or 0)
        unit_price = float(
            item.get("unit_price") or item.get("precio_unitario") or item.get("precio") or 0
        )
        total_price = float(
            item.get("total_price") or item.get("total") or item.get("importe") or qty * unit_price
        )
        if not description or qty <= 0:
            continue

        product, conv_factor = _match_product(db, tenant_id, description)
        stock_qty = qty * conv_factor  # convert invoice qty to inventory units
        logger.info(
            "save_purchase line: desc='%s' qty=%s matched=%s conv=%s stock_only=%s",
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


@router.post("/upload", response_model=list[UploadResponse], dependencies=protected)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    force: bool = Query(
        default=False, description="Si true, fuerza reprocesar aunque exista duplicado"
    ),
    db: Session = Depends(get_db),
):
    """Upload one or multiple files. Auto-classifies and extracts data."""
    tenant_id = _tenant_id(request)
    user_id = _user_id(request)
    results = []

    async def _process_single(file_bytes: bytes, filename: str, tipo_archivo: str | None = None):
        nonlocal db, tenant_id, user_id, results
        tipo_archivo = tipo_archivo or detect_file_type(filename)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = (
            None
            if force
            else crud.find_existing_documento(db, tenant_id, filename, len(file_bytes), file_hash)
        )
        if existing and existing.estado in ("CONFIRMED", "REVIEW"):
            # Reutiliza resultado anterior para ahorrar tiempo
            crud.add_log(
                db, existing.id, "SKIP_DUPLICATE", user_id, {"reason": "same hash_or_name"}
            )
            db.commit()
            results.append(
                UploadResponse(
                    id=existing.id,
                    estado=existing.estado,
                    tipo_documento_detectado=existing.tipo_documento_detectado,
                    confianza_clasificacion=existing.confianza_clasificacion,
                    requiere_revision=existing.requiere_revision,
                    datos_extraidos=existing.datos_extraidos,
                )
            )
            return

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
        crud.add_log(db, doc.id, "UPLOAD", user_id, {"filename": filename, "size": len(file_bytes)})
        db.commit()

        try:
            extraction = await extract_text_from_file(file_bytes, filename)
            text = extraction.get("text", "")
            structured = extraction.get("structured_data")
            sheet_profiles = extraction.get("sheet_profiles")
            headers_lower = []
            if sheet_profiles and isinstance(sheet_profiles, dict):
                for prof in sheet_profiles.values():
                    headers_lower.extend([h.lower() for h in prof.get("headers", [])])

            # Excel/CSV tiene filas ya parseadas — el LLM solo clasifica el tipo, no extrae datos
            has_structured = bool(structured and isinstance(structured, list) and sheet_profiles)

            headers_norm: list[str] = []
            headers_display: list[str] = []
            if has_structured:
                for prof in sheet_profiles.values():
                    headers_norm = prof.get("headers_norm") or []
                    headers_display = prof.get("headers") or headers_norm
                    break

            # Fingerprint para trazabilidad; NO usar el recipe_config guardado para Excel
            # (podría tener prompts de clasificaciones incorrectas anteriores)
            resolved_snapshot_id = None
            resolution_mode = "zero_shot"
            if sheet_profiles:
                _, resolved_snapshot_id, resolution_mode, _, _ = resolve_auto_recipe(
                    db,
                    tenant_id,
                    sheet_profiles,
                    user_id,
                )

            # Contenido para el LLM
            if has_structured:
                sample_lines = [f"Columnas: {headers_display}"]
                for row in structured[:5] if isinstance(structured, list) else []:
                    if isinstance(row, dict):
                        sample_lines.append(
                            str({k: v for k, v in list(row.items())[:8] if not k.startswith("_")})
                        )
                llm_content = "\n".join(sample_lines)
            else:
                llm_content = text[:6000] if text else ""
            vision_image_bytes = extraction.get("vision_image_bytes")
            if not isinstance(vision_image_bytes, (bytes, bytearray)):
                vision_image_bytes = file_bytes if tipo_archivo in ("JPG", "PNG", "IMG") else None

            # LLM con prompt genérico limpio (sin recipe_config que pueda sesgar la clasificación)
            analysis = await analyze_document(
                llm_content,
                filename,
                extraction.get("format", tipo_archivo),
                has_structured_rows=has_structured,
                recipe_config={},
                image_bytes=bytes(vision_image_bytes) if vision_image_bytes else None,
            )

            tipo_doc = analysis.get("doc_type", "OTHER")
            confianza = float(analysis.get("confidence", 0.0))
            requiere_revision = confianza < CONFIDENCE_THRESHOLD

            crud.add_log(
                db,
                doc.id,
                "CLASSIFY",
                user_id,
                {
                    "tipo_documento": tipo_doc,
                    "confianza": confianza,
                    "razonamiento": analysis.get("reasoning", ""),
                    "model_used": analysis.get("model_used"),
                },
            )

            # Construir datos_extraidos
            if has_structured:
                # Excel/CSV: SIEMPRE filas parseadas — el LLM no decide si es tabla
                sheet_used_str = extraction.get("sheet_used")
                sheet_metadata_raw = extraction.get("sheet_metadata") or {}

                # Agrupar filas por hoja (cada fila tiene _sheet)
                filas_por_hoja_raw: dict[str, list] = {}
                for _row in structured or []:
                    if isinstance(_row, dict):
                        _sname = str(_row.get("_sheet") or sheet_used_str or "")
                        if _sname:
                            filas_por_hoja_raw.setdefault(_sname, []).append(_row)

                datos_extraidos = {
                    "filas": structured[:200],
                    "total_filas": len(structured),
                    "columnas": headers_display or headers_norm,
                    "columnas_norm": headers_norm,
                    "filas_por_hoja": filas_por_hoja_raw,
                    "metadata_por_hoja": sheet_metadata_raw,
                    "sheet_usada": sheet_used_str,
                }
            else:
                # PDF/imagen/XML/TXT: usar lo que extrajo el LLM
                datos_extraidos = analysis.get("fields") or {}

            crud.add_log(
                db,
                doc.id,
                "EXTRACT",
                user_id,
                {
                    "campos_extraidos": (
                        list(datos_extraidos.keys()) if isinstance(datos_extraidos, dict) else []
                    )
                },
            )

            datos_extraidos = (
                _json_safe(datos_extraidos)
                if isinstance(datos_extraidos, (dict, list))
                else datos_extraidos
            )
            sheet_profiles = (
                _json_safe(sheet_profiles)
                if isinstance(sheet_profiles, (dict, list))
                else sheet_profiles
            )

            crud.update_documento(
                db,
                doc,
                {
                    "texto_ocr": text[:50000],
                    "tipo_documento_detectado": tipo_doc,
                    "confianza_clasificacion": confianza,
                    "requiere_revision": requiere_revision,
                    "datos_extraidos": datos_extraidos,
                    "estado": "REVIEW",
                    "proveedor_detectado": (
                        get_data_value(
                            datos_extraidos,
                            "vendor",
                            "proveedor",
                            "vendor_name",
                            "supplier",
                            "emisor",
                        )
                        if isinstance(datos_extraidos, dict)
                        else None
                    ),
                    "ruc_detectado": (
                        get_data_value(
                            datos_extraidos,
                            "vendor_tax_id",
                            "ruc",
                            "tax_id",
                            "supplier_tax_id",
                            "ruc_proveedor",
                        )
                        if isinstance(datos_extraidos, dict)
                        else None
                    ),
                    "monto_total": (
                        detect_document_total(datos_extraidos)
                        if isinstance(datos_extraidos, dict)
                        else None
                    ),
                    "moneda": (
                        detect_document_currency(datos_extraidos)
                        if isinstance(datos_extraidos, dict)
                        else None
                    ),
                    "fecha_documento": (
                        detect_document_date(datos_extraidos)
                        if isinstance(datos_extraidos, dict)
                        else None
                    ),
                    "fingerprint_json": sheet_profiles,
                    "sheet_profiles_json": sheet_profiles,
                    "recipe_snapshot_id": resolved_snapshot_id,
                },
            )
            db.commit()

            results.append(
                UploadResponse(
                    id=doc.id,
                    estado=doc.estado,
                    tipo_documento_detectado=tipo_doc,
                    confianza_clasificacion=confianza,
                    requiere_revision=requiere_revision,
                    datos_extraidos=datos_extraidos,
                )
            )
        except Exception as exc:
            logger.error("Error processing %s: %s", filename, exc)
            crud.update_documento(db, doc, {"estado": "FAILED", "error_detalle": str(exc)})
            crud.add_log(db, doc.id, "EXTRACT", user_id, {"error": str(exc)})
            db.commit()
            results.append(UploadResponse(id=doc.id, estado="FAILED"))

    for file in files:
        file_bytes = await file.read()
        filename = file.filename or "sin_nombre"
        tipo_archivo = detect_file_type(filename)

        if tipo_archivo == "ZIP":
            entries = list(iter_zip_entries(file_bytes))
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
                    )
                )
                continue
            for inner_name, inner_bytes in entries:
                await _process_single(
                    inner_bytes, f"{filename}::{inner_name}", detect_file_type(inner_name)
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
    return crud.list_documentos(db, tenant_id, estado=estado, limit=limit, offset=offset)


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
    return doc


class SyncRecipeRequest(BaseModel):
    sheet_usada: str | None = None
    force: bool = False


class SyncRecipesRequest(BaseModel):
    force: bool = False


def _learn_from_confirmation(db: Session, doc, datos_confirmados: dict, user_id: str) -> None:
    """Update the associated recipe snapshot's field_descriptions based on user corrections.

    Compares datos_extraidos vs datos_confirmados to detect which fields the user
    corrected, then stores those hints so future extractions improve.
    """
    from . import recipe_crud

    if not doc.recipe_snapshot_id:
        return
    datos_extraidos = doc.datos_extraidos or {}
    if not isinstance(datos_extraidos, dict) or not isinstance(datos_confirmados, dict):
        return

    skip_keys = {
        "filas",
        "total_filas",
        "columnas",
        "columnas_norm",
        "hojas",
        "sheet_usada",
        "metadata",
        "filas_por_hoja",
        "filas_por_hoja_count",
    }
    corrections: dict[str, str] = {}
    for key, confirmed_val in datos_confirmados.items():
        if key in skip_keys or key.startswith("_"):
            continue
        original_val = datos_extraidos.get(key)
        if confirmed_val != original_val and confirmed_val is not None:
            corrections[key] = (
                f"User corrected '{key}': expected '{confirmed_val}' (was '{original_val}')"
            )

    if not corrections:
        return

    snap = recipe_crud.get_snapshot(db, doc.recipe_snapshot_id)
    if not snap or not snap.content_json:
        return

    content = dict(snap.content_json)
    fd = dict(content.get("field_descriptions") or {})
    fd.update(corrections)
    content["field_descriptions"] = fd
    snap.content_json = content

    crud.add_log(
        db,
        doc.id,
        "LEARN",
        user_id,
        {"corrections": corrections, "snapshot_id": str(snap.id)},
    )


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

    crud.update_documento(
        db, doc, {"datos_confirmados": body.datos_confirmados, "estado": "CONFIRMED"}
    )
    _sync_batch_projection(db, doc.id, "CONFIRMED")
    crud.add_log(db, doc.id, "CONFIRM", user_id, {"datos_confirmados": body.datos_confirmados})

    _learn_from_confirmation(db, doc, body.datos_confirmados, user_id)

    db.commit()
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
    db.commit()

    return SyncRecipesResponse(
        total_sheets=len(available_sheets),
        processed_count=processed_count,
        skipped_count=skipped_count,
        results=results,
    )


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

    if destination == "recipe":
        data = _get_doc_import_data(doc)
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
                paid_at=body.paid_at,
                notes=body.notes,
            ),
        )
        record_ids = [str(purchase_result["purchase_id"])]
        if expense_result.record_id:
            record_ids.append(expense_result.record_id)
        result = SaveDocumentResponse(
            target="purchases",
            destination="supplier_invoice",
            status=purchase_result["status"],
            record_id=str(purchase_result["purchase_id"]),
            record_ids=record_ids,
            message=(
                f"Compra registrada y gasto creado ({body.payment_status})."
                if expense_result.status == "created"
                else purchase_result.get("message", "Compra registrada.")
            ),
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
                paid_at=body.paid_at,
                notes=body.notes,
            ),
        )

    payment_snapshot = (
        _normalize_payment_details(_get_document_total(doc), body)
        if destination != "recipe"
        else {"status": None, "paid_amount": None, "pending_amount": None}
    )
    confirmed = dict(_get_doc_import_data(doc))
    confirmed["_save"] = {
        "destination": destination,
        "target": result.target,
        "status": result.status,
        "record_id": result.record_id,
        "record_ids": result.record_ids,
        "payment_status": payment_snapshot.get("status"),
        "paid_amount": payment_snapshot.get("paid_amount"),
        "pending_amount": payment_snapshot.get("pending_amount"),
        "payment_method": body.payment_method,
        "paid_at": body.paid_at,
        "notes": body.notes,
        "saved_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    crud.update_documento(
        db,
        doc,
        {
            "datos_confirmados": confirmed,
            "estado": "CONFIRMED",
        },
    )
    _sync_batch_projection(db, doc.id, "CONFIRMED")
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
            "payment_method": body.payment_method,
            "paid_at": body.paid_at,
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

    # Merge with existing extracted data
    current = doc.datos_extraidos or {}
    if isinstance(current, dict):
        previous = {k: current.get(k) for k in body.campos}
        current.update(body.campos)

    crud.update_documento(db, doc, {"datos_extraidos": current})
    crud.add_log(
        db,
        doc.id,
        "EDIT",
        user_id,
        {"campos_modificados": body.campos, "valores_anteriores": previous},
    )
    db.commit()
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
            "estado": "CONFIRMED",
            "tipo_documento_detectado": "PRODUCTS",
            "confianza_clasificacion": 1.0,
            "requiere_revision": False,
        },
    )
    _sync_batch_projection(db, doc.id, "CONFIRMED")
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
    return SaveDailyLogResponse(**result)


def _match_product(db: Session, tenant_id: UUID, description: str):
    """Fuzzy product lookup by description → (Product, conversion_factor) or (None, 1).

    import_aliases format on Product:
      [{"name": "HARINA TRADICION PREMIUM 50 KG", "factor": 50, "unit": "kg"}, ...]
    factor = how many inventory-units per 1 invoice-unit.
    """
    import re
    import unicodedata

    from app.models.core.products import Product

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", str(s or ""))
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"[^a-z0-9]+", " ", s.strip().lower())
        return re.sub(r"\s+", " ", s).strip()

    desc_norm = _norm(description)
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
            alias_name = _norm(str(alias.get("name") or ""))
            if not alias_name:
                continue
            if alias_name == desc_norm or alias_name in desc_norm or desc_norm in alias_name:
                factor = float(alias.get("factor") or 1)
                return p, factor

    # 2) Exact name match
    for p in products:
        if _norm(p.name) == desc_norm:
            return p, 1.0

    # 3) Substring match
    for p in products:
        pn = _norm(p.name)
        if desc_norm in pn or pn in desc_norm:
            return p, 1.0

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
