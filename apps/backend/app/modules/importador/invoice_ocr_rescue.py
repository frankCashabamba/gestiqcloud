from __future__ import annotations

import re
import unicodedata
from typing import Any

from .document_fields import safe_floatish
from .text_fallback_extractor import extract_line_items_table_preview_from_text

_GENERIC_VENDOR_TOKENS = {
    "factura",
    "invoice",
    "ruc",
    "nit",
    "cliente",
    "fecha",
    "direccion",
    "telefono",
    "subtotal",
    "total",
    "iva",
    "autorizacion",
    "emision",
    "ambiente",
    "codigo",
    "cantidad",
    "descripcion",
    "importe",
}

_DOC_NUMBER_LABEL_PATTERNS = (
    r"(?i)\b(?:factura|invoice|fact)\s*(?:n(?:o|ro|umero)?\.?|n[°º])?\s*[:#.-]?\s*([A-Z0-9]{3,}(?:-[A-Z0-9]{2,}){1,3})\b",
    r"(?i)\b(?:n(?:o|ro|umero)?\.?|n[°º]|documento|doc)\s*[:#.-]?\s*([A-Z0-9]{3,}(?:-[A-Z0-9]{2,}){1,3})\b",
    r"\b(\d{3}-\d{3}-\d{6,12})\b",
    # Formatos cortos tipo R-0013, B-001, N-0045 — ticket y recibo sin prefijo largo
    r"(?i)\b(?:n(?:o|ro|umero)?\.?|n[°º]|comprobante|recibo|ticket)\s*[:#.-]?\s*([A-Z]-\d{2,})\b",
)

_BLOCKED_VENDOR_EXACTS = {
    "page 1 of 1",
    "page 1",
    "pagina 1 de 1",
    "gracias por su compra",
    "thanks for your purchase",
    "sales_summary_export",
    "report",
    "export",
    "receipt",
    "ticket",
}

_BLOCKED_VENDOR_PATTERNS = (
    r"(?i)^page\s+\d+\s+of\s+\d+$",
    r"(?i)^pagina\s+\d+\s+de\s+\d+$",
    r"(?i)^gracias\s+por\s+su\s+compra$",
    r"(?i)^thank(s)?\s+you\b",
    r"(?i)\b(?:sales|summary|export|report)\b",
    r"(?i)^[A-Z0-9._-]+\.(?:csv|xlsx|xls|pdf|xml|json)$",
)

_COMPANY_EVIDENCE_PATTERNS = (
    r"(?i)\b(?:s\.?a\.?|c\.?a\.?|ltda\.?|llc|inc\.?|corp\.?|corporation|company|co\.|sas|srl|sl|slu)\b",
    r"(?i)\b(?:ruc|nit|cif)\b",
    r"(?i)\b(?:www\.|https?://|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b",
)


def _is_blocked_vendor_text(text: str) -> bool:
    raw = " ".join(str(text or "").split()).strip(" -:|")
    if not raw:
        return True

    norm = _normalize_text(raw)
    if norm in _BLOCKED_VENDOR_EXACTS:
        return True

    for pattern in _BLOCKED_VENDOR_PATTERNS:
        if re.search(pattern, raw):
            return True

    return False


def _looks_like_filename_or_export(text: str) -> bool:
    raw = str(text or "").strip()
    norm = _normalize_text(raw)
    if "_" in raw and any(token in norm for token in ("export", "summary", "report", "sales")):
        return True
    if re.match(r"^[A-Za-z0-9._-]{6,}\.(csv|xlsx|xls|pdf|xml|json)$", raw, flags=re.I):
        return True
    return False


def _line_has_company_evidence(line: str) -> bool:
    raw = str(line or "").strip()
    return any(re.search(pattern, raw) for pattern in _COMPANY_EVIDENCE_PATTERNS)


def _neighbor_has_company_evidence(lines: list[str], idx: int) -> bool:
    start = max(0, idx - 2)
    end = min(len(lines), idx + 3)
    for pos in range(start, end):
        if pos == idx:
            continue
        if _line_has_company_evidence(lines[pos]):
            return True
    return False


def _looks_like_address_only(text: str) -> bool:
    norm = _normalize_text(text)
    address_hits = sum(
        1
        for token in (
            "calle",
            "av",
            "av.",
            "avenida",
            "urb",
            "sector",
            "barrio",
            "telefono",
            "email",
            "direccion",
            "edificio",
            "piso",
            "oficina",
        )
        if token in norm
    )
    return address_hits >= 2


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or ""))
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(normalized.lower().split())


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line and line.strip()]


def _vendor_header_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in _clean_lines(text):
        norm = _normalize_text(line)
        if any(
            marker in norm
            for marker in (
                "datos del cliente",
                "razon social",
                "nombres y apellidos",
                "customer",
            )
        ):
            break
        lines.append(line)
    return lines[:20]


def _is_missing(value: Any) -> bool:
    return value in (None, "", [], {})


def _looks_invoice_like(text: str, existing_fields: dict[str, Any]) -> bool:
    if any(
        not _is_missing(existing_fields.get(key))
        for key in ("vendor_tax_id", "issue_date", "total_amount", "subtotal", "tax_amount")
    ):
        return True
    norm = _normalize_text(text)
    strong_markers = (
        "factura",
        "invoice",
        "recibo",
        "boleta",
        "ticket",
        "comprobante",
    )
    support_markers = (
        "subtotal",
        "valor total",
        "monto total",
        "total",
        "iva",
        "impuesto",
        "ruc",
        "nit",
        "fecha",
        "proveedor",
        "supplier",
        "documento",
    )
    if any(token in norm for token in strong_markers):
        return True
    return sum(1 for token in support_markers if token in norm) >= 2


def _alpha_count(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def _digit_ratio(text: str) -> float:
    if not text:
        return 1.0
    digits = sum(1 for ch in text if ch.isdigit())
    return digits / max(len(text), 1)


def _is_upperish_company_name(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    uppercase = sum(1 for ch in letters if ch.isupper())
    return uppercase / max(len(letters), 1) >= 0.6


def _has_company_shape(text: str) -> bool:
    norm = _normalize_text(text)
    return any(
        re.search(pattern, norm)
        for pattern in (
            r"\bs\s*\.?\s*a\b",
            r"\bc\s*\.?\s*a\b",
            r"\bcia\.?\b",
            r"\bltda\.?\b",
            r"\bsas\b",
            r"\bcorp\b",
        )
    )


def _contains_address_markers(text: str) -> bool:
    norm = _normalize_text(text)
    return any(token in norm for token in ("calle", "av.", "avenida", "urb", "telefono", "email"))


def _looks_like_generic_header(text: str) -> bool:
    raw = " ".join(str(text or "").split()).strip()
    if not raw:
        return True

    if _is_blocked_vendor_text(raw):
        return True

    tokens = set(_normalize_text(raw).replace(":", " ").split())
    if not tokens:
        return True

    generic_hits = tokens & _GENERIC_VENDOR_TOKENS
    if len(generic_hits) >= 1 and len(tokens) <= 4:
        return True

    if len(generic_hits) >= 2:
        return True

    return False


def _company_candidate_from_line(text: str) -> str:
    raw = " ".join(str(text or "").split()).strip(" -:|")
    if not raw:
        return ""
    split = re.split(
        r"(?:20\d{2}[-/]\d{2}[-/]\d{2}|\bruc\b|\bnit\b|\bcif\b|\bambiente\b|\bproduccion\b|\bautorizacion\b|\bfactura\b)",
        raw,
        maxsplit=1,
        flags=re.I,
    )[0].strip(" -:|")
    if split and _has_company_shape(split):
        return split
    return raw


def _enrich_company_name_from_domain(candidate: str, lines: list[str]) -> str:
    raw = " ".join(str(candidate or "").split()).strip(" -:|")
    if not raw or not _has_company_shape(raw):
        return raw
    tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,}", raw)
    significant = [
        token
        for token in tokens
        if _normalize_text(token) not in {"sa", "s", "a", "ca", "cia", "ltda", "sas"}
    ]
    if not significant:
        return raw
    anchor = significant[-1]
    anchor_norm = _normalize_text(anchor).replace(" ", "")
    for line in lines:
        for match in re.finditer(r"(?:www\.)?([a-z0-9-]{6,})\.[a-z]{2,}", line, flags=re.I):
            domain_stem = match.group(1).lower().replace("-", "")
            if not domain_stem.endswith(anchor_norm):
                continue
            prefix = domain_stem[: -len(anchor_norm)]
            if len(prefix) < 4 or not prefix.isalpha():
                continue
            suffix_match = re.search(r"\b(s\.?\s*a\.?|c\.?\s*a\.?|ltda\.?|sas)\b", raw, flags=re.I)
            suffix = suffix_match.group(1).upper().replace(" ", "") if suffix_match else ""
            suffix = "S.A." if suffix.replace(".", "") == "SA" else suffix
            return " ".join(part for part in (prefix.upper(), anchor.upper(), suffix) if part)
    return raw


def _rescue_vendor(text: str) -> str | None:
    lines = _vendor_header_lines(text)
    candidates: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        raw = _company_candidate_from_line(line)
        if not raw or len(raw) < 5:
            continue

        if _is_blocked_vendor_text(raw):
            continue
        if _looks_like_filename_or_export(raw):
            continue
        if _looks_like_generic_header(raw):
            continue
        if re.search(
            r"(?i)\b(ruc|nit|cedula|cliente|fecha|subtotal|iva|total|autorizacion|ambiente|emision)\b",
            raw,
        ):
            continue
        if _looks_like_address_only(raw):
            continue
        if _digit_ratio(raw) > 0.30 or _alpha_count(raw) < 6:
            continue

        words = raw.split()
        if len(words) > 10:
            continue

        score = 0

        # prioridad a las primeras líneas
        if idx < 5:
            score += 5
        elif idx < 8:
            score += 3

        # forma razonable de razón social
        if 2 <= len(words) <= 6:
            score += 4
        elif len(words) <= 8:
            score += 2

        if _is_upperish_company_name(raw):
            score += 3

        if _has_company_shape(raw):
            score += 4

        # evidencia en líneas vecinas: RUC, email, web, etc.
        if _neighbor_has_company_evidence(lines, idx):
            score += 4

        if _line_has_company_evidence(raw):
            score += 3

        if _contains_address_markers(raw):
            score -= 3

        # castigo a frases demasiado genéricas
        norm = _normalize_text(raw)
        if any(token in norm for token in ("compra", "gracias", "resumen", "export", "reporte")):
            score -= 6

        if re.search(r"(?i)\b(?:page|pagina)\b", raw):
            score -= 8

        candidates.append((score, raw))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_value = candidates[0]
    best_value = _enrich_company_name_from_domain(best_value, lines)
    return best_value[:140] if best_score >= 7 else None


def _rescue_doc_number(text: str) -> str | None:
    header_text = "\n".join(_clean_lines(text)[:25])
    for scope in (header_text, text):
        for pattern in _DOC_NUMBER_LABEL_PATTERNS:
            match = re.search(pattern, scope)
            if not match:
                continue
            value = str(match.group(1) or "").strip(" .:-")
            digits = re.sub(r"\D", "", value)
            if 10 <= len(digits) <= 15 and "-" not in value:
                continue
            if value:
                return value
    return None


def _parse_last_amount(line: str) -> float | None:
    tokens = re.findall(r"-?\$?\s*[\d.,]+", str(line or ""))
    for token in reversed(tokens):
        parsed = safe_floatish(token)
        if parsed is not None:
            return parsed
    return None


def _next_nonempty_amount(lines: list[str], start_index: int) -> float | None:
    for idx in range(start_index + 1, min(len(lines), start_index + 3)):
        parsed = _parse_last_amount(lines[idx])
        if parsed is not None:
            return parsed
    return None


def _rescue_amounts(text: str) -> dict[str, float]:
    rescued: dict[str, float] = {}
    subtotal_candidates: list[float] = []
    tax_candidates: list[float] = []
    lines = _clean_lines(text)
    for index, line in enumerate(lines):
        norm = _normalize_text(line)
        looks_like_subtotal = (
            "subtotal" in norm
            or "sub total" in norm
            or "base imponible" in norm
            or bool(re.search(r"\b(?:s|su|sub|ub)\s*total\b", norm))
            or "sin impuestos" in norm
            or "no objeto de iva" in norm
        )
        if looks_like_subtotal:
            parsed = _parse_last_amount(line)
            if parsed is None:
                parsed = _next_nonempty_amount(lines, index)
            if parsed is not None:
                subtotal_candidates.append(parsed)
        looks_like_tax = (
            (" iva" in f" {norm}" or norm.startswith("iva ") or " impuesto" in f" {norm}")
            and not looks_like_subtotal
            and "no objeto" not in norm
            and "sin impuestos" not in norm
        )
        if looks_like_tax:
            parsed = _parse_last_amount(line)
            percent_match = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*%", line)
            if percent_match and parsed is not None:
                percent_value = safe_floatish(percent_match.group(1))
                if percent_value is not None and abs(parsed - percent_value) < 0.001:
                    parsed = None
            if parsed is None:
                parsed = _next_nonempty_amount(lines, index)
            if parsed is not None:
                tax_candidates.append(parsed)
    if subtotal_candidates:
        rescued["subtotal"] = max(subtotal_candidates)
    if tax_candidates:
        positive_tax = [value for value in tax_candidates if value > 0]
        rescued["tax_amount"] = min(positive_tax) if positive_tax else 0.0
    return rescued


def _line_items_total(items: list[dict[str, Any]]) -> float | None:
    total = 0.0
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        item_total = safe_floatish(item.get("total_price"))
        if item_total is None:
            quantity = safe_floatish(item.get("quantity"))
            unit_price = safe_floatish(item.get("unit_price"))
            if quantity is not None and unit_price is not None:
                item_total = round(quantity * unit_price, 2)
        if item_total is None or item_total <= 0:
            continue
        total += float(item_total)
        count += 1
    return round(total, 2) if count else None


def _rescue_total_amount(
    text: str, *, line_items: list[dict[str, Any]] | None = None
) -> float | None:
    amounts = _rescue_amounts(text)
    item_total = _line_items_total(line_items or [])
    subtotal = amounts.get("subtotal")
    if item_total is not None:
        if subtotal is None or abs(float(subtotal) - item_total) <= 1.0:
            return item_total

    labeled_candidates: list[float] = []
    for index, line in enumerate(_clean_lines(text)):
        norm = _normalize_text(line)
        if not any(
            marker in norm
            for marker in ("valor total", "total a pagar", "importe total", "monto total")
        ):
            continue
        parsed = _parse_last_amount(line)
        if parsed is None:
            parsed = _next_nonempty_amount(_clean_lines(text), index)
        if parsed is not None and parsed > 0:
            labeled_candidates.append(parsed)
    if labeled_candidates:
        labeled = labeled_candidates[-1]
        if item_total is not None and abs(labeled - item_total) <= 5.0:
            return item_total
        if subtotal is not None and abs(labeled - subtotal) <= 5.0:
            return subtotal
        return labeled

    if subtotal is not None and subtotal > 0:
        return subtotal
    return item_total


def _looks_like_totals_or_header(line: str) -> bool:
    norm = _normalize_text(line)
    return any(
        re.search(pattern, norm)
        for pattern in (
            r"\bsubtotal\b",
            r"\bsub total\b",
            r"\bvalor total\b",
            r"\bimporte total\b",
            r"\btotal\b",
            r"\biva\b",
            r"\bcantidad descripcion\b",
            r"\bdescripcion cantidad\b",
        )
    )


def _rescue_flat_line_items(text: str) -> list[dict[str, Any]]:
    try:
        from .ai_classifier import _extract_invoice_line_items_from_ocr

        visual_items = _extract_invoice_line_items_from_ocr(text, ocr_runtime={})
        if visual_items:
            return visual_items[:50]
    except Exception:
        pass

    items: list[dict[str, Any]] = []
    for line in _clean_lines(text):
        if _looks_like_totals_or_header(line):
            continue
        tokens = line.split()
        if len(tokens) < 4:
            continue
        quantity = safe_floatish(tokens[0])
        total_price = safe_floatish(tokens[-1])
        unit_price = safe_floatish(tokens[-2])
        if quantity is None or total_price is None:
            continue
        desc_tokens = tokens[1:-2] if unit_price is not None else tokens[1:-1]
        description = " ".join(desc_tokens).strip()
        if not description or _alpha_count(description) < 3:
            continue
        item: dict[str, Any] = {
            "quantity": quantity,
            "description": description,
            "concept": description,
            "total_price": total_price,
        }
        if unit_price is not None:
            item["unit_price"] = unit_price
        items.append(item)
    return items[:50]


def _rescue_line_items(
    text: str,
    *,
    page_texts: list[str] | None = None,
    field_aliases: dict[str, list[str]] | None = None,
    pdf_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if field_aliases:
        preview = extract_line_items_table_preview_from_text(
            text,
            field_aliases,
            pdf_config=pdf_config,
            page_texts=page_texts,
        )
        if preview.get("line_items"):
            rescued = {"line_items": preview["line_items"]}
            if preview.get("line_item_page_groups"):
                rescued["line_item_page_groups"] = preview["line_item_page_groups"]
            return rescued

    flat_items = _rescue_flat_line_items(text)
    return {"line_items": flat_items} if flat_items else {}


def invoice_rescue_from_ocr(
    text: str,
    existing_fields: dict[str, Any] | None = None,
    *,
    page_texts: list[str] | None = None,
    field_aliases: dict[str, list[str]] | None = None,
    pdf_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = dict(existing_fields or {})
    if not str(text or "").strip() or not _looks_invoice_like(text, existing):
        return {}

    rescued: dict[str, Any] = {}

    if _is_missing(existing.get("vendor")):
        vendor = _rescue_vendor(text)
        if vendor and not _is_blocked_vendor_text(vendor):
            rescued["vendor"] = vendor

    if _is_missing(existing.get("doc_number")):
        doc_number = _rescue_doc_number(text)
        if doc_number:
            rescued["doc_number"] = doc_number

    if _is_missing(existing.get("subtotal")) or _is_missing(existing.get("tax_amount")):
        amounts = _rescue_amounts(text)
        if _is_missing(existing.get("subtotal")) and amounts.get("subtotal") is not None:
            rescued["subtotal"] = amounts["subtotal"]
        if _is_missing(existing.get("tax_amount")) and amounts.get("tax_amount") is not None:
            rescued["tax_amount"] = amounts["tax_amount"]

    rescued_line_items: list[dict[str, Any]] | None = None
    if _is_missing(existing.get("line_items")):
        line_item_rescue = _rescue_line_items(
            text,
            page_texts=page_texts,
            field_aliases=field_aliases,
            pdf_config=pdf_config,
        )
        rescued.update(line_item_rescue)
        if isinstance(line_item_rescue.get("line_items"), list):
            rescued_line_items = line_item_rescue["line_items"]

    if _is_missing(existing.get("total_amount")):
        existing_line_items = existing.get("line_items")
        total_amount = _rescue_total_amount(
            text,
            line_items=(
                rescued_line_items
                if rescued_line_items is not None
                else existing_line_items if isinstance(existing_line_items, list) else None
            ),
        )
        if total_amount is not None:
            rescued["total_amount"] = total_amount

    return rescued
