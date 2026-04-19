"""Unified document-field extractors for the importador module.

Historically the AI path (``ai_classifier.py``) and the deterministic text
fallback (``text_fallback_extractor.py``) implemented their own extractors for
the most relevant invoice fields (``total_amount``, ``vendor_name``,
``issue_date``). The two implementations diverged in subtle ways and produced
inconsistent values when the AI classifier failed and the OCR fallback had to
take over.

This module exposes a single set of public extractors that combine the best of
both worlds:

* The label-driven, regex-aware logic from :mod:`.ai_classifier` is preferred
  because it understands amount labels, currency context and stop tokens.
* The line-scoring heuristics from :mod:`.text_fallback_extractor` are used as
  a secondary signal so we still return values when the labelled extractor
  finds nothing (the typical scenario for noisy receipts).

The module is intentionally a thin orchestration layer: it does **not**
re-implement parsing logic. The original private helpers in the two source
modules remain in place so existing tests that import them keep passing. The
functions in this file are the new public API that callers should use.
"""

from __future__ import annotations

from typing import Any

# Local imports are deferred to avoid the circular import between
# ``ai_classifier`` and ``text_fallback_extractor``: both modules import this
# one to delegate to the unified extractors.


def _ensure_lines(text: str | None, lines: list[str] | None) -> list[str]:
    """Return a normalized list of non-empty lines for the given inputs.

    ``text`` and ``lines`` are accepted independently because the legacy AI
    path operates on raw OCR text while the fallback path operates on the
    pre-split lines. When both are provided ``lines`` wins; otherwise the
    text is split.
    """
    if isinstance(lines, list) and lines:
        return [str(line).strip() for line in lines if str(line).strip()]
    if text:
        return [line.strip() for line in str(text).splitlines() if line.strip()]
    return []


def _ensure_text(text: str | None, lines: list[str] | None) -> str:
    """Return the OCR text, reconstructing it from ``lines`` if necessary."""
    if text:
        return str(text)
    if isinstance(lines, list) and lines:
        return "\n".join(str(line) for line in lines)
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Public unified extractors
# ─────────────────────────────────────────────────────────────────────────────


def extract_total_amount(
    text: str | None = None,
    lines: list[str] | None = None,
    *,
    prompt_config: dict[str, Any] | None = None,
) -> float | None:
    """Return the most likely document total.

    Strategy:
      1. Use the label-aware extractor (``_extract_labeled_amount``) which
         understands ``amount_labels`` configuration and handles common
         "TOTAL", "VALOR TOTAL", etc. patterns while rejecting article-count
         "TOTAL ART. VENDIDOS" matches.
      2. Fall back to the contextual maximum extractor when no label hit.
      3. Finally, score lines using the runtime ``total_inference_markers``
         to pick the most plausible value (this is the heuristic the text
         fallback path used historically).
    """
    from .ai_classifier import _extract_contextual_max_amount, _extract_labeled_amount
    from .text_fallback_extractor import _infer_total_amount_from_lines

    content = _ensure_text(text, lines)
    if not content:
        return None

    labeled = _extract_labeled_amount(
        content, "total_amount", prompt_config=prompt_config
    )
    if labeled is not None:
        return labeled

    contextual = _extract_contextual_max_amount(content)
    if contextual is not None:
        return contextual

    return _infer_total_amount_from_lines(_ensure_lines(text, lines))


def extract_vendor_name(
    text: str | None = None,
    lines: list[str] | None = None,
    *,
    ocr_runtime: dict[str, Any] | None = None,
) -> str | None:
    """Return the most likely vendor / issuing-party name.

    The AI-classifier extractor is used first because it implements the
    full set of stop-tokens, suffix detection and proximity-to-RUC scoring
    needed for invoices. When that returns ``None`` the function falls back
    to inferring a short concept-like value from the first lines, which is
    the behaviour the text fallback used to surface for receipts.
    """
    from .ai_classifier import _extract_vendor_name_from_ocr
    from .text_fallback_extractor import _infer_concept_from_lines

    content = _ensure_text(text, lines)
    if not content:
        return None

    candidate = _extract_vendor_name_from_ocr(content, ocr_runtime=ocr_runtime)
    if candidate:
        return candidate

    fallback = _infer_concept_from_lines(_ensure_lines(text, lines))
    return fallback or None


def extract_issue_date(
    text: str | None = None,
    lines: list[str] | None = None,
) -> str | None:
    """Return the most likely issue date in ``YYYY-MM-DD`` format.

    The AI-classifier extractor handles ISO dates, slash-separated dates
    (DD/MM/YYYY and MM/DD/YYYY) and written-out Spanish months with year
    sanity checks. When that returns ``None``, the line-scoring fallback
    looks for ``fecha`` / ``emision`` markers near the date.
    """
    from .ai_classifier import _extract_issue_date_from_ocr
    from .text_fallback_extractor import _infer_issue_date_from_lines

    content = _ensure_text(text, lines)
    if content:
        primary = _extract_issue_date_from_ocr(content)
        if primary:
            return primary

    return _infer_issue_date_from_lines(_ensure_lines(text, lines))


__all__ = [
    "extract_total_amount",
    "extract_vendor_name",
    "extract_issue_date",
]
