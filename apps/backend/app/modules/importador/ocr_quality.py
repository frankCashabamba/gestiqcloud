"""Heurísticas nativas para estimar calidad de texto OCR."""

from __future__ import annotations

import re
from typing import Any

from .runtime_config import load_ocr_runtime_config


def estimate_text_quality(
    text: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
    ai_runtime: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Estimate OCR quality using only local heuristics and runtime config."""
    cfg = ocr_runtime or ai_runtime or load_ocr_runtime_config(None)
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return {"score": 0.0, "chars": 0.0, "words": 0.0}

    chars = len(normalized)
    tokens = re.findall(r"[^\W_]{2,}", normalized, flags=re.UNICODE)
    word_count = len(tokens)
    alpha_chars = sum(1 for ch in normalized if ch.isalpha())
    alnum_chars = sum(1 for ch in normalized if ch.isalnum())
    weird_chars = sum(
        1
        for ch in normalized
        if not (
            ch.isalpha()  # cubre todos los Unicode alphabetic (tildes, ñ, etc.)
            or ch.isdigit()
            or ch.isspace()
            or ch in ".,;:/-_#%()[]{}+*'\"@·•€$£¿¡"  # · separador PDF, ¿¡ español
        )
    )

    alpha_ratio = alpha_chars / max(alnum_chars, 1)
    weird_ratio = weird_chars / max(chars, 1)
    length_score = min(chars / max(float(cfg.get("ocr_length_target_chars") or 1200.0), 1.0), 1.0)
    word_score = min(word_count / max(float(cfg.get("ocr_word_target") or 180.0), 1.0), 1.0)
    alpha_score = min(
        alpha_ratio / max(float(cfg.get("ocr_alpha_ratio_target") or 0.6), 0.01),
        1.0,
    )
    noise_penalty = min(
        weird_ratio / max(float(cfg.get("ocr_noise_ratio_limit") or 0.2), 0.01),
        1.0,
    )

    score = (
        (length_score * float(cfg.get("ocr_score_weight_length") or 0.35))
        + (word_score * float(cfg.get("ocr_score_weight_words") or 0.35))
        + (alpha_score * float(cfg.get("ocr_score_weight_alpha") or 0.2))
        + ((1 - noise_penalty) * float(cfg.get("ocr_score_weight_clean") or 0.1))
    )
    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "chars": float(chars),
        "words": float(word_count),
        "alpha_ratio": round(alpha_ratio, 3),
        "weird_ratio": round(weird_ratio, 3),
    }
