from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any

from celery import states

try:
    from app.modules.imports.application.celery_app import celery_app
except Exception:  # pragma: no cover
    celery_app = None  # type: ignore

from datetime import date, time
from decimal import Decimal

from app.config.database import session_scope
from app.db.rls import set_tenant_guc
from app.models.core.products import Product
from app.models.recipes import Recipe, RecipeIngredient
from app.models.core.modelsimport import ImportBatch, ImportItem
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.parsers import registry as parsers_registry


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
    """Convert values to JSON-serializable primitives."""
    try:
        if isinstance(val, datetime | date | time):
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


def _to_number(val) -> float | None:
    """Convert value to number."""
    if val is None or val == "":
        return None


def _normalize_doc_type(doc_type: str | None) -> str:
    """Mapear alias a doc_type canónico usado por el módulo."""
    if not doc_type:
        return "generic"
    doc = str(doc_type).lower()
    if doc in ("bank", "bank_tx", "bank_transactions"):
        return "bank_transactions"
    if doc in ("invoice", "invoices", "factura", "facturas"):
        return "invoices"
    if doc in ("expense", "expenses", "receipt", "receipts"):
        return "expenses"
    if doc in ("product", "products", "productos"):
        return "products"
    return doc
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _extract_items_from_parsed_result(
    parsed_result: dict[str, Any], doc_type: str
) -> list[dict[str, Any]]:
    """Extract items list from parser result based on doc_type."""
    # If parser embeds items in a top-level key, unwrap first
    if doc_type == "products":
        return parsed_result.get("products", parsed_result.get("rows", [parsed_result]))
    elif doc_type == "invoices":
        return parsed_result.get("invoices", [parsed_result])
    elif doc_type == "bank_transactions":
        return parsed_result.get(
            "bank_transactions", parsed_result.get("transactions", [parsed_result])
        )
    elif doc_type == "recipes":
        return parsed_result.get("recipes", [parsed_result])
    elif "rows" in parsed_result:
        return parsed_result["rows"]
    else:
        return [parsed_result]


def _build_canonical_from_item(
    raw: dict[str, Any],
    normalized: dict[str, Any],
    doc_type: str,
    parser_id: str,
) -> dict[str, Any]:
    """
    Construir CanonicalDocument a partir de un item parseado.

    Mapea según doc_type (products, invoices, bank_transactions) al esquema SPEC-1.
    """
    if doc_type == "invoices":
        # El parser ya devuelve estructura canónica para invoices
        return (
            raw
            if raw.get("doc_type") == "invoice"
            else {
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
        )

    elif doc_type == "bank_transactions":
        # El parser ya devuelve estructura canónica para bank_tx
        return (
            raw
            if raw.get("doc_type") == "bank_tx"
            else {
                "doc_type": "bank_tx",
                "issue_date": raw.get("issue_date") or raw.get("transaction_date"),
                "currency": raw.get("currency", "USD"),
                "bank_tx": raw.get(
                    "bank_tx",
                    {
                        "amount": raw.get("amount"),
                        "direction": raw.get("direction", "credit"),
                        "value_date": raw.get("value_date") or raw.get("issue_date"),
                        "narrative": raw.get("narrative") or raw.get("concepto"),
                        "counterparty": raw.get("counterparty"),
                        "external_ref": raw.get("external_ref"),
                    },
                ),
                "payment": {"iban": raw.get("iban")} if raw.get("iban") else {},
                "source": raw.get("source", "parser"),
                "confidence": raw.get("confidence", 0.7),
            }
        )

    elif doc_type == "recipes":
        return {
            "doc_type": "product",
            "product": {
                "name": raw.get("name") or normalized.get("name"),
                "category": raw.get("classification"),
                "description": raw.get("recipe_type"),
            },
            "metadata": {
                "parser": parser_id,
                "detected_type": "recipes",
                "raw_data": raw,
            },
            "source": "parser",
            "confidence": raw.get("confidence", 0.6),
        }

    else:  # products, generic, or other
        detected = raw.get("doc_type") or raw.get("detected_type") or doc_type
        return {
            "doc_type": detected if detected in ("products", "other") else "other",
            "metadata": {
                "parser": parser_id,
                "doc_type_detected": detected,
                "raw_data": raw,
            },
            "source": "parser",
            "confidence": raw.get("confidence", 0.5),
        }


def _find_product_by_name(db, tenant_id: str, name: str) -> Product | None:
    try:
        return (
            db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                Product.name.ilike(name),
            )
            .first()
        )
    except Exception:
        return None


def _get_or_create_product(
    db,
    tenant_id: str,
    name: str | None,
    *,
    description: str | None = None,
    category: str | None = None,
) -> tuple[Product | None, bool]:
    """Find or create a product by name within a tenant."""
    if not name or str(name).strip() == "":
        return None, False
    normalized = str(name).strip()
    existing = _find_product_by_name(db, tenant_id, normalized)
    if existing:
        return existing, False
    product = Product(
        tenant_id=tenant_id,
        name=normalized,
        description=description,
        category=category,
        active=True,
        unit="unit",
    )
    db.add(product)
    db.flush()
    return product, True


def _persist_recipes(db, tenant_id: str, parsed_result: dict[str, Any]) -> dict[str, int]:
    recipes_data = parsed_result.get("recipes", [])
    ingredients_rows = parsed_result.get("rows", [])
    materials_rows = parsed_result.get("materials", [])
    created = 0
    errors = 0
    created_ingredients = 0
    created_materials = 0
    auto_products = 0

    for recipe_data in recipes_data:
        name = recipe_data.get("name")
        if not name:
            errors += 1
            continue

        product, auto_created = _get_or_create_product(
            db, tenant_id, name, description=recipe_data.get("recipe_type")
        )
        if auto_created:
            auto_products += 1

        if not product:
            errors += 1
            continue

        recipe = Recipe(
            tenant_id=tenant_id,
            product_id=product.id,
            name=name,
            yield_qty=recipe_data.get("portions") or 1,
            prep_time_minutes=None,
            instructions=None,
            is_active=True,
            total_cost=recipe_data.get("total_ingredients_cost") or 0,
        )
        db.add(recipe)
        db.flush()

        recipe_ingredients = [
            row for row in ingredients_rows if row.get("recipe_name") == name
        ]
        for idx, ing in enumerate(recipe_ingredients):
            prod, auto_created_ing = _get_or_create_product(
                db, tenant_id, ing.get("ingredient", ""), category=recipe_data.get("classification")
            )
            if auto_created_ing:
                auto_products += 1
            if not prod:
                errors += 1
                continue
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=prod.id,
                qty=ing.get("quantity") or 0,
                unit=ing.get("unit") or "unit",
                purchase_packaging=None,
                qty_per_package=ing.get("quantity") or 1,
                package_unit=ing.get("unit") or "unit",
                package_cost=ing.get("amount") or 0,
                notes=None,
                line_order=idx,
            )
            db.add(ingredient)
            created_ingredients += 1

        # Persist materials as additional ingredients (tagged in notes)
        mats_for_recipe = [row for row in materials_rows if row.get("recipe_name") == name]
        offset = len(recipe_ingredients)
        for m_idx, mat in enumerate(mats_for_recipe):
            prod, auto_created_mat = _get_or_create_product(
                db, tenant_id, mat.get("description", ""), category=recipe_data.get("classification")
            )
            if auto_created_mat:
                auto_products += 1
            if not prod:
                errors += 1
                continue
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=prod.id,
                qty=mat.get("quantity") or 0,
                unit=mat.get("purchase_unit") or "unit",
                purchase_packaging="material",
                qty_per_package=mat.get("quantity") or 1,
                package_unit=mat.get("purchase_unit") or "unit",
                package_cost=mat.get("amount") or mat.get("purchase_price") or 0,
                notes="material",
                line_order=offset + m_idx,
            )
            db.add(ingredient)
            created_materials += 1
        created += 1

    db.commit()
    return {
        "created": created,
        "errors": errors,
        "ingredients": created_ingredients,
        "materials": created_materials,
        "auto_products": auto_products,
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
            # Si el parser devolvió un tipo detectado, úsalo cuando el parser sea genérico
            detected_doc_type = (
                parsed_result.get("detected_type")
                or parsed_result.get("doc_type")
                or parser_info.get("doc_type")
            )
            doc_type = _normalize_doc_type(detected_doc_type)
            batch.source_type = batch.source_type or doc_type

            # Special handling for recipes: persist to Recipe/RecipeIngredient
            if doc_type == "recipes":
                persisted = _persist_recipes(db, tenant_id, parsed_result)
                batch.status = "READY" if persisted["errors"] == 0 else "PARTIAL"
                db.add(batch)
                db.commit()
                return {"ok": True, **persisted, "doc_type": doc_type, "parser_id": parser_id}

            # Create ImportItems from parsed data
            idx_base = db.query(ImportItem).filter(ImportItem.batch_id == batch_id).count() or 0
            idx = idx_base
            buffer: list[ImportItem] = []

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
                            meta={
                                "processed": processed,
                                "created": created,
                                "validated": items_validated,
                                "failed": items_failed,
                            },
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
