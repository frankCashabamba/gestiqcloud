"""Pre-classifier: resolve doc_type BEFORE calling the AI when possible.

Layers (evaluated in order):
  L1 — Snapshot cache   (structured docs only) — skip AI entirely, full result cached
  L2 — Filename pattern (all types)            — pre-set doc_type, AI still extracts fields
  L3 — Header mapping   (structured docs only) — pre-set doc_type from confirmed field sets

Returns PreClassResult or None (caller must invoke AI).

All thresholds are loaded from imp_config (module='pre_classifier').
All patterns are loaded from imp_filename_pattern and imp_header_doc_type.
Nothing is hardcoded.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

logger = logging.getLogger("importador.pre_classifier")

_CACHE_TTL = 300.0  # 5 min
_cache: dict[str, tuple[float, Any]] = {}


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class PreClassResult:
    doc_type: str
    confidence: float
    layer: str          # "snapshot_cache" | "filename_pattern" | "header_mapping"
    reasoning: str
    skip_ai: bool = False               # True only for snapshot_cache on structured docs
    cached_analysis: dict | None = None  # Populated when skip_ai=True
    matched_canonicals: list[str] = dc_field(default_factory=list)


# ── Config loading ──────────────────────────────────────────────────────────────

def load_pre_classifier_config(db: Any) -> dict[str, float]:
    """Load thresholds from imp_config (module='pre_classifier'), cached 5 min."""
    entry = _cache.get("config")
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]  # type: ignore[return-value]

    defaults: dict[str, float] = {
        "min_header_confirmations": 2.0,
        "filename_min_confidence": 0.70,
        "header_coverage_min_ratio": 0.50,
        "structured_skip_threshold": 0.75,
        "ocr_weird_ratio_max": 0.15,
    }
    if db is None:
        return defaults

    try:
        from app.models.importador import ImpConfig

        rows = db.query(ImpConfig).filter(ImpConfig.module == "pre_classifier").all()
        cfg = dict(defaults)
        for row in rows:
            key = str(row.key or "").strip()
            val = row.value_text
            if key in cfg and val is not None:
                try:
                    cfg[key] = float(val)
                except (ValueError, TypeError):
                    pass
        _cache["config"] = (time.monotonic(), cfg)
        return cfg
    except Exception as exc:
        logger.debug("Could not load pre_classifier config from DB: %s", exc)
        _cache["config"] = (time.monotonic(), defaults)
        return defaults


def _load_filename_patterns(db: Any) -> list[dict]:
    """Load active filename patterns from imp_filename_pattern, cached 5 min."""
    entry = _cache.get("filename_patterns")
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]  # type: ignore[return-value]

    if db is None:
        _cache["filename_patterns"] = (time.monotonic(), [])
        return []

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                "SELECT pattern, doc_type, base_confidence, confirmed_count, failed_count "
                "FROM imp_filename_pattern "
                "WHERE active = TRUE "
                "ORDER BY base_confidence DESC, confirmed_count DESC"
            )
        ).fetchall()
        patterns = [
            {
                "pattern": str(r[0]),
                "doc_type": str(r[1]).upper(),
                "base_confidence": float(r[2]),
                "confirmed_count": int(r[3]),
                "failed_count": int(r[4]),
            }
            for r in rows
        ]
        _cache["filename_patterns"] = (time.monotonic(), patterns)
        return patterns
    except Exception as exc:
        logger.debug("Could not load filename patterns: %s", exc)
        _cache["filename_patterns"] = (time.monotonic(), [])
        return []


def _load_header_doc_types(db: Any, min_confirmations: int) -> list[dict]:
    """Load confirmed header→doc_type mappings, cached 5 min."""
    entry = _cache.get("header_doc_types")
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]  # type: ignore[return-value]

    if db is None:
        _cache["header_doc_types"] = (time.monotonic(), [])
        return []

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                "SELECT canonical_fields_hash, doc_type, confirmed_count, failed_count "
                "FROM imp_header_doc_type "
                "WHERE active = TRUE AND confirmed_count >= :min_c "
                "ORDER BY confirmed_count DESC"
            ),
            {"min_c": min_confirmations},
        ).fetchall()
        mappings = [
            {
                "hash": str(r[0]),
                "doc_type": str(r[1]).upper(),
                "confirmed_count": int(r[2]),
                "failed_count": int(r[3]),
            }
            for r in rows
        ]
        _cache["header_doc_types"] = (time.monotonic(), mappings)
        return mappings
    except Exception as exc:
        logger.debug("Could not load header doc types: %s", exc)
        _cache["header_doc_types"] = (time.monotonic(), [])
        return []


# ── Main entry point ────────────────────────────────────────────────────────────

def classify_before_ai(
    *,
    db: Any,
    filename: str,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
    cached_analysis: dict | None,
    config: dict[str, float] | None = None,
) -> PreClassResult | None:
    """
    Try to classify without calling the AI.
    Returns PreClassResult or None (let AI handle it).

    - L1: Snapshot cache  → skip_ai=True, full cached result returned
    - L2: Filename match  → skip_ai=False, doc_type hint for AI
    - L3: Header mapping  → skip_ai=False, doc_type hint for AI
      (for structured docs, if confidence >= structured_skip_threshold → skip AI classification)
    """
    cfg = config or load_pre_classifier_config(db)
    filename_min_conf = cfg.get("filename_min_confidence", 0.70)
    min_header_conf = int(cfg.get("min_header_confirmations", 2))

    # L1: Snapshot cache (already resolved by auto_recipe before this call)
    if cached_analysis:
        doc_type = str(cached_analysis.get("doc_type") or "").upper().strip()
        confidence = float(cached_analysis.get("confidence") or 0.0)
        if doc_type and confidence > 0:
            return PreClassResult(
                doc_type=doc_type,
                confidence=confidence,
                layer="snapshot_cache",
                reasoning="Exact header fingerprint from previously confirmed document",
                skip_ai=True,
                cached_analysis=cached_analysis,
            )

    # L2: Filename pattern
    patterns = _load_filename_patterns(db)
    stem = _normalize_filename_stem(filename)
    if stem and not _is_uuid_like(stem):
        for pat in patterns:
            try:
                if re.search(pat["pattern"], stem, re.IGNORECASE):
                    conf = _effective_confidence(
                        pat["base_confidence"],
                        pat["confirmed_count"],
                        pat["failed_count"],
                    )
                    if conf >= filename_min_conf:
                        return PreClassResult(
                            doc_type=pat["doc_type"],
                            confidence=conf,
                            layer="filename_pattern",
                            reasoning=(
                                f"Filename '{stem}' matches pattern '{pat['pattern']}' "
                                f"(confirmed={pat['confirmed_count']}, "
                                f"failed={pat['failed_count']})"
                            ),
                            skip_ai=False,
                        )
            except re.error:
                logger.debug("Invalid regex in imp_filename_pattern: %s", pat["pattern"])
                continue

    # L3: Header canonical field coverage
    if headers_norm and field_aliases:
        reverse_map = _build_reverse_alias_map(field_aliases)
        matched = _match_headers_to_canonical(headers_norm, reverse_map)
        if matched and headers_norm:
            coverage = len(matched) / len(headers_norm)
            min_coverage = cfg.get("header_coverage_min_ratio", 0.50)
            if coverage >= min_coverage:
                fhash = _canonical_fields_hash(sorted(matched))
                mappings = _load_header_doc_types(db, min_header_conf)
                for m in mappings:
                    if m["hash"] == fhash:
                        conf = _effective_confidence(0.75, m["confirmed_count"], m["failed_count"])
                        return PreClassResult(
                            doc_type=m["doc_type"],
                            confidence=conf,
                            layer="header_mapping",
                            reasoning=(
                                f"Headers matched canonical fields {sorted(matched)} "
                                f"→ {m['doc_type']} "
                                f"(confirmed={m['confirmed_count']})"
                            ),
                            skip_ai=False,
                            matched_canonicals=sorted(matched),
                        )

    return None


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _effective_confidence(
    base: float,
    confirmed_count: int,
    failed_count: int,
) -> float:
    """Blend seed confidence with learned ratio once enough data accumulates."""
    total = confirmed_count + failed_count
    if total < 3:
        return float(base)
    ratio = confirmed_count / total
    weight = min(1.0, total / 20.0)  # Full weight at 20+ samples
    return round(float(base) * (1.0 - weight) + ratio * weight, 3)


def _normalize_filename_stem(filename: str) -> str:
    """Extract meaningful part of filename, strip dates/UUIDs/numbers."""
    stem = Path(filename).stem
    # Strip accents
    nfd = unicodedata.normalize("NFD", stem)
    stem = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    stem = stem.lower()
    # Remove UUID patterns
    stem = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", " ", stem
    )
    # Remove date patterns
    stem = re.sub(r"\b\d{4}[-_]\d{2}[-_]\d{2}\b", " ", stem)
    stem = re.sub(r"\b\d{2}[-_]\d{2}[-_]\d{4}\b", " ", stem)
    # Remove pure-number tokens (4+ digits)
    stem = re.sub(r"\b\d{4,}\b", " ", stem)
    # Normalize separators
    stem = re.sub(r"[_\-\.]+", " ", stem)
    return " ".join(stem.split()).strip()


def _is_uuid_like(stem: str) -> bool:
    """True if stem is mostly hex digits — not a meaningful descriptive name."""
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


def _match_headers_to_canonical(
    headers_norm: list[str],
    reverse_map: dict[str, str],
) -> set[str]:
    matched: set[str] = set()
    for h in headers_norm:
        canonical = reverse_map.get(h.strip().lower())
        if canonical:
            matched.add(canonical)
    return matched


def invalidate_pre_classifier_cache() -> None:
    """Force reload from DB on next call."""
    _cache.clear()
