"""
Service to import REGISTRO-like sheets as daily production history.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.production._daily_log import DailyProductionLog
from app.models.recipes import Recipe


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class ColumnStats:
    key: str
    non_empty: int
    numeric_ratio: float
    string_ratio: float
    integer_ratio: float
    decimal_ratio: float
    unique_ratio: float
    median_positive: float


@dataclass
class RegistroMapping:
    product_key: str | None
    qty_produced_key: str | None
    unit_price_key: str | None
    qty_sold_key: str | None
    score: float = 0.0


def _parse_date_from_filename(filename: str) -> date | None:
    match = re.search(r"(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{2,4})", filename)
    if not match:
        return None

    try:
        day, month, year_raw = int(match.group(1)), int(match.group(2)), int(match.group(3))
        year = 2000 + year_raw if year_raw < 100 else year_raw
        return date(year, month, day)
    except ValueError:
        return None


def _safe_decimal(value: Any) -> Decimal:
    try:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.0001"))

        text = str(value).strip()
        if not text:
            return Decimal("0")

        text = text.replace(" ", "")
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")

        return Decimal(text).quantize(Decimal("0.0001"))
    except Exception:
        return Decimal("0")


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = re.sub(r"[^0-9,.\-]", "", text.replace("\xa0", " "))
    if not text or text in {"-", ".", ","}:
        return None

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def _match_recipe(db: Session, tenant_id: UUID, product_name: str) -> Recipe | None:
    name_clean = _norm(product_name)
    results = db.execute(select(Recipe).where(Recipe.tenant_id == str(tenant_id))).scalars().all()

    for recipe in results:
        if _norm(recipe.name) == name_clean:
            return recipe

    for recipe in results:
        recipe_name = _norm(recipe.name)
        if name_clean and (name_clean in recipe_name or recipe_name in name_clean):
            return recipe

    return None


def _row_has_data(row: dict[str, Any]) -> bool:
    for value in row.values():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return True
    return False


def _normalize_row_dict(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for raw_key, value in row.items():
        key_text = str(raw_key or "").strip()
        if not key_text or key_text.startswith("_"):
            continue

        key_norm = _norm(key_text)
        if key_norm and key_norm not in normalized:
            normalized[key_norm] = value

    return normalized


def _rows_to_normalized_dicts(rows_raw: list[Any]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []

    dict_rows = [row for row in rows_raw if isinstance(row, dict)]
    if dict_rows:
        for row in dict_rows:
            normalized = _normalize_row_dict(row)
            if _row_has_data(normalized):
                normalized_rows.append(normalized)
        return normalized_rows

    headers: list[str] = []
    for row in rows_raw:
        if not isinstance(row, (list, tuple)):
            continue

        values = list(row)
        if not headers:
            if any(value is not None and str(value).strip() for value in values):
                headers = [(_norm(value) or f"col {index}") for index, value in enumerate(values)]
            continue

        normalized = {
            headers[index]: values[index] if index < len(values) else None
            for index in range(len(headers))
        }
        if _row_has_data(normalized):
            normalized_rows.append(normalized)

    return normalized_rows


def _select_candidate_rows(datos_extraidos: dict) -> tuple[list[Any], str | None]:
    rows_by_sheet = datos_extraidos.get("filas_por_hoja", {})
    if isinstance(rows_by_sheet, dict) and rows_by_sheet:
        for sheet_key, raw_rows in rows_by_sheet.items():
            if "registro" in str(sheet_key).lower() and isinstance(raw_rows, list):
                return raw_rows, str(sheet_key)

        active_sheet = datos_extraidos.get("sheet_usada")
        if active_sheet in rows_by_sheet and isinstance(rows_by_sheet.get(active_sheet), list):
            return rows_by_sheet.get(active_sheet) or [], str(active_sheet)

        for sheet_key, raw_rows in rows_by_sheet.items():
            if isinstance(raw_rows, list) and raw_rows:
                return raw_rows, str(sheet_key)

    raw_rows = datos_extraidos.get("filas", [])
    if isinstance(raw_rows, list):
        return raw_rows, None

    return [], None


def _collect_column_stats(rows: list[dict[str, Any]]) -> dict[str, ColumnStats]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                keys.append(key)

    stats: dict[str, ColumnStats] = {}
    for key in keys:
        values = [row.get(key) for row in rows if row.get(key) not in (None, "")]
        non_empty = len(values)
        numeric_values = [num for value in values if (num := _to_float(value)) is not None]
        string_values = [str(value).strip() for value in values if (num := _to_float(value)) is None and str(value).strip()]

        integer_ratio = (
            sum(1 for value in numeric_values if float(value).is_integer()) / len(numeric_values)
            if numeric_values
            else 0.0
        )
        decimal_ratio = (
            sum(1 for value in numeric_values if not float(value).is_integer()) / len(numeric_values)
            if numeric_values
            else 0.0
        )
        positive_values = [value for value in numeric_values if value > 0]
        median_positive = median(positive_values) if positive_values else 0.0
        unique_base = string_values if string_values else [f"{value:.4f}" for value in numeric_values]
        unique_ratio = len(set(unique_base)) / len(unique_base) if unique_base else 0.0

        stats[key] = ColumnStats(
            key=key,
            non_empty=non_empty,
            numeric_ratio=(len(numeric_values) / non_empty) if non_empty else 0.0,
            string_ratio=(len(string_values) / non_empty) if non_empty else 0.0,
            integer_ratio=integer_ratio,
            decimal_ratio=decimal_ratio,
            unique_ratio=unique_ratio,
            median_positive=float(median_positive),
        )

    return stats


def _string_column_score(stat: ColumnStats) -> float:
    if stat.string_ratio < 0.5 or stat.non_empty < 2:
        return -1.0
    coverage = min(stat.non_empty / 25.0, 1.0)
    return (stat.string_ratio * 3.0) + (stat.unique_ratio * 2.0) + coverage - (stat.numeric_ratio * 2.0)


def _price_column_score(stat: ColumnStats) -> float:
    if stat.numeric_ratio < 0.6 or stat.non_empty < 2:
        return -1.0
    coverage = min(stat.non_empty / 25.0, 1.0)
    median_bonus = 1.0 / (1.0 + max(stat.median_positive, 0.0))
    integer_penalty = 0.6 if stat.integer_ratio > 0.9 and stat.median_positive >= 10 else 0.0
    return coverage + (stat.decimal_ratio * 1.7) + median_bonus - integer_penalty


def _approx_equal(left: float, right: float, rel_tol: float = 0.03, abs_tol: float = 0.05) -> bool:
    if abs(left - right) <= abs_tol:
        return True
    if right == 0:
        return abs(left) <= abs_tol
    return abs(left - right) / max(abs(right), 1.0) <= rel_tol


def _pair_product_score(rows: list[dict[str, Any]], left_key: str, right_key: str, total_key: str) -> tuple[float, int]:
    checks = 0
    hits = 0
    for row in rows:
        left = _to_float(row.get(left_key))
        right = _to_float(row.get(right_key))
        total = _to_float(row.get(total_key))
        if left is None or right is None or total is None or left <= 0 or right <= 0:
            continue
        checks += 1
        if _approx_equal(left * right, total):
            hits += 1

    return ((hits / checks) if checks else 0.0), checks


def _comparison_ratio(
    rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
    relation: callable,
) -> float:
    checks = 0
    hits = 0
    for row in rows:
        left = _to_float(row.get(left_key))
        right = _to_float(row.get(right_key))
        if left is None or right is None:
            continue
        checks += 1
        if relation(left, right):
            hits += 1
    return (hits / checks) if checks else 0.0


def _sum_relation_ratio(
    rows: list[dict[str, Any]],
    left_key: str,
    right_key: str,
    target_key: str,
) -> float:
    checks = 0
    hits = 0
    for row in rows:
        left = _to_float(row.get(left_key))
        right = _to_float(row.get(right_key))
        target = _to_float(row.get(target_key))
        if left is None or right is None or target is None:
            continue
        checks += 1
        if _approx_equal(left + right, target):
            hits += 1
    return (hits / checks) if checks else 0.0


def _pick_qty_produced_key(
    rows: list[dict[str, Any]],
    stats: dict[str, ColumnStats],
    sold_key: str | None,
    price_key: str | None,
) -> str | None:
    candidates = [
        key for key, stat in stats.items()
        if stat.numeric_ratio >= 0.6 and stat.non_empty >= 2 and key != price_key
    ]
    if not candidates:
        return sold_key

    best_key: str | None = None
    best_score = -1.0
    for key in candidates:
        stat = stats[key]
        score = min(stat.non_empty / 25.0, 1.0) + stat.integer_ratio
        if sold_key:
            score += _comparison_ratio(rows, key, sold_key, lambda left, right: left + 0.01 >= right)
            score += 0.75 * _comparison_ratio(rows, key, sold_key, lambda left, right: left > right + 0.01)
            score += 0.25 * _comparison_ratio(rows, key, sold_key, lambda left, right: _approx_equal(left, right))
            for other_key in candidates:
                if other_key in {key, sold_key}:
                    continue
                score += 1.5 * _sum_relation_ratio(rows, sold_key, other_key, key)
        if key == sold_key:
            score += 0.1

        if score > best_score:
            best_score = score
            best_key = key

    return best_key or sold_key


def _infer_mapping_structurally(rows: list[dict[str, Any]]) -> RegistroMapping | None:
    if not rows:
        return None

    stats = _collect_column_stats(rows)
    if not stats:
        return None

    product_key = None
    best_product_score = -1.0
    for key, stat in stats.items():
        score = _string_column_score(stat)
        if score > best_product_score:
            best_product_score = score
            product_key = key

    numeric_keys = [
        key for key, stat in stats.items()
        if stat.numeric_ratio >= 0.6 and stat.non_empty >= 2
    ]

    unit_price_key = None
    qty_sold_key = None
    best_relation_score = -1.0

    for total_key in numeric_keys:
        for left_key in numeric_keys:
            if left_key == total_key:
                continue
            for right_key in numeric_keys:
                if right_key in {left_key, total_key}:
                    continue

                relation_score, checks = _pair_product_score(rows, left_key, right_key, total_key)
                if checks < 2 or relation_score < 0.6:
                    continue

                left_price_score = _price_column_score(stats[left_key])
                right_price_score = _price_column_score(stats[right_key])
                price_key = left_key if left_price_score >= right_price_score else right_key
                sold_key = right_key if price_key == left_key else left_key
                score = (relation_score * 3.0) + _price_column_score(stats[price_key]) + stats[sold_key].integer_ratio

                if score > best_relation_score:
                    best_relation_score = score
                    unit_price_key = price_key
                    qty_sold_key = sold_key

    if unit_price_key is None and numeric_keys:
        unit_price_key = max(numeric_keys, key=lambda key: _price_column_score(stats[key]))

    if qty_sold_key is None:
        remaining_numeric = [key for key in numeric_keys if key != unit_price_key]
        if remaining_numeric:
            qty_sold_key = max(
                remaining_numeric,
                key=lambda key: min(stats[key].non_empty / 25.0, 1.0) + stats[key].integer_ratio,
            )

    qty_produced_key = _pick_qty_produced_key(rows, stats, qty_sold_key, unit_price_key)
    if qty_produced_key is None:
        qty_produced_key = qty_sold_key

    if product_key is None or unit_price_key is None:
        return None

    score = max(best_product_score, 0.0) + max(best_relation_score, 0.0)
    return RegistroMapping(
        product_key=product_key,
        qty_produced_key=qty_produced_key,
        unit_price_key=unit_price_key,
        qty_sold_key=qty_sold_key or qty_produced_key,
        score=score,
    )


def _mapping_to_dict(mapping: RegistroMapping) -> dict[str, Any]:
    return {
        "product_key": mapping.product_key,
        "qty_produced_key": mapping.qty_produced_key,
        "unit_price_key": mapping.unit_price_key,
        "qty_sold_key": mapping.qty_sold_key,
        "score": mapping.score,
    }


def _mapping_from_dict(payload: Any) -> RegistroMapping | None:
    if not isinstance(payload, dict):
        return None

    product_key = payload.get("product_key")
    unit_price_key = payload.get("unit_price_key")
    qty_produced_key = payload.get("qty_produced_key")
    qty_sold_key = payload.get("qty_sold_key")
    score = payload.get("score", 0.0)

    def _as_key(value: Any) -> str | None:
        value_str = str(value or "").strip()
        return _norm(value_str) if value_str else None

    mapping = RegistroMapping(
        product_key=_as_key(product_key),
        qty_produced_key=_as_key(qty_produced_key),
        unit_price_key=_as_key(unit_price_key),
        qty_sold_key=_as_key(qty_sold_key),
        score=float(score or 0.0),
    )
    return mapping if mapping.product_key and mapping.unit_price_key else None


def _mapping_is_usable(mapping: RegistroMapping | None, rows: list[dict[str, Any]]) -> bool:
    if not mapping or not mapping.product_key or not mapping.unit_price_key:
        return False
    available_keys = {key for row in rows for key in row.keys()}
    needed = {mapping.product_key, mapping.unit_price_key}
    if mapping.qty_produced_key:
        needed.add(mapping.qty_produced_key)
    if mapping.qty_sold_key:
        needed.add(mapping.qty_sold_key)
    return needed.issubset(available_keys)


def _apply_mapping(rows: list[dict[str, Any]], mapping: RegistroMapping) -> list[dict]:
    result: list[dict[str, Any]] = []
    for row in rows:
        product_name = str(row.get(mapping.product_key or "") or "").strip()
        if not product_name:
            continue

        qty_source = mapping.qty_produced_key or mapping.qty_sold_key
        sold_source = mapping.qty_sold_key or mapping.qty_produced_key

        qty_produced = _safe_decimal(row.get(qty_source))
        unit_price = _safe_decimal(row.get(mapping.unit_price_key))
        qty_sold = _safe_decimal(row.get(sold_source))

        if qty_produced == 0 and qty_sold != 0:
            qty_produced = qty_sold
        if qty_sold == 0 and qty_produced != 0:
            qty_sold = qty_produced

        if qty_produced == 0 and unit_price == 0 and qty_sold == 0:
            continue

        result.append(
            {
                "product_name": product_name,
                "qty_produced": qty_produced,
                "unit_price": unit_price,
                "qty_sold": qty_sold,
            }
        )

    return result


def _parse_json_response(content: str) -> dict[str, Any] | None:
    content = str(content or "").strip()
    if not content:
        return None
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 2:
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        payload = json.loads(content)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            try:
                payload = json.loads(content[start : end + 1])
                return payload if isinstance(payload, dict) else None
            except json.JSONDecodeError:
                return None
    return None


async def _infer_mapping_with_ai(
    rows: list[dict[str, Any]],
    sheet_name: str | None,
) -> RegistroMapping | None:
    if not rows:
        return None

    from app.services.ai.base import AITask
    from app.services.ai.service import AIService

    headers = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                headers.append(key)

    sample_rows = [{k: row.get(k) for k in headers[:10]} for row in rows[:8]]
    prompt = (
        "Analyze this spreadsheet sheet and map columns for a daily production log.\n"
        "Return ONLY valid JSON with these exact keys:\n"
        "{\n"
        '  "product_key": "header name or null",\n'
        '  "qty_produced_key": "header name or null",\n'
        '  "unit_price_key": "header name or null",\n'
        '  "qty_sold_key": "header name or null",\n'
        '  "score": 0.0\n'
        "}\n"
        "Rules:\n"
        "- Use header names exactly as provided.\n"
        "- product_key must be the text column with product/item names.\n"
        "- unit_price_key must be the unit sale price column, not a total column.\n"
        "- qty_sold_key must be the sold quantity column.\n"
        "- qty_produced_key must be the produced/available quantity column.\n"
        "- If only one quantity column exists, it can be used for both qty_produced_key and qty_sold_key.\n"
        "- Ignore total/summary columns.\n\n"
        f"Sheet: {sheet_name or 'unknown'}\n"
        f"Headers: {headers}\n"
        f"Sample rows: {sample_rows}\n"
    )

    response = await AIService.query(
        task=AITask.EXTRACTION,
        prompt=prompt,
        temperature=0.1,
        max_tokens=400,
        module="importador",
        enable_recovery=True,
    )
    if response.is_error:
        return None

    return _mapping_from_dict(_parse_json_response(response.content))


def _ensure_daily_log_snapshot(db: Session, tenant_id: UUID, doc: Any, user_id: str | None = None):
    from . import recipe_crud
    from .auto_recipe import resolve_auto_recipe

    snapshot_id = getattr(doc, "recipe_snapshot_id", None)
    if snapshot_id:
        snapshot = recipe_crud.get_snapshot(db, snapshot_id)
        if snapshot:
            return snapshot

    sheet_profiles = getattr(doc, "sheet_profiles_json", None) or {}
    if not sheet_profiles:
        return None

    _, snapshot_id, _, _, _ = resolve_auto_recipe(db, tenant_id, sheet_profiles, created_by=user_id)
    if not snapshot_id:
        return None

    snapshot = recipe_crud.get_snapshot(db, snapshot_id)
    if snapshot and getattr(doc, "recipe_snapshot_id", None) != snapshot.id:
        doc.recipe_snapshot_id = snapshot.id
        db.flush()
    return snapshot


async def resolve_registro_rows(
    db: Session,
    tenant_id: UUID,
    doc: Any,
    user_id: str | None = None,
) -> list[dict]:
    datos = doc.datos_confirmados or doc.datos_extraidos or {}
    if not isinstance(datos, dict):
        return []

    rows_raw, sheet_name = _select_candidate_rows(datos)
    if not rows_raw:
        return []

    normalized_rows = _rows_to_normalized_dicts(rows_raw)
    if not normalized_rows:
        return []

    snapshot = _ensure_daily_log_snapshot(db, tenant_id, doc, user_id=user_id)
    stored_mapping = None
    if snapshot:
        stored_mapping = _mapping_from_dict((snapshot.content_json or {}).get("daily_log_mapping"))
        if not _mapping_is_usable(stored_mapping, normalized_rows):
            stored_mapping = None

    mapping = stored_mapping
    if mapping is None:
        ai_mapping = await _infer_mapping_with_ai(normalized_rows, sheet_name)
        if _mapping_is_usable(ai_mapping, normalized_rows):
            mapping = ai_mapping
            if snapshot:
                content = dict(snapshot.content_json or {})
                content["daily_log_mapping"] = _mapping_to_dict(ai_mapping)
                snapshot.content_json = content
                db.flush()
                db.commit()

    if mapping is None:
        mapping = _infer_mapping_structurally(normalized_rows)

    if not _mapping_is_usable(mapping, normalized_rows):
        return []

    return _apply_mapping(normalized_rows, mapping)


def parse_registro_rows(datos_extraidos: dict) -> list[dict]:
    rows_raw, _sheet_name = _select_candidate_rows(datos_extraidos)
    if not rows_raw:
        return []

    normalized_rows = _rows_to_normalized_dicts(rows_raw)
    if not normalized_rows:
        return []

    mapping = _infer_mapping_structurally(normalized_rows)
    if not _mapping_is_usable(mapping, normalized_rows):
        return []

    return _apply_mapping(normalized_rows, mapping)


def save_daily_log(
    db: Session,
    tenant_id: UUID,
    document_id: UUID,
    log_date: date,
    rows: list[dict],
    replace_existing: bool = True,
) -> dict:
    if replace_existing:
        existing = db.execute(
            select(DailyProductionLog).where(
                and_(
                    DailyProductionLog.tenant_id == str(tenant_id),
                    DailyProductionLog.log_date == log_date,
                    DailyProductionLog.source_document_id == str(document_id),
                )
            )
        ).scalars().all()
        for entry in existing:
            db.delete(entry)

    inserted = 0
    matched = 0
    unmatched: list[str] = []

    for row in rows:
        recipe = _match_recipe(db, tenant_id, row["product_name"])
        product_id = str(recipe.product_id) if recipe and recipe.product_id else None
        recipe_id = str(recipe.id) if recipe else None

        if recipe:
            matched += 1
        else:
            unmatched.append(row["product_name"])

        log = DailyProductionLog(
            tenant_id=str(tenant_id),
            log_date=log_date,
            product_name=row["product_name"],
            recipe_id=recipe_id,
            product_id=product_id,
            qty_produced=row["qty_produced"],
            unit_price=row["unit_price"],
            qty_sold=row["qty_sold"],
            source_document_id=str(document_id),
        )
        db.add(log)
        inserted += 1

    db.commit()
    return {
        "inserted": inserted,
        "matched_recipes": matched,
        "unmatched_products": unmatched,
        "log_date": log_date.isoformat(),
    }
