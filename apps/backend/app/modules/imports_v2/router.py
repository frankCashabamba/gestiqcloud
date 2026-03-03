from __future__ import annotations

import io
import logging
import os
import re
import tempfile
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pandas as pd  # type: ignore
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.modelsimport import ImportBatch, ImportItem
from app.models.imports import ImportColumnMapping
from app.modules.imports.application.status import ImportBatchStatus, ImportItemStatus
from app.modules.imports.application.transform_dsl import _to_number, apply_mapping_pipeline
from app.modules.imports.services.ocr_service import OCRService

logger = logging.getLogger("imports_v2")

router = APIRouter(
    prefix="/imports/v2",
    tags=["imports-v2"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


def _detect_doc_type(filename: str, mime: str, text_preview: str = "") -> str:
    name = (filename or "").lower()
    m = mime.lower() if mime else ""
    if name.endswith((".xlsx", ".xls", ".csv")):
        # Distinguir productos vs invoices por keywords en cabeceras más adelante
        return "auto_excel"
    if name.endswith(".xml"):
        return "xml"
    if any(name.endswith(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        t = text_preview.lower()
        if "ticket" in t or "gracias" in t or "tpv" in t or "pos" in t:
            return "sales"  # tratamos ticket POS como venta
        if "iban" in t or "transfer" in t or "saldo" in t or "statement" in t:
            return "bank"
        if "factura" in t or "invoice" in t or "subtotal" in t:
            return "invoices"
        return "expenses"
    return "generic"


def _create_batch(db: Session, tenant_id: UUID, source_type: str, filename: str, created_by: UUID | None) -> ImportBatch:
    batch = ImportBatch(
        id=uuid4(),
        tenant_id=tenant_id,
        origin=filename,
        source_type=source_type,
        status=ImportBatchStatus.PENDING,
        created_by=str(created_by or tenant_id),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def _resolve_mapping(
    db: Session,
    tenant_id: UUID,
    filename: str | None,
    headers: list[str] | None,
) -> ImportColumnMapping | None:
    """Devuelve el mejor mapping por regex de filename o similitud de cabeceras."""
    mappings = (
        db.query(ImportColumnMapping)
        .filter(ImportColumnMapping.tenant_id == tenant_id, ImportColumnMapping.is_active)
        .all()
    )
    if not mappings:
        return None
    # 1) filename regex
    if filename:
        for m in mappings:
            try:
                if m.file_pattern and re.search(str(m.file_pattern), filename, re.I):
                    return m
            except Exception:
                continue
    # 2) header similarity muy simple: intersección de claves
    if headers:
        header_set = {h.strip().lower() for h in headers if h}
        best = None
        best_score = 0
        for m in mappings:
            mp = m.mapping or {}
            keys = {str(k).strip().lower() for k in mp.keys() if k}
            vals = {
                str(v).strip().lower()
                for v in mp.values()
                if isinstance(v, str) and v.lower() != "ignore"
            }
            overlap = len(header_set & keys) + len(header_set & vals)
            if overlap > best_score:
                best_score = overlap
                best = m
        return best
    return None


def _apply_mapping(headers: list[str], row: dict[str, Any], mapping: dict, transforms: dict | None, defaults: dict | None) -> dict[str, Any]:
    """Aplica mapping v1/legacy (ImportColumnMapping.mapping) usando DSL existente."""
    values = [row.get(h, "") for h in headers]
    return apply_mapping_pipeline(
        headers=headers,
        values=values,
        mapping=mapping or {},
        transforms=transforms or {},
        defaults=defaults or {},
    )


def _auto_map_products(row: dict[str, Any]) -> dict[str, Any]:
    """Heurística rápida para productos cuando no hay mapping ni aliases configurados."""
    norm = {}

    def pick(keys: list[str]):
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        for k in row.keys():
            if any(k.lower().replace(" ", "_").startswith(t) for t in keys):
                return row[k]
        return None

    nombre = pick(["nombre", "name", "descripcion", "descripción", "producto", "detalle", "articulo", "artículo"])
    sku = pick(["sku", "codigo", "código", "code", "barcode", "ean", "upc"])
    price = pick(["precio", "price", "pvp", "venta", "precio_venta", "precio unitario", "precio_unitario"])
    cost = pick(["costo", "cost", "cost_price", "precio_costo"])
    stock = pick(["stock", "cantidad", "existencias", "unidades", "qty"])
    category = pick(["categoria", "categoría", "category", "rubro", "familia", "grupo", "linea", "línea"])
    unit = pick(["unidad", "uom", "un", "unidad_medida", "medida"])

    if nombre is not None:
        norm["name"] = str(nombre)
        norm["nombre"] = str(nombre)
    if sku is not None:
        norm["sku"] = str(sku)
        norm["codigo"] = str(sku)
    if price is not None:
        norm["price"] = _to_number(price)
        norm["precio"] = _to_number(price)
    if cost is not None:
        norm["cost_price"] = _to_number(cost)
    if stock is not None:
        norm["stock"] = _to_number(stock)
        norm["cantidad"] = _to_number(stock)
    if category is not None:
        norm["category"] = str(category)
        norm["categoria"] = str(category)
    if unit is not None:
        norm["unit"] = str(unit)
        norm["unidad"] = str(unit)

    # Conserva el resto de campos originales
    out = dict(row)
    out.update(norm)
    return out


def _ingest_rows(
    db: Session,
    batch: ImportBatch,
    rows: list[dict[str, Any]],
    doc_type: str,
    origin: str,
):
    items: list[ImportItem] = []

    def _extract_date(text: str) -> str | None:
        # Busca fechas en formatos comunes: 2026-02-28, 28/02/2026, 28-02-26
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if m:
            return m.group(1)
        m = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b", text)
        if m:
            val = m.group(1).replace("/", "-")
            parts = val.split("-")
            if len(parts[2]) == 2:
                # asumimos siglo actual
                parts[2] = "20" + parts[2]
            return "-".join([parts[2], parts[1], parts[0]])
        return None

    for idx, row in enumerate(rows):
        norm = dict(row)
        text_blob = " ".join(str(v) for v in row.values() if v is not None)
        # Normalizaciones rápidas para compatibilidad
        if doc_type in ("expenses", "invoices", "ticket_pos", "sales"):
            if "amount" not in norm:
                norm["amount"] = _to_number(norm.get("importe") or norm.get("total") or norm.get("monto"))
        if doc_type == "sales":
            # Fecha: intenta extraer, si no, hoy
            dt = _extract_date(text_blob) or datetime.utcnow().date().isoformat()
            norm.setdefault("expense_date", dt)
            # Categoría ventas por defecto
            norm.setdefault("category", "VENTAS")
            # Descripción corta
            desc = str(norm.get("description") or norm.get("concepto") or "").strip()
            if not desc and "texto" in norm:
                desc = str(norm.get("texto")).split("\n")[0][:120]
            norm["description"] = (desc or "Ticket de venta POS")[:180]
            # Cliente/proveedor vacío
            norm.setdefault("counterparty", "")
            norm["doc_type"] = "sales"
            norm["direction"] = "income"
        item = ImportItem(
            id=uuid4(),
            tenant_id=batch.tenant_id,
            batch_id=batch.id,
            idx=idx,
            raw={
                "source": {"origin": origin, "row": idx + 1},
                "tables": [{"headers_raw": list(row.keys()), "rows": [row]}],
            },
            normalized=norm,
            status=ImportItemStatus.OK,
            idempotency_key=f"{batch.tenant_id}:{batch.id}:{idx}",
            dedupe_hash="",
        )
        items.append(item)
    db.bulk_save_objects(items)
    batch.status = ImportBatchStatus.PENDING
    db.add(batch)
    db.commit()
    return len(items)


@router.post("/upload")
async def upload_and_ingest(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Ingesta un archivo (Excel/CSV/PDF/imagen) en un batch nuevo usando heurísticas simples.
    Sin plantillas ni rutas legacy.
    """
    claims = getattr(request.state, "access_claims", None)
    tenant_id = claims.get("tenant_id") if claims else None
    user_id = claims.get("user_id") if claims else None
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_missing")
    tenant_uuid = UUID(str(tenant_id))
    user_uuid = UUID(str(user_id)) if user_id else tenant_uuid

    filename = file.filename or "archivo"
    mime = file.content_type or ""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty_file")

    # PDF/imagen -> OCR primero si aplica
    text_preview = ""
    if filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        ocr = OCRService()
        if not ocr.is_available():
            raise HTTPException(status_code=501, detail="ocr_not_available")
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            result = await ocr.extract_text(tmp_path)
            text_preview = result.text[:2000] if result and result.text else ""
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    doc_type = _detect_doc_type(filename, mime, text_preview)
    resolved_type = doc_type
    if doc_type == "auto_excel":
        resolved_type = "products"
    batch = _create_batch(db, tenant_uuid, resolved_type, filename, user_uuid)

    # Excel/CSV
    if filename.lower().endswith((".xlsx", ".xls", ".csv")):
        try:
            if filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=415, detail=f"parse_error: {e}") from e

        if df.empty:
            return {"batch_id": str(batch.id), "items": 0, "doc_type": doc_type}

        headers = [str(h).strip() or f"col_{i+1}" for i, h in enumerate(df.columns)]
        rows = []
        for _, r in df.iterrows():
            row_dict = {headers[i]: ("" if pd.isna(v) else v) for i, v in enumerate(r.tolist())}
            if any(str(v).strip() for v in row_dict.values()):
                rows.append(row_dict)

        # Resolver mapping por filename/headers
        mapping_obj = _resolve_mapping(db, tenant_uuid, filename, headers)
        if mapping_obj and mapping_obj.mapping:
            mapped_rows = []
            for r in rows:
                try:
                    mapped_rows.append(
                        _apply_mapping(headers, r, mapping_obj.mapping, mapping_obj.transforms, mapping_obj.defaults)
                    )
                except Exception:
                    mapped_rows.append(r)
            rows = mapped_rows
            batch.mapping_id = mapping_obj.id

        # Heurística de doc_type por cabeceras o mapping
        lowered = " ".join(headers).lower()
        if mapping_obj and mapping_obj.description and "source_type=" in (mapping_obj.description or ""):
            try:
                doc_type = mapping_obj.description.split("source_type=", 1)[1].split()[0].strip()
            except Exception:
                doc_type = doc_type
        elif "sku" in lowered or "producto" in lowered or "price" in lowered:
            doc_type = "products"
        elif "invoice" in lowered or "factura" in lowered:
            doc_type = "invoices"
        elif "iban" in lowered or "transfer" in lowered:
            doc_type = "bank"
        else:
            doc_type = "expenses"
        batch.source_type = doc_type
        db.add(batch)
        # Si es products y no hubo mapping, aplicar auto-map heurístico fila a fila
        if doc_type == "products" and not mapping_obj:
            rows = [_auto_map_products(r) for r in rows]
        count = _ingest_rows(db, batch, rows, doc_type, origin="excel")
        return {"batch_id": str(batch.id), "items": count, "doc_type": doc_type, "mapping": str(mapping_obj.id) if mapping_obj else None}

    # PDF / imagen
    if filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        ocr = OCRService()
        if not ocr.is_available():
            raise HTTPException(status_code=501, detail="ocr_not_available")
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            result = await ocr.extract_text(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        if not result or not result.text:
            raise HTTPException(status_code=422, detail="ocr_empty")

        text = result.text
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        # Extraer montos simples
        amounts = re.findall(r"\b\d+[.,]\d{2}\b", text)
        first_amount = amounts[0] if amounts else None
        row = {
            "texto": "\n".join(lines[:50]),
            "amount": _to_number(first_amount),
            "description": lines[0] if lines else filename,
            "source": "ocr",
        }
        # Resolver mapping (poco probable en OCR, pero soportado)
        mapping_obj = _resolve_mapping(db, tenant_uuid, filename, list(row.keys()))
        rows = [row]
        if mapping_obj and mapping_obj.mapping:
            try:
                rows = [
                    _apply_mapping(list(row.keys()), row, mapping_obj.mapping, mapping_obj.transforms, mapping_obj.defaults)
                ]
                batch.mapping_id = mapping_obj.id
            except Exception:
                rows = [row]

        count = _ingest_rows(db, batch, rows, doc_type, origin="ocr")
        return {
            "batch_id": str(batch.id),
            "items": count,
            "doc_type": doc_type,
            "mapping": str(mapping_obj.id) if mapping_obj else None,
        }

    # XML u otros -> no soportado aún
    raise HTTPException(status_code=415, detail="unsupported_file_type")
