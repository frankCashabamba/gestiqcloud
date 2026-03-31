"""Self-feeding learning for the pre-classifier.

Called after every document confirmation. Updates:
  - imp_filename_pattern : confirms/fails existing patterns, promotes new learned ones
  - imp_header_doc_type  : records canonical field set → doc_type mappings
  - imp_field_alias      : records new column name → canonical field aliases (global, tenant_id=NULL)

Design principles:
  - No human intervention needed for common patterns
  - Confidence is computed from history (confirmed / total), not stored as fixed value
  - Only promotes patterns that are safe: no UUIDs, no pure numbers, no long values
  - Field aliases only learned for short, clean header names (not data values)
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger("importador.classifier_learning")

_MIN_STEM_LEN = 3
_MAX_STEM_LEN = 35
_MIN_ALIAS_LEN = 2
_MAX_ALIAS_LEN = 50


def learn_from_confirmation(
    db: Session,
    *,
    doc_filename: str,
    doc_type_confirmed: str,
    pre_class_layer: str | None,
    pre_class_doc_type: str | None,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
) -> dict[str, int]:
    """
    Main learning entry point. Call after user confirms a document.

    Returns counts: {"filename_patterns": N, "header_mappings": N, "aliases": N}
    """
    doc_type = str(doc_type_confirmed or "").upper().strip()
    if not doc_type or doc_type == "OTHER":
        return {"filename_patterns": 0, "header_mappings": 0, "aliases": 0}

    stats = {
        "filename_patterns": _learn_filename(
            db,
            filename=doc_filename,
            confirmed_type=doc_type,
            pre_class_layer=pre_class_layer,
            pre_class_type=str(pre_class_doc_type or "").upper(),
        ),
        "header_mappings": _learn_header_mapping(
            db,
            headers_norm=headers_norm,
            field_aliases=field_aliases,
            confirmed_type=doc_type,
        ),
        "aliases": _learn_column_aliases(
            db,
            headers_norm=headers_norm,
            field_aliases=field_aliases,
        ),
    }

    if any(v > 0 for v in stats.values()):
        logger.info(
            "Classifier learning: file=%s type=%s layer=%s → %s",
            doc_filename,
            doc_type,
            pre_class_layer or "none",
            stats,
        )
    return stats


# ── Filename learning ───────────────────────────────────────────────────────────

def _learn_filename(
    db: Session,
    *,
    filename: str,
    confirmed_type: str,
    pre_class_layer: str | None,
    pre_class_type: str,
) -> int:
    from sqlalchemy import text as sa_text

    updated = 0

    # Update existing pattern counters when filename_pattern layer fired
    if pre_class_layer == "filename_pattern":
        stem = _normalize_stem(filename)
        if stem:
            col = "confirmed_count" if pre_class_type == confirmed_type else "failed_count"
            try:
                result = db.execute(
                    sa_text(
                        f"UPDATE imp_filename_pattern "  # noqa: S608
                        f"SET {col} = {col} + 1, updated_at = now() "
                        f"WHERE active = TRUE AND :stem ~ pattern"
                    ),
                    {"stem": stem},
                )
                updated += result.rowcount or 0
            except Exception as exc:
                logger.debug("Could not update filename pattern counter: %s", exc)

    # Try to promote this filename as a new learned pattern
    stem = _normalize_stem(filename)
    if not stem or _is_uuid_like(stem):
        return updated

    # Use the first meaningful word as the pattern anchor
    words = stem.split()
    anchor = words[0] if words else ""
    if len(anchor) < _MIN_STEM_LEN or len(anchor) > _MAX_STEM_LEN:
        return updated

    escaped = re.escape(anchor)
    try:
        db.execute(
            sa_text(
                "INSERT INTO imp_filename_pattern "
                "    (pattern, doc_type, base_confidence, confirmed_count, source) "
                "VALUES (:pattern, :doc_type, 0.65, 1, 'learned') "
                "ON CONFLICT (pattern, doc_type) DO UPDATE "
                "    SET confirmed_count = imp_filename_pattern.confirmed_count + 1, "
                "        updated_at = now()"
            ),
            {"pattern": escaped, "doc_type": confirmed_type},
        )
        updated += 1
    except Exception as exc:
        logger.debug("Could not upsert learned filename pattern '%s': %s", anchor, exc)

    return updated


# ── Header → doc_type learning ──────────────────────────────────────────────────

def _learn_header_mapping(
    db: Session,
    *,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
    confirmed_type: str,
) -> int:
    if not headers_norm or not field_aliases:
        return 0

    reverse_map = _build_reverse_alias_map(field_aliases)
    matched = {
        reverse_map[h.strip().lower()]
        for h in headers_norm
        if h.strip().lower() in reverse_map
    }
    if not matched:
        return 0

    fhash = _canonical_fields_hash(sorted(matched))
    from sqlalchemy import text as sa_text

    try:
        db.execute(
            sa_text(
                "INSERT INTO imp_header_doc_type "
                "    (canonical_fields_hash, canonical_fields, doc_type, confirmed_count) "
                "VALUES (:hash, :fields, :doc_type, 1) "
                "ON CONFLICT (canonical_fields_hash) DO UPDATE "
                "    SET confirmed_count = imp_header_doc_type.confirmed_count + 1, "
                "        updated_at = now()"
            ),
            {
                "hash": fhash,
                "fields": sorted(matched),
                "doc_type": confirmed_type,
            },
        )
        return 1
    except Exception as exc:
        logger.debug("Could not upsert header doc type: %s", exc)
        return 0


# ── Column alias learning ───────────────────────────────────────────────────────

def _learn_column_aliases(
    db: Session,
    *,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
) -> int:
    """Record new global aliases for headers that successfully mapped to canonical fields."""
    if not headers_norm or not field_aliases:
        return 0

    reverse_map = _build_reverse_alias_map(field_aliases)
    known_aliases: set[str] = {
        alias.strip().lower()
        for aliases in field_aliases.values()
        for alias in aliases
    }

    from sqlalchemy import text as sa_text

    learned = 0
    for raw_header in headers_norm:
        alias_clean = _normalize_alias(raw_header)
        canonical = reverse_map.get(alias_clean)

        if not canonical:
            continue
        if alias_clean in known_aliases:
            # Already known — just bump last_seen_at
            try:
                db.execute(
                    sa_text(
                        "UPDATE imp_field_alias "
                        "SET confirmed_count = confirmed_count + 1, last_seen_at = now() "
                        "WHERE canonical_field = :c AND alias = :a AND tenant_id IS NULL"
                    ),
                    {"c": canonical, "a": alias_clean},
                )
            except Exception:
                pass
            continue

        if len(alias_clean) < _MIN_ALIAS_LEN or len(alias_clean) > _MAX_ALIAS_LEN:
            continue
        # Skip if looks like a data value (long digit sequences, email-like, etc.)
        if re.search(r"\d{4,}", alias_clean) or "@" in alias_clean:
            continue

        try:
            db.execute(
                sa_text(
                    "INSERT INTO imp_field_alias "
                    "    (tenant_id, canonical_field, alias, priority, source, confirmed_count, last_seen_at) "
                    "VALUES (NULL, :canonical, :alias, 1, 'learned', 1, now()) "
                    "ON CONFLICT (canonical_field, alias) WHERE tenant_id IS NULL DO UPDATE "
                    "    SET confirmed_count = imp_field_alias.confirmed_count + 1, "
                    "        last_seen_at = now()"
                ),
                {"canonical": canonical, "alias": alias_clean},
            )
            known_aliases.add(alias_clean)
            learned += 1
        except Exception as exc:
            logger.debug("Could not learn alias '%s' → %s: %s", alias_clean, canonical, exc)

    return learned


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _normalize_stem(filename: str) -> str:
    stem = Path(filename).stem
    nfd = unicodedata.normalize("NFD", stem)
    stem = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    stem = stem.lower()
    stem = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "", stem
    )
    stem = re.sub(r"\b\d{4}[-_]\d{2}[-_]\d{2}\b", "", stem)
    stem = re.sub(r"\b\d{2}[-_]\d{2}[-_]\d{4}\b", "", stem)
    stem = re.sub(r"\b\d{4,}\b", "", stem)
    stem = re.sub(r"[_\-\.]+", " ", stem)
    return " ".join(stem.split()).strip()


def _normalize_alias(raw: str) -> str:
    nfd = unicodedata.normalize("NFD", str(raw or ""))
    text = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return " ".join(text.split()).strip()


def _is_uuid_like(stem: str) -> bool:
    clean = re.sub(r"[^a-f0-9]", "", stem.lower().replace(" ", ""))
    return len(clean) >= 20 and len(clean) / max(len(stem.replace(" ", "")), 1) > 0.65


def _canonical_fields_hash(fields: list[str]) -> str:
    payload = ",".join(sorted(set(str(f).strip().lower() for f in fields if f)))
    return hashlib.sha256(payload.encode()).hexdigest()


def _build_reverse_alias_map(field_aliases: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            result[alias.strip().lower()] = canonical
    return result
