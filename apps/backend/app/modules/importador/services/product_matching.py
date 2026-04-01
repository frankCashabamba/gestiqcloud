"""Funciones de matching de productos para el importador.

Movidas desde router.py para mantener el router limpio.
"""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.products.interface.http.tenant import _generate_next_sku

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


def _has_meaningful_match_text(value: str) -> bool:
    tokens = [token for token in _norm_import_text(value).split(" ") if token]
    if not tokens:
        return False
    if any(any(ch.isalpha() for ch in token) and len(token) >= 3 for token in tokens):
        return True
    return len(tokens) >= 2 and sum(len(token) for token in tokens) >= 6


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


def _normalize_supplier_ref(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text[:120]


def _extract_line_supplier_ref(item: dict | None) -> str | None:
    if not isinstance(item, dict):
        return None
    return _normalize_supplier_ref(item.get("supplier_ref"))


def _iter_product_supplier_refs(product) -> list[str]:
    refs: list[str] = []
    metadata = product.product_metadata if isinstance(product.product_metadata, dict) else {}
    for key in ("source_supplier_ref", "supplier_ref"):
        normalized = _normalize_supplier_ref(metadata.get(key))
        if normalized:
            refs.append(normalized)
    raw_refs = metadata.get("supplier_refs")
    if isinstance(raw_refs, list):
        for value in raw_refs:
            normalized = _normalize_supplier_ref(value)
            if normalized:
                refs.append(normalized)
    elif raw_refs is not None:
        normalized = _normalize_supplier_ref(raw_refs)
        if normalized:
            refs.append(normalized)
    aliases = product.import_aliases if isinstance(product.import_aliases, list) else []
    for alias in aliases:
        if not isinstance(alias, dict):
            continue
        normalized = _normalize_supplier_ref(alias.get("supplier_ref"))
        if normalized:
            refs.append(normalized)
    normalized_sku = _normalize_supplier_ref(getattr(product, "sku", None))
    if normalized_sku:
        refs.append(normalized_sku)
    unique: list[str] = []
    seen: set[str] = set()
    for value in refs:
        norm = _norm_import_text(value)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        unique.append(value)
    return unique


def _product_has_supplier_ref(product, supplier_ref: str | None) -> bool:
    normalized_ref = _normalize_supplier_ref(supplier_ref)
    if not normalized_ref:
        return False
    target = _norm_import_text(normalized_ref)
    return any(
        _norm_import_text(candidate) == target for candidate in _iter_product_supplier_refs(product)
    )


def _persist_product_supplier_ref(product, supplier_ref: str | None) -> None:
    normalized_ref = _normalize_supplier_ref(supplier_ref)
    if not normalized_ref:
        return
    metadata = (
        dict(product.product_metadata or {}) if isinstance(product.product_metadata, dict) else {}
    )
    existing = metadata.get("supplier_refs")
    supplier_refs: list[str]
    if isinstance(existing, list):
        supplier_refs = [str(value) for value in existing if _normalize_supplier_ref(value)]
    elif existing is None:
        supplier_refs = []
    else:
        supplier_refs = [str(existing)]
    if not any(
        _norm_import_text(value) == _norm_import_text(normalized_ref) for value in supplier_refs
    ):
        supplier_refs.append(normalized_ref)
    metadata["supplier_refs"] = supplier_refs
    metadata.setdefault("source_supplier_ref", normalized_ref)
    product.product_metadata = metadata


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


def _create_product_from_line(
    db: Session,
    tenant_id: UUID,
    description: str,
    unit_price: float,
    initial_stock: float,
    supplier_ref: str | None = None,
):
    """Create a new product from an invoice line and return it.

    Stock starts at zero because the purchase receipt flow will post the
    inventory movement and update the aggregate stock once.
    """
    from app.models.core.products import Product

    category_name = None
    category_id = None
    sku = _generate_next_sku(db, tenant_id, category_name)
    normalized_description = description.strip()[:255]
    initial_price = unit_price if unit_price > 0 else 0.0
    normalized_supplier_ref = _normalize_supplier_ref(supplier_ref)

    product = Product(
        tenant_id=tenant_id,
        sku=sku,
        name=normalized_description,
        description=normalized_description,
        price=initial_price,
        cost_price=unit_price if unit_price > 0 else None,
        stock=0,
        unit="uds",
        active=True,
        is_raw_material=False,
        category_id=category_id,
        product_metadata={
            "import_source": "supplier_invoice_line_create_new",
            "source_description": normalized_description,
            "source_initial_unit_cost": unit_price if unit_price > 0 else None,
            "source_initial_qty": initial_stock if initial_stock > 0 else None,
            "source_supplier_ref": normalized_supplier_ref,
            "supplier_refs": [normalized_supplier_ref] if normalized_supplier_ref else [],
        },
        import_aliases=[
            {
                "name": normalized_description,
                "factor": 1.0,
                "unit": "uds",
                "supplier_ref": normalized_supplier_ref,
            }
        ],
    )
    db.add(product)
    db.flush()
    return product


def _append_import_alias(
    product,
    description: str,
    factor: float,
    unit: str | None = None,
    supplier_ref: str | None = None,
) -> None:
    description = str(description or "").strip()
    normalized_supplier_ref = _normalize_supplier_ref(supplier_ref)
    if not description and not normalized_supplier_ref:
        return
    aliases = (
        [dict(alias) for alias in product.import_aliases]
        if isinstance(product.import_aliases, list)
        else []
    )
    normalized_description = _norm_import_text(description)
    for alias in aliases:
        if not isinstance(alias, dict):
            continue
        same_name = (
            normalized_description
            and _norm_import_text(str(alias.get("name") or "")) == normalized_description
        )
        same_ref = normalized_supplier_ref and _norm_import_text(
            str(alias.get("supplier_ref") or "")
        ) == _norm_import_text(normalized_supplier_ref)
        if same_name or same_ref:
            if normalized_supplier_ref and not alias.get("supplier_ref"):
                alias["supplier_ref"] = normalized_supplier_ref
            if factor and not alias.get("factor"):
                alias["factor"] = float(factor or 1)
            if unit and not alias.get("unit"):
                alias["unit"] = str(unit or product.unit or "").strip() or None
            product.import_aliases = aliases
            _persist_product_supplier_ref(product, normalized_supplier_ref)
            return
    aliases.append(
        {
            "name": description,
            "factor": float(factor or 1),
            "unit": str(unit or product.unit or "").strip() or None,
            "supplier_ref": normalized_supplier_ref,
        }
    )
    product.import_aliases = aliases
    _persist_product_supplier_ref(product, normalized_supplier_ref)


def _score_product_candidate(
    description: str,
    product,
    supplier_ref: str | None = None,
) -> tuple[float, str | None, float]:
    from difflib import SequenceMatcher

    desc_norm = _norm_import_text(description)
    desc_core = _strip_pack_tokens(description)
    normalized_supplier_ref = _normalize_supplier_ref(supplier_ref)
    if normalized_supplier_ref and _product_has_supplier_ref(product, normalized_supplier_ref):
        inferred_factor = _infer_pack_conversion_factor(description, getattr(product, "unit", None))
        return 1.0, "supplier_ref_exact", inferred_factor
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
    product_name_meaningful = _has_meaningful_match_text(product_name)
    product_core_meaningful = _has_meaningful_match_text(product_core)
    if product_name == desc_norm and 0.93 > best_score:
        best_score = 0.93
        best_reason = "name_exact"
        best_factor = inferred_factor
    if (
        desc_core
        and product_core
        and product_core_meaningful
        and desc_core == product_core
        and 0.91 > best_score
    ):
        best_score = 0.91
        best_reason = "core_exact"
        best_factor = inferred_factor
    if (
        product_name_meaningful
        and product_name
        and (desc_norm in product_name or product_name in desc_norm)
        and 0.84 > best_score
    ):
        best_score = 0.84
        best_reason = "name_partial"
        best_factor = inferred_factor
    if (
        product_core_meaningful
        and desc_core
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
        supplier_ref = _extract_line_supplier_ref(item)
        if not description or qty <= 0:
            continue

        ranked: list[tuple[float, str, float, object]] = []
        for product in products:
            score, reason, factor = _score_product_candidate(
                description,
                product,
                supplier_ref=supplier_ref,
            )
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
