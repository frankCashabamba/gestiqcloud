"""Heuristics to estimate OCR text quality."""

from __future__ import annotations

import re
from typing import Any

from .runtime_config import load_ocr_runtime_config

_USEFUL_MARKERS = (
    "factura",
    "invoice",
    "receipt",
    "ticket",
    "boleta",
    "subtotal",
    "total",
    "tax",
    "iva",
    "igv",
    "vat",
    "fecha",
    "date",
    "ruc",
    "nit",
    "cif",
    "currency",
    "moneda",
    "vendor",
    "proveedor",
    "customer",
    "cliente",
    "description",
    "descripcion",
    "concepto",
    "item",
    "qty",
    "quantity",
    "price",
    "amount",
)


def _count_useful_markers(normalized: str) -> int:
    lowered = normalized.lower()
    return sum(1 for marker in _USEFUL_MARKERS if marker in lowered)


def estimate_text_quality(
    text: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
    ai_runtime: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Estimate OCR quality using local heuristics and runtime config."""
    cfg = ocr_runtime or ai_runtime or load_ocr_runtime_config(None)
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return {"score": 0.0, "chars": 0.0, "words": 0.0}

    chars = len(normalized)
    tokens = re.findall(r"[^\W_]{2,}", normalized, flags=re.UNICODE)
    word_count = len(tokens)
    unique_tokens = {token.lower() for token in tokens}
    repeated_tokens = max(0, len(tokens) - len(unique_tokens))
    repeat_ratio = repeated_tokens / max(len(tokens), 1)
    line_count = sum(1 for line in str(text or "").splitlines() if line.strip())
    useful_hits = _count_useful_markers(normalized)

    alpha_chars = sum(1 for ch in normalized if ch.isalpha())
    digit_chars = sum(1 for ch in normalized if ch.isdigit())
    alnum_chars = sum(1 for ch in normalized if ch.isalnum())
    weird_chars = sum(
        1
        for ch in normalized
        if not (ch.isalpha() or ch.isdigit() or ch.isspace() or ch in ".,;:/-_#%()[]{}+*'\"@$|")
    )

    alpha_ratio = alpha_chars / max(alnum_chars, 1)
    digit_ratio = digit_chars / max(chars, 1)
    weird_ratio = weird_chars / max(chars, 1)

    length_score = min(chars / max(float(cfg.get("ocr_length_target_chars") or 1200.0), 1.0), 1.0)
    word_score = min(word_count / max(float(cfg.get("ocr_word_target") or 180.0), 1.0), 1.0)
    alpha_score = min(
        alpha_ratio / max(float(cfg.get("ocr_alpha_ratio_target") or 0.6), 0.01),
        1.0,
    )
    clean_score = 1.0 - min(
        weird_ratio / max(float(cfg.get("ocr_noise_ratio_limit") or 0.2), 0.01),
        1.0,
    )
    useful_score = min(
        useful_hits / max(float(cfg.get("ocr_useful_marker_target") or 4.0), 1.0),
        1.0,
    )

    repeat_limit = max(float(cfg.get("ocr_repeat_ratio_limit") or 0.35), 0.01)
    repetition_penalty = min(repeat_ratio / repeat_limit, 1.0)
    short_penalty = 0.0
    if chars < int(cfg.get("weak_text_min_chars") or 24):
        short_penalty += 0.22
    if word_count < int(cfg.get("weak_text_min_words") or 4):
        short_penalty += 0.18

    # Use explicit None-check for useful weight so that an explicit 0.0 in the config
    # (e.g. ai_runtime where the 4 primary weights already sum to 1.0) is respected
    # instead of being treated as falsy by the `or` operator.
    _useful_weight_raw = cfg.get("ocr_score_weight_useful")
    _useful_weight = float(_useful_weight_raw) if _useful_weight_raw is not None else 0.15
    base_score = (
        (length_score * float(cfg.get("ocr_score_weight_length") or 0.30))
        + (word_score * float(cfg.get("ocr_score_weight_words") or 0.25))
        + (alpha_score * float(cfg.get("ocr_score_weight_alpha") or 0.15))
        + (clean_score * float(cfg.get("ocr_score_weight_clean") or 0.15))
        + (useful_score * _useful_weight)
    )
    score = base_score
    score *= max(0.45, 1.0 - (repetition_penalty * 0.35))
    score -= short_penalty
    if useful_hits >= 2:
        score += 0.05
    if line_count >= 3 and useful_hits >= 1:
        score += 0.03

    score = max(0.0, min(1.0, score))
    result: dict[str, float] = {
        "score": round(score, 3),
        "chars": float(chars),
        "words": float(word_count),
        "alpha_ratio": round(alpha_ratio, 3),
        "weird_ratio": round(weird_ratio, 3),
        "repeat_ratio": round(repeat_ratio, 3),
        "digit_ratio": round(digit_ratio, 3),
        "unique_word_ratio": round(len(unique_tokens) / max(len(tokens), 1), 3),
        "line_count": float(line_count),
        "useful_hits": float(useful_hits),
    }
    return result
