from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any

import openpyxl
from celery import states

try:
    from app.modules.imports.application.celery_app import celery_app
except Exception:  # pragma: no cover
    celery_app = None  # type: ignore

from datetime import date, time
from decimal import Decimal

from app.config.database import session_scope
from app.db.rls import set_tenant_guc
from app.models.core.modelsimport import ImportBatch, ImportItem
from app.modules.imports.application.transform_dsl import apply_mapping_pipeline
from app.services.excel_analyzer import detect_header_row, extract_headers


def _dedupe_hash(obj: dict[str, Any]) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _idempotency_key(tenant_id: str, file_key: str, idx: int) -> str:
    return f"{tenant_id}:{file_key}:{idx}"


def _file_path_from_key(file_key: str) -> str:
    # Local provider: file_key like "imports/{tenant}/{uuid}.xlsx" under uploads/
    if file_key.startswith("imports/"):
        return os.path.join("uploads", file_key.replace("/", os.sep))
    return file_key


def _to_serializable(val):
    """Convert Excel cell values to JSON-serializable primitives."""
    try:
        if isinstance(val, (datetime, date, time)):
            # Keep full precision for datetimes; date/time isoformat as well
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        # Numpy scalar types -> Python scalars
        try:
            import numpy as np  # type: ignore

            if isinstance(val, (np.integer,)):
                return int(val)
            if isinstance(val, (np.floating,)):
                return float(val)
            if isinstance(val, (np.bool_,)):
                return bool(val)
        except Exception:
            pass
        return val
    except Exception:
        # Fallback: stringify unknown types
        try:
            return str(val)
        except Exception:
            return None


@celery_app.task(name="imports.import_products_excel", bind=True)
def import_products_excel(
    self, *, tenant_id: str, batch_id: str, file_key: str, source_type: str = "products"
):
    """Stream-parse a large Excel and create ImportItems in batches.

    - Uses read_only openpyxl
    - Detects header row and headers via excel_analyzer helpers
    - Commits every N rows to keep memory/locks bounded
    """
    file_path = _file_path_from_key(file_key)

    # Progress tracking
    processed = 0
    created = 0
    failed = 0
    BATCH_SIZE = 1000

    with session_scope() as db:
        # Fix tenant GUC for RLS-aware backends
        try:
            set_tenant_guc(db, str(tenant_id), persist=False)
        except Exception:
            pass

        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            self.update_state(state=states.FAILURE, meta={"error": "batch_not_found"})
            return {"ok": False, "error": "batch_not_found"}

        # Mark parsing
        batch.status = "PARSING"
        db.add(batch)
        db.commit()

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb.active
        except Exception as e:
            batch.status = "ERROR"
            db.add(batch)
            db.commit()
            self.update_state(state=states.FAILURE, meta={"error": f"open_failed: {e}"})
            return {"ok": False, "error": str(e)}

        try:
            header_row = detect_header_row(ws)
            headers: list[str] = extract_headers(ws, header_row)
            # Optional mapping for this batch
            map_cfg = None
            tf_cfg = None
            df_cfg = None
            try:
                if getattr(batch, "mapping_id", None):
                    from app.models.imports import ImportColumnMapping  # type: ignore

                    cm = (
                        db.query(ImportColumnMapping)
                        .filter(ImportColumnMapping.id == batch.mapping_id)
                        .first()
                    )
                    if cm:
                        map_cfg = cm.mapping or cm.mappings or {}
                        tf_cfg = cm.transforms or {}
                        df_cfg = cm.defaults or {}
            except Exception:
                map_cfg = tf_cfg = df_cfg = None
            # Iterate rows after header
            row_iter = ws.iter_rows(min_row=header_row + 1, values_only=True)

            idx_base = db.query(ImportItem).filter(ImportItem.batch_id == batch_id).count() or 0
            idx = idx_base
            buffer: list[ImportItem] = []

            for values in row_iter:
                processed += 1
                # Build dict row (raw)
                row: dict[str, Any] = {}
                for i, header in enumerate(headers):
                    if i < len(values):
                        row[header] = _to_serializable(values[i])
                # Skip fully empty lines
                if not any(v is not None and str(v).strip() != "" for v in row.values()):
                    continue
                # Apply mapping/transforms/defaults if available
                mapped: dict[str, Any] | None = None
                if map_cfg or tf_cfg or df_cfg:
                    mapped = apply_mapping_pipeline(
                        headers,
                        list(values),
                        mapping=map_cfg or {},
                        transforms=tf_cfg or {},
                        defaults=df_cfg or {},
                    )
                # Normalization using mapped (preferred) or raw heuristics
                if mapped is None:
                    nombre = row.get("nombre") or row.get("producto") or row.get("name") or ""
                    precio = row.get("precio") or row.get("price") or 0
                    cantidad = row.get("cantidad") or row.get("qty") or row.get("stock") or 0
                    categoria = row.get("categoria") or row.get("category") or "SIN_CATEGORIA"
                    try:
                        precio_f = float(precio) if precio not in (None, "") else 0.0
                    except Exception:
                        precio_f = 0.0
                    try:
                        cantidad_f = float(cantidad) if cantidad not in (None, "") else 0.0
                    except Exception:
                        cantidad_f = 0.0
                    normalized = {
                        "nombre": str(nombre).strip(),
                        "name": str(nombre).strip(),
                        "producto": str(nombre).strip(),
                        "precio": precio_f,
                        "price": precio_f,
                        "cantidad": cantidad_f,
                        "quantity": cantidad_f,
                        "stock": cantidad_f,
                        "categoria": str(categoria).strip(),
                        "category": str(categoria).strip(),
                    }
                else:
                    # Build normalized from mapped with synonyms
                    nombre = (
                        mapped.get("name") or mapped.get("nombre") or mapped.get("producto") or ""
                    )
                    precio_f = _to_number(mapped.get("price") or mapped.get("precio")) or 0.0
                    cantidad_f = (
                        _to_number(
                            mapped.get("stock") or mapped.get("cantidad") or mapped.get("quantity")
                        )
                        or 0.0
                    )
                    categoria = mapped.get("category") or mapped.get("categoria") or "SIN_CATEGORIA"
                    normalized = {
                        "nombre": str(nombre).strip(),
                        "name": str(nombre).strip(),
                        "producto": str(nombre).strip(),
                        "precio": float(precio_f),
                        "price": float(precio_f),
                        "cantidad": float(cantidad_f),
                        "quantity": float(cantidad_f),
                        "stock": float(cantidad_f),
                        "categoria": str(categoria).strip(),
                        "category": str(categoria).strip(),
                    }
                    # Preserve mapped extras (sku, image_url, packs, etc.)
                    for k, v in (mapped or {}).items():
                        if k not in normalized:
                            normalized[k] = v
                idx += 1
                idem = _idempotency_key(str(tenant_id), file_key, idx)
                dedupe = _dedupe_hash({"normalized": normalized})
                item = ImportItem(
                    batch_id=batch_id,
                    idx=idx,
                    raw=row,
                    normalized=normalized,
                    idempotency_key=idem,
                    dedupe_hash=dedupe,
                    status="PENDING",
                )
                buffer.append(item)

                if len(buffer) >= BATCH_SIZE:
                    db.add_all(buffer)
                    db.commit()
                    created += len(buffer)
                    buffer.clear()
                    # Report progress
                    try:
                        self.update_state(
                            state=states.STARTED,
                            meta={"processed": processed, "created": created},
                        )
                    except Exception:
                        pass

            # Flush remainder
            if buffer:
                db.add_all(buffer)
                db.commit()
                created += len(buffer)

            # Done
            batch.status = "READY"
            db.add(batch)
            db.commit()
            return {"ok": True, "processed": processed, "created": created}
        except Exception as e:
            batch.status = "ERROR"
            db.add(batch)
            db.commit()
            self.update_state(state=states.FAILURE, meta={"error": str(e)})
            return {"ok": False, "error": str(e)}
        finally:
            try:
                wb.close()
            except Exception:
                pass
