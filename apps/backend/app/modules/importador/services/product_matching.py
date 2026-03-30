"""Funciones de matching de productos para el importador.

Movidas desde router.py para mantener el router limpio.
"""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from sqlalchemy.orm import Session

PACK_UNIT_PATTERN = re.compile(
    r"(?<![a-z0-9])(\d+(?:[.,]\d+)?)\s*(kg|kilos?|kilogramos?|g|gr|gramos?|"
    r"lb|lbs|libras?|oz|onzas?|ton|toneladas?|l|lt|ltr|litros?|ml|mililitros?)\b",
    re.IGNORECASE,
)


def _norm_import_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text.strip().lower())
    return re.sub(r"\s+", " ", text).strip()


def _strip_pack_tokens(value: str) -> str:
    stripped = PACK_UNIT_PATTERN.sub(" ", str(value or ""))
    return _norm_import_text(stripped)


def _infer_pack_conversion_factor(description: str, product_unit: str | None) -> float:
    from app.services.unit_catalog_service import normalize_operational_unit
    from app.utils.unit_converter import are_compatible_units, convert

    normalized_product_unit = normalize_operational_unit(product_unit, default="uds")
    if normalized_product_unit == "uds":
        return 1.0

    matches = PACK_UNIT_PATTERN.findall(str(description or ""))
    for raw_qty, raw_unit in reversed(matches):
        try:
            pack_qty = float(str(raw_qty).replace(",", "."))
        except ValueError:
            continue
        if pack_qty <= 0:
            continue
        normalized_pack_unit = normalize_operational_unit(raw_unit, default=raw_unit)
        if normalized_pack_unit == normalized_product_unit:
            return pack_qty
        try:
            if are_compatible_units(normalized_pack_unit, normalized_product_unit):
                return float(convert(pack_qty, normalized_pack_unit, normalized_product_unit))
        except ValueError:
            continue
    return 1.0


def _get_line_values(item: dict) -> tuple[str, float, float]:
    description = str(item.get("description") or "").strip()
    qty = float(item.get("quantity") or 0)
    unit_price = float(item.get("unit_price") or 0)
    return description, qty, unit_price


def _find_product_by_id(db: Session, tenant_id: UUID, product_id: UUID | str | None):
    from app.models.core.products import Product

    if not product_id:
        return None
    try:
        product_id = UUID(str(product_id))
    except (TypeError, ValueError):
        return None
    return (
        db.query(Product)
        .filter(
            Product.tenant_id == tenant_id,
            Product.id == product_id,
            Product.active == True,  # noqa: E712
        )
        .first()
    )


def _append_import_alias(product, description: str, factor: float, unit: str | None = None) -> None:
    description = str(description or "").strip()
    if not description:
        return
    aliases = product.import_aliases if isinstance(product.import_aliases, list) else []
    normalized_description = _norm_import_text(description)
    for alias in aliases:
        if not isinstance(alias, dict):
            continue
        if _norm_import_text(str(alias.get("name") or "")) == normalized_description:
            return
    aliases.append(
        {
            "name": description,
            "factor": float(factor or 1),
            "unit": str(unit or product.unit or "").strip() or None,
        }
    )
    product.import_aliases = aliases


def _score_product_candidate(description: str, product) -> tuple[float, str | None, float]:
    from difflib import SequenceMatcher

    desc_norm = _norm_import_text(description)
    desc_core = _strip_pack_tokens(description)
    if not desc_norm:
        return 0.0, None, 1.0

    best_score = 0.0
    best_reason: str | None = None
    best_factor = 1.0
    inferred_factor = _infer_pack_conversion_factor(description, getattr(product, "unit", None))

    aliases = product.import_aliases if isinstance(product.import_aliases, list) else []
    for alias in aliases:
        if not isinstance(alias, dict):
            continue
        alias_name = _norm_import_text(str(alias.get("name") or ""))
        if not alias_name:
            continue
        if alias_name == desc_norm:
            return 0.99, "alias_exact", float(alias.get("factor") or 1)
        if alias_name in desc_norm or desc_norm in alias_name:
            score = 0.94
        else:
            score = SequenceMatcher(None, desc_norm, alias_name).ratio() * 0.88
        if score > best_score:
            best_score = score
            best_reason = "alias"
            best_factor = float(alias.get("factor") or 1)

    product_name = _norm_import_text(getattr(product, "name", ""))
    product_core = _strip_pack_tokens(getattr(product, "name", ""))
    if product_name == desc_norm and 0.93 > best_score:
        best_score = 0.93
        best_reason = "name_exact"
        best_factor = inferred_factor
    if desc_core and product_core and desc_core == product_core and 0.91 > best_score:
        best_score = 0.91
        best_reason = "core_exact"
        best_factor = inferred_factor
    if (
        product_name
        and (desc_norm in product_name or product_name in desc_norm)
        and 0.84 > best_score
    ):
        best_score = 0.84
        best_reason = "name_partial"
        best_factor = inferred_factor
    if (
        desc_core
        and product_core
        and (desc_core in product_core or product_core in desc_core)
        and 0.81 > best_score
    ):
        best_score = 0.81
        best_reason = "core_partial"
        best_factor = inferred_factor

    similarity = SequenceMatcher(None, desc_norm, product_name).ratio() if product_name else 0.0
    if desc_core and product_core:
        similarity = max(similarity, SequenceMatcher(None, desc_core, product_core).ratio())
    if similarity >= 0.52:
        fuzzy_score = min(similarity * 0.78, 0.79)
        if fuzzy_score > best_score:
            best_score = fuzzy_score
            best_reason = "fuzzy"
            best_factor = inferred_factor

    return best_score, best_reason, best_factor


def _build_document_line_matches(
    db: Session,
    tenant_id: UUID,
    doc,
    *,
    line_matches=None,
    limit_per_line: int = 5,
):
    from app.models.core.products import Product

    from ..schemas import DocumentLineMatchOut, ProductMatchCandidateOut

    data = doc.datos_confirmados or doc.datos_extraidos or {}
    if not isinstance(data, dict):
        data = {}
    line_items_raw = data.get("line_items") or []
    if not isinstance(line_items_raw, list):
        line_items_raw = []
    line_items = [item for item in line_items_raw if isinstance(item, dict)]

    selected_by_index = {
        int(match.line_index): match
        for match in (line_matches or [])
        if getattr(match, "line_index", None) is not None
    }
    products = (
        db.query(Product)
        .filter(Product.tenant_id == str(tenant_id), Product.active == True)  # noqa: E712
        .all()
    )

    output: list[DocumentLineMatchOut] = []
    for index, item in enumerate(line_items):
        description, qty, unit_price = _get_line_values(item)
        if not description or qty <= 0:
            continue

        ranked: list[tuple[float, str, float, object]] = []
        for product in products:
            score, reason, factor = _score_product_candidate(description, product)
            if score <= 0:
                continue
            ranked.append((score, reason or "candidate", factor, product))
        ranked.sort(key=lambda row: (-row[0], getattr(row[3], "name", "")))

        selected_match = selected_by_index.get(index)
        selected_product = (
            _find_product_by_id(db, tenant_id, selected_match.product_id)
            if selected_match
            else None
        )
        selected_reason = "manual" if selected_product else None
        selected_factor = (
            _infer_pack_conversion_factor(description, getattr(selected_product, "unit", None))
            if selected_product
            else 1.0
        )

        if not selected_product and ranked:
            top_score, top_reason, top_factor, top_product = ranked[0]
            if top_score >= 0.84:
                selected_product = top_product
                selected_reason = top_reason
                selected_factor = top_factor

        candidates = [
            ProductMatchCandidateOut(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                unit=product.unit or "unit",
                stock=float(product.stock or 0),
                score=round(score, 4),
                reason=reason,
                inferred_factor=float(factor or 1),
            )
            for score, reason, factor, product in ranked[:limit_per_line]
        ]
        output.append(
            DocumentLineMatchOut(
                line_index=index,
                description=description,
                quantity=qty,
                unit_price=unit_price,
                selected_product_id=selected_product.id if selected_product else None,
                selected_reason=selected_reason,
                inferred_factor=float(selected_factor or 1),
                candidates=candidates,
            )
        )

    return output
