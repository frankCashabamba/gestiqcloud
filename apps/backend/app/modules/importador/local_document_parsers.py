from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from .document_fields import safe_floatish
from .invoice_ocr_rescue import invoice_rescue_from_ocr


@dataclass(frozen=True, slots=True)
class LocalParseResult:
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()


def _norm(value: Any) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.lower()
    return " ".join(normalized.split())


def _clean_lines(text: str) -> list[str]:
    return [" ".join(line.split()).strip() for line in str(text or "").splitlines() if line.strip()]


def _amounts_from_line(line: str) -> list[float]:
    values: list[float] = []
    for token in re.findall(r"(?<!\d)-?\d{1,6}(?:[.,]\d{2,3})?(?!\d)", str(line or "")):
        parsed = safe_floatish(token)
        if parsed is not None:
            values.append(round(float(parsed), 2))
    return values


def _parse_date(text: str) -> str | None:
    for match in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", str(text or "")):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2099:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def _receipt_vendor(lines: list[str]) -> str | None:
    stop_tokens = {
        "factura",
        "ticket",
        "fecha",
        "total",
        "tarjeta",
        "cambio",
        "iva",
        "cliente",
        "establecimiento",
        "localidad",
    }
    for line in lines[:8]:
        norm = _norm(line)
        if not norm or any(token in norm for token in stop_tokens):
            continue
        if sum(ch.isalpha() for ch in line) < 5:
            continue
        if len(_amounts_from_line(line)) > 0:
            continue
        return line.strip(" -:|")[:140]
    for line in lines:
        norm = _norm(line)
        if "establecimiento" not in norm:
            continue
        value = re.split(r"establecimiento\s*:?", norm, maxsplit=1)
        if len(value) == 2 and value[1].strip():
            return value[1].strip().upper()[:140]
    return None


def _receipt_total(lines: list[str]) -> float | None:
    candidates: list[tuple[int, int, float]] = []
    for idx, line in enumerate(lines):
        norm = _norm(line)
        if any(token in norm for token in ("total art", "art vendidos", "numero operacion")):
            continue
        amounts = [value for value in _amounts_from_line(line) if value > 0]
        if not amounts:
            continue
        score = 0
        if re.search(r"\b(tot|total)\b", norm):
            score += 30
        if "importe" in norm or "moneda" in norm:
            score += 20
        if "tarjeta" in norm or "efectivo" in norm:
            score += 12
        if "cambio" in norm:
            score -= 8
        if "iva" in norm or "base" in norm or "cuota" in norm:
            score -= 12
        candidates.append((score, idx, amounts[-1]))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[2], -item[1]), reverse=True)
    return candidates[0][2]


def _receipt_line_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        norm = _norm(line)
        if any(
            token in norm
            for token in (
                "factura",
                "total",
                "tarjeta",
                "cambio",
                "iva",
                "base",
                "cuota",
                "cliente",
                "establecimiento",
                "fecha",
                "numero",
                "autorizacion",
                "aid",
                "entidad",
            )
        ) or re.search(r"\b(tot|importe)\b", norm):
            continue
        match = re.match(r"^(.+?)\s+(\d{1,5}[.,]\d{2})\s*[A-Z]?\s*$", line)
        if not match:
            continue
        description = match.group(1).strip(" -:|")
        amount = safe_floatish(match.group(2))
        if amount is None or amount <= 0:
            continue
        if sum(ch.isalpha() for ch in description) < 3:
            continue
        items.append(
            {
                "description": description[:160],
                "concept": description[:160],
                "quantity": 1.0,
                "total_price": round(float(amount), 2),
            }
        )
    return items[:80]


def parse_thermal_receipt(text: str) -> LocalParseResult:
    lines = _clean_lines(text)
    fields: dict[str, Any] = {}
    reasons: list[str] = []

    vendor = _receipt_vendor(lines)
    if vendor:
        fields["vendor"] = vendor
        reasons.append("vendor")

    issue_date = _parse_date(text)
    if issue_date:
        fields["issue_date"] = issue_date
        reasons.append("date")

    total = _receipt_total(lines)
    if total is not None:
        fields["total_amount"] = total
        reasons.append("total")

    if any("tarjeta" in _norm(line) for line in lines):
        fields["payment_method"] = "Tarjeta"
        reasons.append("payment_method")
    elif any("efectivo" in _norm(line) for line in lines):
        fields["payment_method"] = "Efectivo"
        reasons.append("payment_method")

    items = _receipt_line_items(lines)
    if items:
        fields["line_items"] = items
        reasons.append("line_items")

    confidence = min(0.55 + len(reasons) * 0.06, 0.82) if fields else 0.0
    return LocalParseResult(fields=fields, confidence=confidence, reasons=tuple(reasons))


def parse_printed_invoice(text: str, *, existing_fields: dict[str, Any] | None = None) -> LocalParseResult:
    rescued = invoice_rescue_from_ocr(text, existing_fields=existing_fields or {})
    reasons = tuple(sorted(rescued.keys()))
    confidence = min(0.58 + len(reasons) * 0.05, 0.84) if rescued else 0.0
    return LocalParseResult(fields=rescued, confidence=confidence, reasons=reasons)


def parse_local_document(
    text: str,
    *,
    family: str,
    existing_fields: dict[str, Any] | None = None,
) -> LocalParseResult:
    normalized_family = str(family or "").upper()
    if normalized_family == "THERMAL_RECEIPT":
        return parse_thermal_receipt(text)
    if normalized_family in {"PRINTED_INVOICE", "SCANNED_PDF"}:
        return parse_printed_invoice(text, existing_fields=existing_fields)
    return LocalParseResult()
