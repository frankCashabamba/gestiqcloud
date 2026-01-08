from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any

import openpyxl
import unicodedata
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
from app.modules.imports.application.tasks.task_import_file import _to_number
from app.modules.imports.application.sku_utils import sanitize_sku
from app.modules.imports.application.transform_dsl import apply_mapping_pipeline
from app.services.excel_analyzer import detect_header_row, extract_headers


def _dedupe_hash(obj: dict[str, Any]) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
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
        if isinstance(val, datetime | date | time):
            # Keep full precision for datetimes; date/time isoformat as well
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        # Numpy scalar types -> Python scalars
        try:
            import numpy as np  # type: ignore

            if isinstance(val, np.integer):
                return int(val)
            if isinstance(val, np.floating):
                return float(val)
            if isinstance(val, np.bool_):
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


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return _to_serializable(obj)


def _norm_key(s: str) -> str:
    try:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.strip().lower()
        out = []
        prev_underscore = False
        for ch in s:
            if ch.isalnum():
                out.append(ch)
                prev_underscore = False
            else:
                if not prev_underscore:
                    out.append("_")
                    prev_underscore = True
        return "".join(out).strip("_")
    except Exception:
        return str(s).strip().lower()


def _first_from_maps(row: dict[str, Any], row_norm: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
        nk = _norm_key(k)
        if nk in row_norm and row_norm[nk] not in (None, ""):
            return row_norm[nk]
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
    BATCH_SIZE = 1000

    with session_scope() as db:
        # Fix tenant GUC for RLS-aware backends
        try:
            set_tenant_guc(db, str(tenant_id), persist=False)
        except Exception:
            pass

        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            raise RuntimeError("batch_not_found")

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
            raise RuntimeError(f"open_failed: {e}") from e

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
                row_norm = {_norm_key(k): v for k, v in row.items() if isinstance(k, str)}
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
                    nombre = _first_from_maps(row, row_norm, ["nombre", "producto", "articulo", "name"]) or ""
                    precio = _first_from_maps(
                        row,
                        row_norm,
                        [
                            "precio",
                            "price",
                            "venta",
                            "valor",
                            "importe",
                            "precio_unitario_venta",
                            "precio_unitario",
                        ],
                    )
                    costo = _first_from_maps(
                        row,
                        row_norm,
                        [
                            "costo",
                            "cost",
                            "coste",
                            "costo_promedio",
                            "costo_promedio",
                            "costo_unitario",
                            "precio_costo",
                            "cost_price",
                            "unit_cost",
                        ],
                    )
                    cantidad = _first_from_maps(
                        row, row_norm, ["cantidad", "qty", "stock", "existencia", "existencias", "unidades"]
                    )
                    bultos = _first_from_maps(row, row_norm, ["bultos", "packs", "paquetes"])
                    unidades_por_bulto = _first_from_maps(
                        row,
                        row_norm,
                        ["cantidad_por_bulto", "unidades_por_bulto", "cantidad_x_bulto", "cant_por_bulto"],
                    )
                    categoria = _first_from_maps(row, row_norm, ["categoria", "category"]) or "SIN_CATEGORIA"
                    precio_f = _to_number(precio) or 0.0
                    cantidad_f = _to_number(cantidad) or 0.0
                    costo_f = _to_number(costo)
                    if (cantidad_f == 0) and bultos and unidades_por_bulto:
                        cantidad_f = (_to_number(bultos) or 0.0) * (_to_number(unidades_por_bulto) or 0.0)
                    has_name = bool(str(nombre).strip())
                    has_price = precio not in (None, "")
                    has_stock = cantidad not in (None, "") or (
                        bultos not in (None, "") and unidades_por_bulto not in (None, "")
                    )
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
                    if costo_f is not None:
                        normalized["cost_price"] = costo_f
                        normalized["cost"] = costo_f
                        normalized["unit_cost"] = costo_f
                    sku = _first_from_maps(row, row_norm, ["codigo", "sku", "code", "cod"])
                    sku = sanitize_sku(sku)
                    if sku:
                        normalized["sku"] = sku
                else:
                    # Build normalized from mapped with synonyms
                    nombre = (
                        mapped.get("name") or mapped.get("nombre") or mapped.get("producto") or ""
                    )
                    if not str(nombre).strip():
                        nombre = (
                            _first_from_maps(row, row_norm, ["nombre", "producto", "articulo", "name"])
                            or ""
                        )
                    precio_src = mapped.get("price") or mapped.get("precio")
                    precio_f = _to_number(precio_src)
                    if precio_f is None:
                        precio_src = _first_from_maps(
                            row,
                            row_norm,
                            [
                                "precio",
                                "price",
                                "venta",
                                "valor",
                                "importe",
                                "precio_unitario_venta",
                                "precio_unitario",
                            ],
                        )
                        precio_f = _to_number(precio_src)
                    if precio_f is None:
                        precio_f = 0.0
                    costo_src = (
                        mapped.get("cost_price")
                        or mapped.get("cost")
                        or mapped.get("costo")
                        or mapped.get("unit_cost")
                    )
                    costo_f = _to_number(costo_src)
                    if costo_f is None:
                        costo_src = _first_from_maps(
                            row,
                            row_norm,
                            [
                                "costo",
                                "cost",
                                "coste",
                                "costo_promedio",
                                "costo_unitario",
                                "precio_costo",
                                "cost_price",
                                "unit_cost",
                            ],
                        )
                        costo_f = _to_number(costo_src)
                    cantidad_src = (
                        mapped.get("stock") or mapped.get("cantidad") or mapped.get("quantity")
                    )
                    cantidad_f = _to_number(cantidad_src)
                    if cantidad_f is None:
                        cantidad_src = _first_from_maps(
                            row,
                            row_norm,
                            ["cantidad", "qty", "stock", "existencia", "existencias", "unidades"],
                        )
                        cantidad_f = _to_number(cantidad_src)
                    if cantidad_f is None:
                        cantidad_f = 0.0
                    categoria = (
                        mapped.get("category")
                        or mapped.get("categoria")
                        or _first_from_maps(row, row_norm, ["categoria", "category"])
                        or "SIN_CATEGORIA"
                    )
                    has_name = bool(str(nombre).strip())
                    has_price = precio_src not in (None, "")
                    has_stock = cantidad_src not in (None, "")
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
                    if costo_f is not None:
                        normalized["cost_price"] = float(costo_f)
                        normalized["cost"] = float(costo_f)
                        normalized["unit_cost"] = float(costo_f)
                    # Preserve mapped extras (sku, image_url, packs, etc.)
                    for k, v in (mapped or {}).items():
                        if k in ("unit", "unidad"):
                            if isinstance(v, (int, float)) or (
                                isinstance(v, str) and v.strip().isdigit()
                            ):
                                continue
                        if k not in normalized:
                            normalized[k] = v
                    if not normalized.get("sku"):
                        normalized["sku"] = _first_from_maps(row, row_norm, ["codigo", "sku", "code", "cod"])
                    sku = sanitize_sku(normalized.get("sku"))
                    if sku:
                        normalized["sku"] = sku
                status = "OK" if (has_name and has_price and has_stock) else "PENDING"
                raw_safe = _json_safe(row)
                normalized_safe = _json_safe(normalized)
                idx += 1
                idem = _idempotency_key(str(tenant_id), file_key, idx)
                dedupe = _dedupe_hash({"normalized": normalized_safe})
                item = ImportItem(
                    batch_id=batch_id,
                    idx=idx,
                    raw=raw_safe,
                    normalized=normalized_safe,
                    idempotency_key=idem,
                    dedupe_hash=dedupe,
                    status=status,
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
            db.rollback()
            batch.status = "ERROR"
            db.add(batch)
            db.commit()
            raise RuntimeError(str(e)) from e
        finally:
            try:
                wb.close()
            except Exception:
                pass
