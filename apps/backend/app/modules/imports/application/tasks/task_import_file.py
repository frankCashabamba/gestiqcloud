from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List

from celery import states

try:
    from app.modules.imports.application.celery_app import celery_app
except Exception:  # pragma: no cover
    celery_app = None  # type: ignore

from app.config.database import session_scope
from app.db.rls import set_tenant_guc
from app.models.core.modelsimport import ImportBatch, ImportItem
from app.modules.imports.parsers import registry as parsers_registry
from app.modules.imports.domain.canonical_schema import validate_canonical
from decimal import Decimal
from datetime import datetime, date, time


def _dedupe_hash(obj: Dict[str, Any]) -> str:
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
    """Convert values to JSON-serializable primitives."""
    try:
        if isinstance(val, (datetime, date, time)):
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


def _to_number(val) -> float | None:
    """Convert value to number."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _extract_items_from_parsed_result(parsed_result: Dict[str, Any], doc_type: str) -> List[Dict[str, Any]]:
    """Extract items list from parser result based on doc_type."""
    if doc_type == "products":
        return parsed_result.get("products", parsed_result.get("rows", [parsed_result]))
    elif doc_type == "invoices":
        return parsed_result.get("invoices", [parsed_result])
    elif doc_type == "bank_transactions":
        return parsed_result.get("bank_transactions", parsed_result.get("transactions", [parsed_result]))
    elif "rows" in parsed_result:
        return parsed_result["rows"]
    else:
        return [parsed_result]


def _build_canonical_from_item(
    raw: Dict[str, Any],
    normalized: Dict[str, Any],
    doc_type: str,
    parser_id: str,
) -> Dict[str, Any]:
    """
    Construir CanonicalDocument a partir de un item parseado.
    
    Mapea según doc_type (products, invoices, bank_transactions) al esquema SPEC-1.
    """
    if doc_type == "invoices":
        # El parser ya devuelve estructura canónica para invoices
        return raw if raw.get("doc_type") == "invoice" else {
            "doc_type": "invoice",
            "invoice_number": raw.get("invoice_number"),
            "issue_date": raw.get("issue_date"),
            "due_date": raw.get("due_date"),
            "vendor": raw.get("vendor"),
            "buyer": raw.get("buyer"),
            "totals": raw.get("totals"),
            "lines": raw.get("lines"),
            "currency": raw.get("currency", "USD"),
            "payment": raw.get("payment"),
            "source": raw.get("source", "parser"),
            "confidence": raw.get("confidence", 0.7),
        }
    
    elif doc_type == "bank_transactions":
        # El parser ya devuelve estructura canónica para bank_tx
        return raw if raw.get("doc_type") == "bank_tx" else {
            "doc_type": "bank_tx",
            "issue_date": raw.get("issue_date") or raw.get("transaction_date"),
            "currency": raw.get("currency", "USD"),
            "bank_tx": raw.get("bank_tx", {
                "amount": raw.get("amount"),
                "direction": raw.get("direction", "credit"),
                "value_date": raw.get("value_date") or raw.get("issue_date"),
                "narrative": raw.get("narrative") or raw.get("concepto"),
                "counterparty": raw.get("counterparty"),
                "external_ref": raw.get("external_ref"),
            }),
            "payment": {"iban": raw.get("iban")} if raw.get("iban") else {},
            "source": raw.get("source", "parser"),
            "confidence": raw.get("confidence", 0.7),
        }
    
    else:  # products, generic, or other
        return {
            "doc_type": "other",
            "metadata": {
                "parser": parser_id,
                "doc_type_detected": doc_type,
                "raw_data": raw,
            },
            "source": "parser",
            "confidence": raw.get("confidence", 0.5),
        }


@celery_app.task(name="imports.import_file", bind=True)
def import_file(self, *, tenant_id: str, batch_id: str, file_key: str, parser_id: str):
    """Generic file import task using registered parsers.

    - Uses parser registry to dispatch to appropriate parser
    - Creates CanonicalDocument from parser output
    - Validates via validate_canonical
    - Persists parser_id y canonical_doc en ImportItems
    - Creates ImportItems in batches
    """
    file_path = _file_path_from_key(file_key)

    # Get parser from registry
    parser_info = parsers_registry.get_parser(parser_id)
    if not parser_info:
        self.update_state(state=states.FAILURE, meta={"error": f"parser_not_found: {parser_id}"})
        return {"ok": False, "error": f"parser_not_found: {parser_id}"}

    parser_func = parser_info["handler"]
    doc_type = parser_info["doc_type"]

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

        # Persistir parser_id elegido en batch
        batch.parser_id = parser_id
        batch.status = "PARSING"
        db.add(batch)
        db.commit()

        try:
            # Call parser
            parsed_result = parser_func(file_path)

            # Create ImportItems from parsed data
            idx_base = (
                db.query(ImportItem).filter(ImportItem.batch_id == batch_id).count() or 0
            )
            idx = idx_base
            buffer: List[ImportItem] = []

            # Extract items from parsed result based on parser type
            items_data = _extract_items_from_parsed_result(parsed_result, doc_type)
            
            items_validated = 0
            items_failed = 0

            for item_data in items_data:
                processed += 1
                idx += 1

                # Normalize data for ImportItem
                raw = item_data
                normalized = _to_serializable(raw)

                # Add metadata
                normalized["_metadata"] = {
                    "parser": parser_id,
                    "doc_type": doc_type,
                    "_imported_at": raw.get("_imported_at", datetime.utcnow().isoformat()),
                }

                # Construir documento canónico basado en doc_type
                canonical_doc = _build_canonical_from_item(
                    raw=raw,
                    normalized=normalized,
                    doc_type=doc_type,
                    parser_id=parser_id,
                )

                # Validar documento canónico
                is_valid, errors = validate_canonical(canonical_doc)
                
                idem = _idempotency_key(str(tenant_id), file_key, idx)
                dedupe = _dedupe_hash({"normalized": normalized, "doc_type": doc_type})

                import_item = ImportItem(
                    batch_id=batch_id,
                    idx=idx,
                    raw=raw,
                    normalized=normalized,
                    canonical_doc=canonical_doc if is_valid else None,
                    idempotency_key=idem,
                    dedupe_hash=dedupe,
                    status="OK" if is_valid else "ERROR_VALIDATION",
                    errors=errors if not is_valid else [],
                )
                buffer.append(import_item)
                
                if is_valid:
                    items_validated += 1
                else:
                    items_failed += 1

                if len(buffer) >= BATCH_SIZE:
                    db.add_all(buffer)
                    db.commit()
                    created += len(buffer)
                    buffer.clear()
                    # Report progress
                    try:
                        self.update_state(
                            state=states.STARTED,
                            meta={"processed": processed, "created": created, "validated": items_validated, "failed": items_failed},
                        )
                    except Exception:
                        pass

            # Flush remainder
            if buffer:
                db.add_all(buffer)
                db.commit()
                created += len(buffer)

            # Done
            batch.status = "READY" if items_failed == 0 else "PARTIAL"
            db.add(batch)
            db.commit()
            return {
                "ok": True,
                "processed": processed,
                "created": created,
                "validated": items_validated,
                "failed": items_failed,
                "doc_type": doc_type,
                "parser_id": parser_id,
            }

        except Exception as e:
            batch.status = "ERROR"
            db.add(batch)
            db.commit()
            self.update_state(state=states.FAILURE, meta={"error": str(e)})
            return {"ok": False, "error": str(e)}
