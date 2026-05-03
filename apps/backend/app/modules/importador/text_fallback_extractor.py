"""DB-driven OCR text fallback extractor.

Used when AI is unavailable (timeout, connection refused, etc.) to extract
fields from raw OCR text using only DB-configured canonical fields, field
aliases, and amount label patterns.  Zero hardcoded field names.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from .document_fields import detect_document_total, safe_floatish
from .runtime_config import load_ocr_runtime_config

logger = logging.getLogger("importador.text_fallback")

# Unidades de medida reconocidas como celdas de columna, no como continuación de descripción.
# Se usa cuando pdf_config no provee unit_values (fallback sin base de datos).
_DEFAULT_UNIT_VALUES: frozenset[str] = frozenset(
    {
        "ml",
        "mg",
        "g",
        "gr",
        "kg",
        "l",
        "lt",
        "lts",
        "ltr",
        "unit",
        "und",
        "unid",
        "unidad",
        "unidades",
        "uds",
        "oz",
        "lb",
        "lbs",
        "pz",
        "pza",
        "pzas",
        "m",
        "cm",
        "mm",
        "m2",
        "m3",
        "caja",
        "caj",
        "bolsa",
        "bol",
        "saco",
        "rollo",
        "par",
    }
)

# Patrones de pie de página que siempre se filtran aunque pdf_config no los provea.
_DEFAULT_FOOTER_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.I)
    for p in (
        r"\bpagina\s+\d",  # "Pagina 1 de 3"
        r"\bpage\s+\d",  # "Page 1 of 3"
        r"\bpag\.?\s+\d",  # "Pag. 1"
    )
)

# Patrones que indican el inicio de una sección post-tabla (observaciones, totales, firmas).
# Cuando aparecen en la tabla vertical, el parser detiene la lectura de ítems.
_SECTION_END_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.I)
    for p in (
        r"^\s*observaciones?\s*$",
        r"^\s*notas?\s*$",
        r"^\s*condiciones?\s*$",
        r"^\s*resumen\b",
        r"^\s*terminos?\b",
        r"^\s*firma\b",
        r"^\s*autorizado\b",
        r"^\s*recibido\s+por\b",
        r"^\s*_+\s*$",  # línea de guiones bajos (espacio para firma)
        r"^\s*-{5,}\s*$",  # separador con guiones
    )
)

# Patrones de filas que NO son ítems de producto sino totales, métodos de pago,
# referencias o pies de recibo. Se filtran para no contaminar la tabla.
_NON_PRODUCT_ROW_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.I)
    for p in (
        r"^\s*subtotal\b",
        r"^\s*total\b",
        r"^\s*totales?\b",
        r"^\s*iva\b",
        r"^\s*tax\b",
        r"^\s*impuesto\b",
        r"^\s*payment\b",
        r"^\s*pago\b",
        r"^\s*metodo\b",
        r"^\s*method\b",
        r"^\s*mastercard\b",
        r"^\s*visa\b",
        r"^\s*amex\b",
        r"^\s*american\s+express\b",
        r"^\s*discover\b",
        r"^\s*tarjeta\b",
        r"^\s*card\s+ending\b",
        r"^\s*ending\s+in\b",
        r"^\s*see\s+https?://",
        r"^\s*ver\s+https?://",
        r"https?://\S+\s*$",
        r"^\s*page\s+\d",
        r"^\s*pagina\s+\d",
        r"^\s*pag\.?\s+\d",
    )
)


def _is_non_product_row(line: str) -> bool:
    """True si la línea es un total, método de pago, URL o pie de página."""
    return any(pattern.search(line) for pattern in _NON_PRODUCT_ROW_PATTERNS)


def _item_looks_non_product(item: dict[str, Any]) -> bool:
    """Detecta items parseados que en realidad son footers / referencias / totales.

    Los parsers verticales arman cada celda desde una línea distinta, por lo que
    los patrones de ``_is_non_product_row`` no aplican. Aquí concatenamos los
    valores del item ya armado y revisamos los mismos patrones, además de
    detectar URLs en cualquier celda.
    """
    if not isinstance(item, dict):
        return False
    parts: list[str] = []
    for key, value in item.items():
        if key == "extra_columns" and isinstance(value, dict):
            for sub_value in value.values():
                if sub_value is None:
                    continue
                parts.append(str(sub_value))
            continue
        if value is None:
            continue
        parts.append(str(value))
    if not parts:
        return False
    joined = " ".join(parts).strip()
    if not joined:
        return False
    if _is_non_product_row(joined):
        return True
    # Cualquier celda con URL marca el item como no-producto.
    if any("http://" in p.lower() or "https://" in p.lower() for p in parts):
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_label(text: str) -> str:
    """Lowercase + strip accents + collapse whitespace for label matching."""
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(normalized.lower().split())


def _repair_split_header_tokens(
    tokens: list[str],
    matched_fields: list[str],
    reverse_map: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Merge adjacent OCR header tokens when they form a recognized header label."""
    if len(tokens) < 2 or len(tokens) != len(matched_fields):
        return tokens, matched_fields

    index = 0
    while index < len(tokens) - 1:
        combined = f"{tokens[index]} {tokens[index + 1]}".strip()
        canonical = reverse_map.get(combined)
        if canonical:
            first_known = bool(matched_fields[index])
            second_known = bool(matched_fields[index + 1])
            if (
                not first_known
                or not second_known
                or matched_fields[index] == matched_fields[index + 1]
            ):
                tokens[index : index + 2] = [combined]
                matched_fields[index : index + 2] = [canonical]
                continue
        elif not matched_fields[index] and not matched_fields[index + 1]:
            canonical = _generic_header_to_canonical(combined)
            if canonical:
                tokens[index : index + 2] = [combined]
                matched_fields[index : index + 2] = [canonical]
                continue
        index += 1

    return tokens, matched_fields


def _prepare_lines(ocr_text: str) -> list[str]:
    """Split OCR text into clean lines, preserving originals for value extraction."""
    return [line for line in ocr_text.splitlines() if line.strip()]


def _effective_page_texts(ocr_text: str, page_texts: list[str] | None) -> list[str]:
    """Return a per-page text list when available, otherwise a single-document fallback."""
    if isinstance(page_texts, list) and page_texts:
        normalized = [str(text or "") for text in page_texts]
        if any(text.strip() for text in normalized):
            return normalized
    return [ocr_text]


def _parse_date(raw: str) -> str | None:
    """Parse common date formats into YYYY-MM-DD.  Returns None on failure."""
    raw = raw.strip()[:30]

    # YYYY-MM-DD already
    m = re.match(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", raw)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", raw)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year}-{month:02d}-{day:02d}"
        # Possibly MM/DD/YYYY
        if 1 <= day <= 12 and 1 <= month <= 31:
            return f"{year}-{day:02d}-{month:02d}"

    # DD/MM/YY
    m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})(?!\d)", raw)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = 2000 + int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year}-{month:02d}-{day:02d}"

    return None


def _parse_numeric(raw: str) -> float | None:
    """Extract a numeric value from a text segment using safe_floatish."""
    # Try the whole segment first
    result = safe_floatish(raw)
    if result is not None:
        return result

    # Find the last amount-looking token (e.g. "$ 16,567.49" or "14.792,40")
    tokens = re.findall(r"[\d.,]+(?:\.\d+)?", raw)
    for token in reversed(tokens):
        result = safe_floatish(token)
        if result is not None:
            return result
    return None


def _parse_text(raw: str) -> str | None:
    """Clean a text value.  Returns None if empty."""
    cleaned = " ".join(raw.split()).strip()
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# Spec builder
# ---------------------------------------------------------------------------

_FieldSpec = dict  # {"type": str, "labels": list[str], "labels_norm": list[str]}

_GENERIC_HEADER_TO_CANONICAL: tuple[tuple[str, str], ...] = (
    ("fecha", "issue_date"),
    ("cant", "quantity"),
    ("cantidad", "quantity"),
    ("qty", "quantity"),
    ("descrip", "description"),
    ("descripcion", "description"),
    ("unit price", "unit_price"),
    ("precio unit", "unit_price"),
    ("p.unit", "unit_price"),
    ("p. unitario", "unit_price"),
    ("unitario", "unit_price"),
    ("v.unit", "unit_price"),
    ("unit", "unit_price"),
    ("v.total", "total_price"),
    ("valor total", "total_price"),
    ("importe", "total_price"),
    ("total", "total_price"),
    ("subtotal", "subtotal"),
    ("iva", "tax_amount"),
    ("impuesto", "tax_amount"),
    ("cliente", "customer"),
    ("proveedor", "vendor"),
)

_GENERIC_ROW_FIELDS: frozenset[str] = frozenset(
    {
        "issue_date",
        "quantity",
        "unit_price",
        "total_price",
        "description",
        "customer",
        "vendor",
        "subtotal",
        "tax_amount",
        "currency",
        "doc_number",
    }
)


def _build_specs(
    canonical_fields: dict[str, dict],
    field_aliases: dict[str, list[str]],
    amount_labels: dict[str, list[str]],
) -> dict[str, _FieldSpec]:
    """Build extraction specs for each canonical field from DB config."""
    specs: dict[str, _FieldSpec] = {}
    for field_name, field_config in canonical_fields.items():
        field_type = field_config.get("type", "text")
        if field_type == "list":
            continue  # line_items not supported in text fallback

        labels: list[str] = []
        # Add aliases from imp_field_alias
        for alias in field_aliases.get(field_name, []):
            if alias not in labels:
                labels.append(alias)
        # Add amount_label_config entries (total_amount, subtotal, tax_amount...)
        for extra in amount_labels.get(field_name, []):
            if extra not in labels:
                labels.append(extra)
        # Include the canonical field name itself
        if field_name not in labels:
            labels.append(field_name)

        if not labels:
            continue

        # Sort longest first for greedy matching
        labels.sort(key=lambda s: len(s), reverse=True)

        specs[field_name] = {
            "type": field_type,
            "labels": labels,
            "labels_norm": [_normalize_label(lb) for lb in labels],
        }
    return specs


def _generic_header_to_canonical(label: str) -> str | None:
    """Map common OCR table headers to canonical keys when no DB alias matches."""
    norm = _normalize_label(label)
    if not norm:
        return None
    compact = re.sub(r"[^\w]+", " ", norm).strip()
    for token, canonical in _GENERIC_HEADER_TO_CANONICAL:
        if token in {norm, compact}:
            return canonical
        if token in norm or token in compact:
            return canonical
    return None


def _looks_like_generic_header_token(token: str) -> bool:
    norm = _normalize_label(token)
    if not norm:
        return False
    if len(norm) > 24 and len(norm.split()) > 3:
        return False
    if _generic_header_to_canonical(norm):
        return True
    return norm in {
        "pedidos",
        "items",
        "pedido",
        "linea",
        "lineas",
        "cantidad",
        "cant",
        "descripcion",
        "cliente",
        "ruc",
        "nit",
    }


def _looks_like_tax_id_value(raw: str) -> bool:
    """Heuristic guard for RUC/NIT/CEDULA-like values.

    We only accept values that contain enough digits to plausibly be an ID,
    so an address line after `RUC:` is not misread as a tax identifier.
    """
    digits = re.sub(r"\D", "", str(raw or ""))
    return 8 <= len(digits) <= 15


def _is_tax_id_label(label_norm: str) -> bool:
    return any(
        token in label_norm
        for token in (
            "ruc",
            "nit",
            "cedula",
            "identificacion",
            "tax id",
            "tax_id",
            "nif",
        )
    )


def _looks_like_address_only(text: str) -> bool:
    norm = _normalize_label(text)
    address_hits = sum(
        1
        for token in (
            "calle",
            "avenida",
            "av ",
            "av.",
            "direccion",
            "dirección",
            "telefono",
            "teléfono",
            "email",
            "correo",
            "piso",
            "oficina",
            "urb",
            "sector",
            "barrio",
        )
        if token in norm
    )
    return address_hits >= 2


def _extract_inline_pipe_table(ocr_text: str) -> list[dict[str, Any]]:
    """Fallback para tablas inline separadas por '|' cuando OCR colapsa las líneas."""
    raw_tokens = [
        token.strip() for token in re.split(r"\s*\|\s*|\t+", str(ocr_text or "")) if token.strip()
    ]
    if len(raw_tokens) < 6:
        return []

    start_idx = None
    for idx, token in enumerate(raw_tokens):
        if _looks_like_generic_header_token(token):
            start_idx = idx
            break
    if start_idx is None:
        return []

    headers: list[str] = []
    data_start = start_idx
    for idx in range(start_idx, len(raw_tokens)):
        token = raw_tokens[idx]
        if _looks_like_generic_header_token(token):
            headers.append(token)
            data_start = idx + 1
            continue
        if len(headers) < 3 and not re.search(r"\d", token):
            headers.append(token)
            data_start = idx + 1
            continue
        break

    if len(headers) < 3:
        return []

    remaining = raw_tokens[data_start:]
    if len(remaining) < len(headers):
        return []

    items: list[dict[str, Any]] = []
    row_size = len(headers)
    for offset in range(0, len(remaining) - row_size + 1, row_size):
        chunk = remaining[offset : offset + row_size]
        row: dict[str, Any] = {}
        for header, value in zip(headers, chunk):
            clean_value = str(value or "").strip().strip("|")
            if not clean_value:
                continue
            canonical = _generic_header_to_canonical(header)
            if canonical == "issue_date":
                parsed_date = _parse_date(clean_value)
                if parsed_date is not None:
                    row[canonical] = parsed_date
                else:
                    row[canonical] = clean_value
            elif canonical in {"quantity", "unit_price", "total_price", "subtotal", "tax_amount"}:
                parsed_num = _parse_numeric(clean_value)
                if parsed_num is not None:
                    row[canonical] = parsed_num
                else:
                    row[canonical] = clean_value
            elif canonical:
                row[canonical] = clean_value
            else:
                row.setdefault("extra_columns", {})[header] = clean_value
        if row:
            items.append(row)

    return items


def _looks_like_payroll_document(lines: list[str]) -> bool:
    if not lines:
        return False

    joined = " ".join(_normalize_label(line) for line in lines[:120])
    markers = (
        "devengos",
        "deducciones",
        "liquido a percibir",
        "liquido",
        "base irpf",
        "base ss",
        "cotizacion",
        "trabajador",
        "empresa",
    )
    hits = sum(1 for marker in markers if marker in joined)
    return hits >= 3 or ("devengos" in joined and "deducciones" in joined)


def _parse_compact_invoice_line_item(line: str) -> dict[str, Any] | None:
    """Parse compact invoice/photo rows with code, barcode, qty, description and amounts."""
    raw = str(line or "").strip()
    if not raw:
        return None

    amount_pattern = re.compile(r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)")
    matches = list(amount_pattern.finditer(raw))
    if len(matches) < 3:
        return None

    qty_match, unit_match, total_match = matches[-3], matches[-2], matches[-1]
    quantity = safe_floatish(qty_match.group(0))
    unit_price = safe_floatish(unit_match.group(0))
    total_price = safe_floatish(total_match.group(0))
    if quantity is None or unit_price is None or total_price is None:
        return None

    prefix = raw[: qty_match.start()].strip()
    prefix = prefix.strip("|{}[]")
    prefix_tokens = [token.strip("{}[]|") for token in re.split(r"\s+", prefix) if token.strip()]
    if not prefix_tokens:
        return None

    product_code = None
    barcode = None
    if re.fullmatch(r"[A-Z0-9][A-Z0-9\-]{2,}", prefix_tokens[0]):
        product_code = prefix_tokens.pop(0)
    if prefix_tokens and re.fullmatch(r"\d{8,15}", re.sub(r"\D", "", prefix_tokens[0])):
        barcode = re.sub(r"\D", "", prefix_tokens.pop(0))

    description = " ".join(prefix_tokens).strip(" -:|/{}[]")
    description = re.sub(r"^[^A-Za-zÁÉÍÓÚÑáéíóúñ]+", "", description).strip()
    if not description:
        return None

    return {
        "product_code": product_code,
        "barcode": barcode,
        "quantity": round(float(quantity), 2),
        "unit_price": round(float(unit_price), 2),
        "total_price": round(float(total_price), 2),
        "amount": round(float(total_price), 2),
        "description": description,
        "concept": description,
        "raw_text": raw,
    }


def _extract_compact_invoice_items(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        item = _parse_compact_invoice_line_item(line)
        if item is not None:
            items.append(item)
    return items


def _parse_compact_invoice_line_item_relaxed(line: str) -> dict[str, Any] | None:
    raw = str(line or "").strip()
    if not raw:
        return None

    amount_pattern = re.compile(r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)")
    matches = list(amount_pattern.finditer(raw))
    if len(matches) < 3:
        return None

    qty_match, unit_match, total_match = matches[-3], matches[-2], matches[-1]
    quantity = safe_floatish(qty_match.group(0))
    unit_price = safe_floatish(unit_match.group(0))
    total_price = safe_floatish(total_match.group(0))
    if quantity is None or unit_price is None or total_price is None:
        return None

    prefix = raw[: qty_match.start()].strip().strip("|{}[]")
    prefix_tokens = [token.strip("{}[]|") for token in re.split(r"\s+", prefix) if token.strip()]
    if not prefix_tokens:
        return None

    product_code = None
    barcode = None
    if re.fullmatch(r"[A-Z0-9][A-Z0-9\-]{2,}", prefix_tokens[0]):
        product_code = prefix_tokens.pop(0)
    if prefix_tokens and re.fullmatch(r"\d{8,15}", re.sub(r"\D", "", prefix_tokens[0])):
        barcode = re.sub(r"\D", "", prefix_tokens.pop(0))

    middle_segment = raw[qty_match.end() : unit_match.start()].strip().strip("|{}[]")
    middle_segment = re.sub(r"^[^A-Za-zÃÃ‰ÃÃ“ÃšÃ‘Ã¡Ã©Ã­Ã³ÃºÃ±]+", "", middle_segment).strip()
    description = middle_segment or " ".join(prefix_tokens).strip(" -:|/{}[]")
    description = re.sub(r"^[^A-Za-zÃÃ‰ÃÃ“ÃšÃ‘Ã¡Ã©Ã­Ã³ÃºÃ±]+", "", description).strip()
    if not description:
        return None

    return {
        "product_code": product_code,
        "barcode": barcode,
        "quantity": round(float(quantity), 2),
        "unit_price": round(float(unit_price), 2),
        "total_price": round(float(total_price), 2),
        "amount": round(float(total_price), 2),
        "description": description,
        "concept": description,
        "raw_text": raw,
    }


def _extract_compact_invoice_items_relaxed(lines: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in lines:
        item = _parse_compact_invoice_line_item_relaxed(line)
        if item is not None:
            items.append(item)
    return items


def _parse_payroll_row(line: str, *, section: str, index: int) -> dict[str, Any] | None:
    raw = str(line or "").strip()
    if not raw:
        return None

    amount_pattern = re.compile(r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)")
    matches = list(amount_pattern.finditer(raw))
    if not matches:
        return None

    amount_match = matches[-1]
    amount = safe_floatish(amount_match.group(0))
    if amount is None:
        return None

    prefix = raw[: amount_match.start()].strip()
    prefix_tokens = [
        token.strip(" *-:|/{}[]") for token in re.split(r"\s+", prefix) if token.strip()
    ]
    if not prefix_tokens:
        return None

    quantity = None
    unit_price = None
    code = None
    cursor = 0
    if cursor < len(prefix_tokens) and safe_floatish(prefix_tokens[cursor]) is not None:
        quantity = safe_floatish(prefix_tokens[cursor])
        cursor += 1
    if cursor < len(prefix_tokens) and safe_floatish(prefix_tokens[cursor]) is not None:
        unit_price = safe_floatish(prefix_tokens[cursor])
        cursor += 1
    if cursor < len(prefix_tokens):
        code_candidate = re.sub(r"\D", "", prefix_tokens[cursor])
        if code_candidate and len(code_candidate) <= 5:
            code = code_candidate
            cursor += 1

    concept = " ".join(prefix_tokens[cursor:]).strip(" *-:|/{}[]")
    if not concept:
        return None

    return {
        "section": section,
        "code": code,
        "quantity": round(float(quantity), 2) if quantity is not None else None,
        "unit_price": round(float(unit_price), 3) if unit_price is not None else None,
        "total_price": round(float(amount), 2),
        "amount": round(float(amount), 2),
        "description": concept,
        "concept": concept,
        "raw_text": raw,
        "row_index": index,
    }


def _extract_payroll_items(lines: list[str]) -> list[dict[str, Any]]:
    if not _looks_like_payroll_document(lines):
        return []

    start_idx = None
    for idx, line in enumerate(lines):
        norm = _normalize_label(line)
        if "concepto" in norm:
            window_end = min(idx + 5, len(lines))
            window = [_normalize_label(lines[j]) for j in range(idx, window_end)]
            if any("devengos" in item for item in window) and any(
                "deducciones" in item for item in window
            ):
                last_heading = max(
                    j
                    for j in range(idx, window_end)
                    if "devengos" in _normalize_label(lines[j])
                    or "deducciones" in _normalize_label(lines[j])
                )
                start_idx = last_heading + 1
                break
    if start_idx is None:
        for idx, line in enumerate(lines):
            norm = _normalize_label(line)
            if "devengos" in norm:
                window_end = min(idx + 5, len(lines))
                if any("deducciones" in _normalize_label(lines[j]) for j in range(idx, window_end)):
                    last_heading = max(
                        j
                        for j in range(idx, window_end)
                        if "devengos" in _normalize_label(lines[j])
                        or "deducciones" in _normalize_label(lines[j])
                    )
                    start_idx = last_heading + 1
                    break
    if start_idx is None:
        return []

    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        norm = _normalize_label(lines[idx])
        norm_words = re.sub(r"[^a-z0-9]+", " ", norm).strip()
        if any(
            marker in norm
            for marker in (
                "rem total",
                "t devengado",
                "base s.s",
                "liquido a percibir",
                "liquido",
                "iban",
                "swift",
                "coste empresa",
            )
        ) or any(marker in norm_words for marker in ("rem total", "t devengado")):
            end_idx = idx
            break

    deduction_start = next(
        (
            idx
            for idx in range(max(0, start_idx - 5), end_idx)
            if "deducciones" in _normalize_label(lines[idx])
        ),
        end_idx,
    )

    items: list[dict[str, Any]] = []
    for idx in range(start_idx, end_idx):
        line = lines[idx].strip()
        norm = _normalize_label(line)
        if not line or any(token in norm for token in ("concepto", "devengos", "deducciones")):
            continue
        if not re.search(r"\d", line):
            continue
        section = "DEDUCCION" if idx >= deduction_start else "DEVENGO"
        parsed = _parse_payroll_row(line, section=section, index=idx)
        if parsed is not None:
            items.append(parsed)

    return items


def _parse_loose_number(token: str) -> float | None:
    text = re.sub(r"[^0-9,.-]", "", str(token or "").strip())
    if not text:
        return None

    sign = -1.0 if text.startswith("-") else 1.0
    text = text.lstrip("-")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            normalized = text.replace(".", "").replace(",", ".")
        else:
            normalized = text.replace(",", "")
    elif "," in text:
        normalized = text.replace(".", "").replace(",", ".")
    elif "." in text:
        parts = text.split(".")
        normalized = text if len(parts) <= 2 else text.replace(".", "")
    else:
        normalized = text

    try:
        return sign * float(normalized)
    except ValueError:
        return None


def _parse_payroll_row_relaxed(line: str, *, section: str, index: int) -> dict[str, Any] | None:
    raw = str(line or "").strip()
    if not raw:
        return None

    amount_pattern = re.compile(r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)")
    matches = list(amount_pattern.finditer(raw))
    if not matches:
        return None

    total_match = matches[-1]
    amount = _parse_loose_number(total_match.group(0))
    if amount is None:
        return None

    prefix = raw[: total_match.start()].strip().strip("|{}[]")
    tokens = [token.strip(" *-:|/{}[]") for token in re.split(r"\s+", prefix) if token.strip()]
    if not tokens:
        return None

    code = None
    quantity = None
    unit_price = None
    cursor = 0

    if cursor < len(tokens) and re.fullmatch(r"\d{1,5}", re.sub(r"\D", "", tokens[cursor])):
        next_token = tokens[cursor + 1] if cursor + 1 < len(tokens) else ""
        if not re.search(r"[A-Za-z]", next_token):
            code = re.sub(r"\D", "", tokens[cursor])
            cursor += 1
        elif len(tokens[cursor]) > 5:
            quantity = _parse_loose_number(tokens[cursor])
            cursor += 1

    if cursor < len(tokens) and quantity is None:
        token = tokens[cursor]
        if re.search(r"[.,]", token):
            quantity = _parse_loose_number(token)
            if quantity is not None:
                cursor += 1

    if cursor < len(tokens):
        token = tokens[cursor]
        if re.search(r"[.,]", token):
            unit_price = _parse_loose_number(token)
            if unit_price is not None:
                cursor += 1

    if quantity is None and tokens:
        trailing_token = tokens[-1]
        if re.search(r"[.,]", trailing_token):
            quantity = _parse_loose_number(trailing_token)
            if quantity is not None and cursor < len(tokens) and tokens[-1] == trailing_token:
                tokens = tokens[:-1]

    concept_tokens = tokens[cursor:]
    if quantity is not None and concept_tokens and re.search(r"[.,]", concept_tokens[-1]):
        maybe_number = _parse_loose_number(concept_tokens[-1])
        if maybe_number is not None:
            if unit_price is None:
                unit_price = maybe_number
            concept_tokens = concept_tokens[:-1]

    concept = " ".join(concept_tokens).strip(" *-:|/{}[]")
    if not concept:
        concept = " ".join(tokens).strip(" *-:|/{}[]")
    if not concept:
        return None

    return {
        "section": section,
        "code": code,
        "quantity": round(float(quantity), 2) if quantity is not None else None,
        "unit_price": round(float(unit_price), 3) if unit_price is not None else None,
        "total_price": round(float(amount), 2),
        "amount": round(float(amount), 2),
        "description": concept,
        "concept": concept,
        "raw_text": raw,
        "row_index": index,
    }


def _extract_payroll_items_relaxed(lines: list[str]) -> list[dict[str, Any]]:
    if not _looks_like_payroll_document(lines):
        return []

    start_idx = None
    for idx, line in enumerate(lines):
        norm = _normalize_label(line)
        if "concepto" in norm:
            window_end = min(idx + 5, len(lines))
            window = [_normalize_label(lines[j]) for j in range(idx, window_end)]
            if any("devengos" in item for item in window) and any(
                "deducciones" in item for item in window
            ):
                last_heading = max(
                    j
                    for j in range(idx, window_end)
                    if "devengos" in _normalize_label(lines[j])
                    or "deducciones" in _normalize_label(lines[j])
                )
                start_idx = last_heading + 1
                break
    if start_idx is None:
        for idx, line in enumerate(lines):
            norm = _normalize_label(line)
            if "devengos" in norm:
                window_end = min(idx + 5, len(lines))
                if any("deducciones" in _normalize_label(lines[j]) for j in range(idx, window_end)):
                    last_heading = max(
                        j
                        for j in range(idx, window_end)
                        if "devengos" in _normalize_label(lines[j])
                        or "deducciones" in _normalize_label(lines[j])
                    )
                    start_idx = last_heading + 1
                    break
    if start_idx is None:
        return []

    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        norm = _normalize_label(lines[idx])
        norm_words = re.sub(r"[^a-z0-9]+", " ", norm).strip()
        if any(
            marker in norm
            for marker in (
                "base s.s",
                "liquido a percibir",
                "liquido",
                "iban",
                "swift",
                "coste empresa",
            )
        ) or any(marker in norm_words for marker in ("rem total", "t devengado")):
            end_idx = idx
            break

    items: list[dict[str, Any]] = []
    deduction_markers = (
        "cotizacion",
        "tributacion",
        "deduccion",
        "dcto",
        "irpf",
        "mei",
        "formacion",
        "desempleo",
        "seguridad",
        "cont.comu",
    )
    for idx in range(start_idx, end_idx):
        line = lines[idx].strip()
        norm = _normalize_label(line)
        norm_words = re.sub(r"[^a-z0-9]+", " ", norm).strip()
        if not line or norm in {"concepto", "devengos", "deducciones"}:
            continue
        if (
            any(marker in norm_words for marker in ("rem total", "t devengado", "t a deducir"))
            or "REM." in line.upper()
        ):
            continue
        if not re.search(r"\d", line):
            continue
        section = "DEDUCCION" if any(marker in norm for marker in deduction_markers) else "DEVENGO"
        parsed = _parse_payroll_row_relaxed(line, section=section, index=idx)
        if parsed is not None:
            items.append(parsed)

    return items


def _infer_payroll_metadata(
    lines: list[str], payroll_items: list[dict[str, Any]]
) -> dict[str, Any]:
    if not _looks_like_payroll_document(lines):
        return {}

    result: dict[str, Any] = {}

    if lines:
        first_line = _parse_text(lines[0])
        if first_line and len(first_line.split()) <= 8:
            result["employee_name"] = first_line

    for idx, line in enumerate(lines[:40]):
        norm = _normalize_label(line)
        if "empresa" in norm and idx + 1 < len(lines):
            for look_ahead in range(idx + 1, min(idx + 8, len(lines))):
                company_line = str(lines[look_ahead] or "").strip()
                company_norm = _normalize_label(company_line)
                if not company_line or any(
                    marker in company_norm
                    for marker in (
                        "domicilio",
                        "trabajador",
                        "categoria",
                        "antiguedad",
                        "periodo",
                        "nif",
                    )
                ):
                    continue
                if (
                    re.search(r"\b(?:s\.l\.u\.|s\.l\.|s\.a\.|slu|sa)\b", company_norm)
                    or "," in company_line
                ):
                    company_candidate = re.split(r"\s{2,}", company_line)[0].strip()
                    company_candidate = company_candidate.strip(" |")
                    if company_candidate:
                        result.setdefault("company_name", company_candidate)
                        break
        if "trabajador" in norm and idx + 1 < len(lines):
            worker_candidate = _parse_text(lines[idx + 1])
            if worker_candidate:
                result.setdefault("employee_name", worker_candidate)
        if "periodo" in norm:
            for look_ahead in range(idx + 1, min(idx + 8, len(lines))):
                period_candidate = _parse_text(lines[look_ahead])
                if not period_candidate:
                    continue
                period_norm = _normalize_label(period_candidate)
                if re.search(r"\b\d{2}\s+[A-Z]{3}\s+\d{2}\b", period_norm):
                    result.setdefault("payroll_period", period_candidate)
                    break
        if "liquido a percibir" in norm or ("liquido" in norm and "percibir" in norm):
            amounts = _find_amounts(line)
            if amounts:
                result["liquido_a_percibir"] = round(float(amounts[-1]), 2)
            else:
                for look_ahead in range(idx + 1, min(idx + 4, len(lines))):
                    amounts = _find_amounts(lines[look_ahead])
                    if amounts:
                        result["liquido_a_percibir"] = round(float(amounts[-1]), 2)
                        break

    devengos_total = 0.0
    deducciones_total = 0.0
    for item in payroll_items:
        amount = safe_floatish(item.get("total_price"))
        if amount is None:
            amount = safe_floatish(item.get("amount"))
        if amount is None:
            continue
        section = str(item.get("section") or "").upper()
        if section == "DEDUCCION":
            deducciones_total += float(amount)
        else:
            devengos_total += float(amount)

    if devengos_total:
        result["gross_pay"] = round(devengos_total, 2)
    if deducciones_total:
        result["deductions_total"] = round(deducciones_total, 2)
    if devengos_total and deducciones_total:
        inferred_net = round(devengos_total - deducciones_total, 2)
        result.setdefault("liquido_a_percibir", inferred_net)
        result.setdefault("total_amount", result["liquido_a_percibir"])

    return result


def _all_known_labels_norm(specs: dict[str, _FieldSpec]) -> set[str]:
    """Collect all normalized labels across specs (for boundary detection)."""
    result: set[str] = set()
    for spec in specs.values():
        result.update(spec["labels_norm"])
    return result


# ---------------------------------------------------------------------------
# Pattern matchers
# ---------------------------------------------------------------------------

_Candidate = tuple[Any, int]  # (parsed_value, score)


def _is_label_line(line_norm: str, all_labels: set[str]) -> bool:
    """Check whether a normalized line is or starts with a known label."""
    stripped = re.sub(r"[:：\-–—#]?\s*$", "", line_norm).strip()
    if stripped in all_labels:
        return True
    # Also check if the line starts with a label followed by a separator
    for label in all_labels:
        if stripped.startswith(label) and len(stripped) > len(label):
            after = stripped[len(label)]
            if after in " :：-–—#.":
                return True
    return False


def _match_same_line(
    spec: _FieldSpec,
    line: str,
    line_norm: str,
) -> list[_Candidate]:
    """Try 'Label[...]: Value' or 'Label[...]  Value' on a single line.

    Handles variations like:
      - "RUC: 1792845612001"         (label + separator + value)
      - "Factura No. FAC-2026-0487"  (label + extra words + separator + value)
      - "IVA 12%  $ 1,775.09"       (label + noise + value)
      - "Subtotal  $ 14,792.40"     (label + whitespace + value)
    """
    candidates: list[_Candidate] = []
    for label_norm in spec["labels_norm"]:
        if label_norm not in line_norm:
            continue
        escaped = re.escape(label_norm)
        # Pattern 1: label at line start + optional extra text + explicit separator + value
        # e.g. "Factura No. FAC-2026-0487" or "Fecha de emision: 03/04/2026"
        p1 = rf"^{escaped}[\w\s%#]*?(?:[:：]|\.)\s+(.+)"
        m = re.search(p1, line_norm)
        if m:
            raw_value = line[m.start(1) :].strip()
            if raw_value:
                candidates.append((raw_value, 20 + len(label_norm)))
                continue
        # Pattern 2: label at line start + 2+ spaces or $ sign + value
        # e.g. "Subtotal  $ 14,792.40" or "Total $ 16,567.49"
        p2 = rf"^{escaped}[\w\s.%#]*?(?:\s{{2,}}|\s*\$\s*)(.+)"
        m = re.search(p2, line_norm)
        if m:
            raw_value = line[m.start(1) :].strip()
            if raw_value:
                candidates.append((raw_value, 18 + len(label_norm)))
                continue
        # Pattern 3: label + single whitespace + value.
        # This is common in scanned PDFs where OCR collapses "Fecha 2026-03-21"
        # or "Total 1.00 USD" into one line without punctuation.
        if spec["type"] in ("numeric", "number", "date"):
            p3 = rf"^{escaped}[\w\s.%#]*?\s+(.+)"
            m = re.search(p3, line_norm)
            if m:
                raw_value = line[m.start(1) :].strip()
                if raw_value:
                    parsed_value = _parse_value(raw_value, spec["type"])
                    if parsed_value is not None:
                        candidates.append((raw_value, 17 + len(label_norm)))
        elif _is_tax_id_label(label_norm):
            p3 = rf"^{escaped}[\w\s.%#]*?\s+(.+)"
            m = re.search(p3, line_norm)
            if m:
                raw_value = line[m.start(1) :].strip()
                if raw_value and _looks_like_tax_id_value(raw_value):
                    candidates.append((raw_value, 17 + len(label_norm)))
        elif spec["type"] == "text":
            p3 = rf"^{escaped}[\w\s.%#]*?\s+(.+)"
            m = re.search(p3, line_norm)
            if m:
                raw_value = line[m.start(1) :].strip()
                if raw_value and not _looks_like_tax_id_value(raw_value):
                    if len(raw_value) <= 80 and len(raw_value.split()) <= 8:
                        candidates.append((raw_value, 16 + len(label_norm)))
    return candidates


def _match_next_line(
    spec: _FieldSpec,
    lines: list[str],
    lines_norm: list[str],
    index: int,
    all_labels: set[str],
) -> list[_Candidate]:
    """Try 'Label\\nValue' across two lines."""
    candidates: list[_Candidate] = []
    line_norm = lines_norm[index]
    stripped = re.sub(r"[:：\-–—#]?\s*$", "", line_norm).strip()

    for label_norm in spec["labels_norm"]:
        # Label-only line: exact match, or starts with label + non-alpha
        # e.g. "iva 12%" matches alias "iva", "subtotal" matches exactly
        if stripped != label_norm and not (
            stripped.startswith(label_norm)
            and len(stripped) > len(label_norm)
            and not stripped[len(label_norm)].isalpha()
        ):
            continue
        # Label-only line found; next non-empty line is the value
        if spec["type"] in ("numeric", "number"):
            max_capture = 4 if "total" in label_norm else 2
        elif spec["type"] == "date":
            max_capture = 1
        else:
            max_capture = 2
        value_parts: list[str] = []
        for j in range(index + 1, min(index + 1 + max_capture, len(lines))):
            next_norm = lines_norm[j]
            if _is_label_line(next_norm, all_labels):
                break
            value_parts.append(lines[j].strip())
        if not value_parts:
            continue
        raw_value = " ".join(value_parts)
        if _is_tax_id_label(label_norm) and not _looks_like_tax_id_value(raw_value):
            continue
        score = 15 + len(label_norm)
        candidates.append((raw_value, score))
    return candidates


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------


def _parse_value(raw: str, field_type: str) -> Any | None:
    """Parse a raw text candidate according to canonical field type."""
    if field_type in ("numeric", "number"):
        return _parse_numeric(raw)
    if field_type == "date":
        return _parse_date(raw)
    return _parse_text(raw)


def _best_candidate(candidates: list[_Candidate], field_type: str) -> Any | None:
    """Pick the best candidate from scored matches."""
    if not candidates:
        return None
    # Sort by score descending
    candidates.sort(key=lambda c: c[1], reverse=True)
    for raw_value, _score in candidates:
        parsed = _parse_value(raw_value, field_type)
        if parsed is not None:
            return parsed
    return None


def _find_first_date(text: str) -> str | None:
    """Find the first parseable date in a text fragment."""
    for match in re.finditer(r"\b\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}\b", str(text or "")):
        parsed = _parse_date(match.group(0))
        if parsed is not None:
            return parsed
    return None


def _find_amounts(text: str) -> list[float]:
    """Return all parseable amounts found in a text fragment."""
    values: list[float] = []
    amount_pattern = re.compile(r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)")
    for match in amount_pattern.finditer(str(text or "")):
        parsed = safe_floatish(match.group(0))
        if parsed is not None:
            values.append(parsed)
    return values


def _infer_issue_date_from_lines(lines: list[str]) -> str | None:
    """Infer a likely issue date from generic OCR lines."""
    if not lines:
        return None

    date_markers = (
        "fecha",
        "emision",
        "emisión",
        "operacion",
        "operación",
        "valor",
        "vencimiento",
        "expedicion",
        "expedición",
    )

    scored: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        norm = _normalize_label(line)
        if not norm:
            continue
        date = _find_first_date(line)
        if date is None and idx + 1 < len(lines):
            date = _find_first_date(lines[idx + 1])
        if date is None and idx > 0:
            date = _find_first_date(lines[idx - 1])
        if date is None:
            continue

        score = 0
        if any(marker in norm for marker in date_markers):
            score += 20
        if "fecha" in norm:
            score += 8
        if idx < 12:
            score += 4
        if re.search(r"\bfecha\s+(valor|operacion|operación|emision|emisión)\b", norm):
            score += 8
        scored.append((score, -idx, date))

    if scored:
        scored.sort(reverse=True)
        return scored[0][2]

    for line in lines:
        date = _find_first_date(line)
        if date is not None:
            return date
    return None


def _infer_total_amount_from_lines(lines: list[str]) -> float | None:
    """Infer a likely total/amount from generic OCR lines."""
    if not lines:
        return None

    cfg = load_ocr_runtime_config(None)
    reject_total_patterns: list[re.Pattern[str]] = []
    for raw in cfg.get("total_amount_reject_patterns") or []:
        pattern = str(raw or "").strip()
        if not pattern:
            continue
        try:
            reject_total_patterns.append(re.compile(pattern))
        except re.error as exc:
            logger.warning(
                "Ignoring invalid OCR regex for total_amount_reject_patterns: %s (%s)", pattern, exc
            )
    amount_markers = {
        _normalize_label(str(marker))
        for marker in (cfg.get("total_inference_markers") or [])
        if str(marker).strip()
    }

    scored: list[tuple[int, int, float]] = []
    for idx, line in enumerate(lines):
        norm = _normalize_label(line)
        if not norm:
            continue
        if any(pattern.search(norm) for pattern in reject_total_patterns):
            continue
        amounts = _find_amounts(line)
        if not amounts:
            continue

        score = 0
        if any(marker and marker in norm for marker in amount_markers):
            score += 20
        if re.search(r"\b(total|importe|monto|cuota)\b", norm):
            score += 10
        if "eur" in norm or "usd" in norm or "$" in line or "€" in line:
            score += 4
        if idx < 12:
            score += 2
        if len(amounts) == 1:
            score += 1
        for amount in amounts:
            scored.append((score, -idx, amount))

    if scored:
        scored.sort(reverse=True)
        return round(float(scored[0][2]), 2)

    return None


def _infer_concept_from_lines(lines: list[str]) -> str | None:
    """Infer a short human-readable concept/title from the OCR text."""
    if not lines:
        return None

    concept_markers = (
        "nota de venta",
        "detalle del movimiento",
        "compra",
        "cuota",
        "recibo",
        "ticket",
        "factura",
        "boleta",
        "movimiento",
    )

    for idx, line in enumerate(lines[:20]):
        norm = _normalize_label(line)
        if not norm or _looks_like_address_only(norm):
            continue
        if any(marker in norm for marker in concept_markers):
            cleaned = _parse_text(line)
            if cleaned and len(cleaned) <= 80:
                return cleaned.strip(" -:|'\"")

    for line in lines[:10]:
        cleaned = _parse_text(line)
        if not cleaned or _looks_like_address_only(cleaned):
            continue
        if re.search(r"\d", cleaned):
            continue
        if 3 <= len(cleaned.split()) <= 8:
            return cleaned.strip(" -:|'\"")
    return None


def _infer_payment_method_from_lines(lines: list[str]) -> str | None:
    """Infer a simple payment method from OCR text."""
    if not lines:
        return None

    payment_markers = (
        "tarjeta",
        "efectivo",
        "transferencia",
        "debito",
        "débito",
        "credito",
        "crédito",
        "bizum",
        "yape",
        "plin",
        "deposito",
        "depósito",
        "cajero",
        "cuenta",
    )

    for line in lines:
        norm = _normalize_label(line)
        if any(marker in norm for marker in payment_markers):
            for marker in payment_markers:
                if marker in norm:
                    pretty = marker.replace("  ", " ").strip()
                    return pretty.title()
            cleaned = _parse_text(line)
            if cleaned and len(cleaned) <= 60:
                return cleaned.strip(" -:|'\"")
    return None


def _looks_like_sales_summary_export(lines: list[str]) -> bool:
    if not lines:
        return False

    joined = " ".join(_normalize_label(line) for line in lines[:30])
    if "sales_summary_export" in joined or "sales summary export" in joined:
        return True
    return all(marker in joined for marker in ("fecha", "pedidos", "items", "total"))


def _infer_sales_summary_total(lines: list[str]) -> float | None:
    if not _looks_like_sales_summary_export(lines):
        return None

    data_rows = [line for line in lines if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", line)]
    if len(data_rows) > 1:
        last_row = data_rows[-1]
        cells = [cell.strip() for cell in re.split(r"\s*\|\s*", last_row) if cell.strip()]
        if len(cells) >= 3:
            items_value = _parse_loose_number(cells[2])
            if items_value is not None:
                return round(float(items_value), 2)

    currency_amounts: list[float] = []
    numeric_tokens: list[float] = []
    numeric_pattern = re.compile(r"(?<!\d)(-?\d+(?:[.,]\d+)?)(?!\d)")
    for line in lines:
        norm = _normalize_label(line)
        if any(token in norm for token in ("$", "eur", "usd", "€")):
            currency_amounts.extend(_find_amounts(line))
        for match in numeric_pattern.finditer(line):
            parsed = _parse_loose_number(match.group(1))
            if parsed is not None:
                numeric_tokens.append(parsed)

    if currency_amounts:
        return round(float(currency_amounts[-1]), 2)
    if numeric_tokens:
        return round(float(numeric_tokens[-1]), 2)
    return None


def _infer_sales_summary_issue_date(lines: list[str]) -> str | None:
    if not _looks_like_sales_summary_export(lines):
        return None

    dates = []
    for line in lines:
        match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", line)
        if match:
            dates.append(match.group(1))
    return dates[-1] if dates else None


def _looks_like_bank_statement(lines: list[str]) -> bool:
    if not lines:
        return False

    joined = " ".join(_normalize_label(line) for line in lines[:60])
    joined_words = re.sub(r"[^a-z0-9]+", " ", joined).strip()
    markers = (
        "detalle del movimiento",
        "transferencias emitidas",
        "fecha de envio",
        "fecha valor",
        "fecha de la operacion",
        "nuestra referencia",
        "importe a liquidar",
        "importe ordenado",
        "contravalor",
        "titular",
        "beneficiario",
    )
    if sum(1 for marker in markers if marker in joined or marker in joined_words) >= 2:
        return True
    if "santander" in joined and ("movimiento" in joined or "transferencias emitidas" in joined):
        return True
    if "ibercaja" in joined and ("transferencias emitidas" in joined or "concepto" in joined):
        return True
    return False


def _clean_bank_item_description(text: str) -> str | None:
    cleaned = _parse_text(text) or str(text or "")
    if not cleaned.strip():
        return None

    cleaned = cleaned.replace(">>", " ")
    cleaned = re.sub(
        r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"\b(?:eur|usd|€)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:|'\"")
    norm = _normalize_label(cleaned)
    boilerplate_markers = (
        "por cuenta de",
        "importe ordenado",
        "importe a liquidar",
        "ultimo beneficiario",
        "ultima beneficiaria",
        "beneficiario",
        "titular",
        "contravalor",
        "nuestra referencia",
        "total nuestros gastos",
        "fecha de envio",
        "fecha de operacion",
        "fecha valor",
        "tipo operacion",
        "gastos por cuenta",
        "transferencias emitidas",
        "oficina",
        "entidad",
        "iban",
        "cuenta:",
    )
    if any(marker in norm for marker in boilerplate_markers) and not any(
        marker in norm for marker in ("compra", "tarjeta", "piso", "alquiler")
    ):
        return None
    return cleaned or None


def _dedupe_bank_statement_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []

    stopwords = {
        "por",
        "cuenta",
        "importe",
        "ordenado",
        "liquidar",
        "ultimo",
        "ultima",
        "beneficiario",
        "beneficiaria",
        "titular",
        "contravalor",
        "nuestra",
        "referencia",
        "total",
        "nuestros",
        "gastos",
        "fecha",
        "envio",
        "operacion",
        "valor",
        "tipo",
        "transferencias",
        "emitidas",
        "oficina",
        "entidad",
        "iban",
        "eur",
        "usd",
    }
    seen: set[tuple[float, str]] = set()
    deduped: list[dict[str, Any]] = []

    for item in items:
        amount = safe_floatish(item.get("amount"))
        if amount is None:
            amount = safe_floatish(item.get("total_price"))
        amount_value = round(float(amount or 0.0), 2)

        description = _normalize_label(str(item.get("description") or item.get("concept") or ""))
        description = re.sub(r"^\W+", " ", description)
        tokens = [
            token
            for token in description.split()
            if len(token) > 1 and token not in stopwords and not token.isdigit()
        ]
        if not tokens:
            tokens = [
                token for token in description.split() if len(token) > 1 and not token.isdigit()
            ]
        signature = " ".join(tokens[:10]).strip()
        key = (amount_value, signature)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def _extract_bank_statement_items(lines: list[str]) -> list[dict[str, Any]]:
    if not _looks_like_bank_statement(lines):
        return []

    items: list[dict[str, Any]] = []
    amount_pattern = re.compile(r"(?P<sign>[-+])?\s*(?P<amount>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")
    bank_markers = (
        "compra",
        "tarjeta",
        "detalle del movimiento",
        "transferencias emitidas",
        ">>",
    )

    for idx, line in enumerate(lines):
        norm = _normalize_label(line)
        if not norm or not re.search(r"\d", line):
            continue
        if not any(marker in norm for marker in bank_markers):
            continue

        amounts: list[float] = []
        for match in amount_pattern.finditer(line):
            raw_amount = match.group("amount")
            if not raw_amount:
                continue
            signed_amount = raw_amount
            prefix = line[: match.start()]
            if match.group("sign") == "-" or re.search(r"[-−]\s*$", prefix):
                signed_amount = f"-{raw_amount}"
            parsed = safe_floatish(signed_amount)
            if parsed is not None:
                amounts.append(parsed)
        amounts = [amount for amount in amounts if amount is not None]
        if not amounts:
            continue

        description = _clean_bank_item_description(line)
        if not description:
            continue

        issue_date = None
        for nearby in (
            line,
            lines[idx - 1] if idx > 0 else "",
            lines[idx + 1] if idx + 1 < len(lines) else "",
        ):
            issue_date = _find_first_date(nearby)
            if issue_date is not None:
                break

        amount = float(amounts[-1])
        items.append(
            {
                "description": description,
                "concept": description,
                "issue_date": issue_date,
                "quantity": None,
                "unit_price": None,
                "total_price": round(amount, 2),
                "amount": round(amount, 2),
                "raw_text": line,
            }
        )

    return _dedupe_bank_statement_items(items)


def _infer_bank_statement_total(items: list[dict[str, Any]], lines: list[str]) -> float | None:
    if items:
        amounts: list[float] = []
        for item in items:
            amount = safe_floatish(item.get("amount"))
            if amount is None:
                amount = safe_floatish(item.get("total_price"))
            if amount is not None:
                amounts.append(float(amount))
        if amounts:
            joined = " ".join(_normalize_label(line) for line in lines[:80])
            negative_amounts = [amount for amount in amounts if amount < 0]
            if negative_amounts and "transferencias emitidas" in joined:
                return round(float(negative_amounts[0]), 2)
            rounded_unique = {round(amount, 2) for amount in amounts}
            if len(rounded_unique) == 1:
                return round(float(amounts[0]), 2)
            total = sum(amounts)
            if abs(total) > 0.01:
                return round(total, 2)

    signed_amount_pattern = re.compile(
        r"(?P<prefix>[-−]?\s*)(?P<amount>\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"
    )
    movement_negatives: list[float] = []
    for line in lines:
        norm = _normalize_label(line)
        if not any(
            marker in norm for marker in ("compra", "tarjeta", "transferencias emitidas", ">>")
        ):
            continue
        for match in signed_amount_pattern.finditer(line):
            raw_amount = match.group("amount")
            prefix = line[: match.start()]
            if "-" not in match.group("prefix") and not re.search(r"[-−]\s*$", prefix):
                continue
            parsed = safe_floatish(f"-{raw_amount}")
            if parsed is not None:
                movement_negatives.append(float(parsed))
    if movement_negatives:
        return round(float(movement_negatives[0]), 2)

    for label in ("importe a liquidar", "importe ordenado", "contravalor", "saldo", "importe"):
        for line in lines:
            norm = _normalize_label(line)
            if label in norm:
                signed_amounts: list[float] = []
                for match in signed_amount_pattern.finditer(line):
                    raw_amount = match.group("amount")
                    prefix = line[: match.start()]
                    signed = (
                        f"-{raw_amount}"
                        if "-" in match.group("prefix") or re.search(r"[-−]\s*$", prefix)
                        else raw_amount
                    )
                    parsed = safe_floatish(signed)
                    if parsed is not None:
                        signed_amounts.append(float(parsed))
                if signed_amounts:
                    negatives = [amount for amount in signed_amounts if amount < 0]
                    return round(float((negatives or signed_amounts)[-1]), 2)
    return None


_SPANISH_MONTHS = {
    "ene": 1,
    "enero": 1,
    "feb": 2,
    "febrero": 2,
    "mar": 3,
    "marzo": 3,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "jul": 7,
    "julio": 7,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "sept": 9,
    "septiembre": 9,
    "oct": 10,
    "octubre": 10,
    "nov": 11,
    "noviembre": 11,
    "dic": 12,
    "diciembre": 12,
}


def _infer_receipt_metadata(lines: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in lines:
        raw = str(line or "").strip()
        norm = _normalize_label(raw)
        if "cuota" not in norm:
            continue

        concept = _parse_text(raw)
        if concept:
            concept = re.sub(
                r"\bCUOTA\s+([A-ZÃÃ‰ÃÃ“ÃšÃ‘]{3,12})\s*/\s*(20\d{2})\b",
                r"CUOTA \1./\2",
                concept,
                flags=re.I,
            )
            concept = re.sub(
                r"\s+(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})\s*$",
                "",
                concept,
            ).strip(" |")
            result["concept"] = concept

        match = re.search(r"\bcuota\s+([a-zÃ¡Ã©Ã­Ã³ÃºÃ±]{3,12})\.?\s*/\s*(20\d{2})", norm)
        if match:
            month = _SPANISH_MONTHS.get(match.group(1).strip("."))
            if month is not None:
                result["issue_date"] = f"{int(match.group(2)):04d}-{month:02d}-01"
        break
    return result


def _looks_like_ticket_document(lines: list[str]) -> bool:
    if not lines:
        return False

    joined = " ".join(_normalize_label(line) for line in lines[:40])
    markers = ("ticket de venta", "productos", "subtotal", "total", "pagos", "cash")
    simplified_markers = (
        "factura simplificada",
        "factura simplif",
        "nota de venta",
        "para el cliente",
        "establecimiento",
        "localidad",
        "numero operacion",
        "importe / moneda",
        "importe moneda",
    )
    if "ticket" in joined and any(
        marker in joined for marker in ("total", "subtotal", "pagos", "cash", "productos")
    ):
        return True
    if sum(1 for marker in simplified_markers if marker in joined) >= 3 and any(
        marker in joined for marker in ("tarjeta", "efectivo", "cambio", "importe")
    ):
        return True
    return sum(1 for marker in markers if marker in joined) >= 3


def _extract_pos_receipt_metadata(lines: list[str]) -> dict[str, Any]:
    if not _looks_like_ticket_document(lines):
        return {}

    result: dict[str, Any] = {}
    stop_prefixes = (
        "factura simplif",
        "factura simplificada",
        "nota de venta",
        "para el cliente",
        "localidad",
        "fecha",
        "numero tarjeta",
        "numero operacion",
        "tipo de transaccion",
        "codigo respuesta",
        "importe / moneda",
        "importe moneda",
        "numero autorizacion",
        "etiqueta apli",
        "verificacion usuario",
        "entidad",
        "imp.",
        "iva",
        "cambio",
        "tarjeta",
        "subtotal",
        "total",
    )

    for line in lines[:25]:
        raw = " ".join(str(line or "").split()).strip()
        if not raw:
            continue
        norm = _normalize_label(raw)
        if norm.startswith("establecimiento"):
            vendor = _parse_text(raw.split(":", 1)[-1]) if ":" in raw else _parse_text(raw)
            if vendor:
                result["vendor"] = _clean_pos_receipt_vendor(vendor.strip(" -:|'\""))
                break

    if "vendor" not in result:
        for line in lines[:8]:
            raw = " ".join(str(line or "").split()).strip()
            if not raw:
                continue
            norm = _normalize_label(raw)
            if any(norm.startswith(prefix) for prefix in stop_prefixes):
                continue
            if re.search(r"\d", raw):
                continue
            candidate = _parse_text(raw) or raw
            if candidate and 1 <= len(candidate.split()) <= 5:
                result["vendor"] = _clean_pos_receipt_vendor(candidate.strip(" -:|'\""))
                break

    for line in lines:
        raw = " ".join(str(line or "").split()).strip()
        norm = _normalize_label(raw)
        if "fecha" in norm:
            parsed_date = _find_first_date(raw)
            if parsed_date is not None:
                result["issue_date"] = parsed_date
                break

    for line in lines:
        raw = " ".join(str(line or "").split()).strip()
        norm = _normalize_label(raw)
        if "numero operacion" in norm:
            match = re.search(r"(\d{3,})", raw)
            if match:
                result["doc_number"] = match.group(1)
                break

    total_candidates: list[float] = []
    for line in lines:
        raw = " ".join(str(line or "").split()).strip()
        norm = _normalize_label(raw)
        if not raw or any(
            token in norm
            for token in (
                "num. total",
                "num total",
                "iva",
                "imp.",
                "base",
                "cuota",
                "numero tarjeta",
                "numero operacion",
                "numero autorizacion",
                "referencia",
                "aid",
                "verificacion usuario",
            )
        ):
            continue
        if any(
            token in norm
            for token in (
                "importe / moneda",
                "importe moneda",
                "tarjeta",
                "efectivo",
                "cambio",
                "total",
            )
        ):
            amounts = _find_amounts(raw)
            if amounts:
                total_candidates.append(float(amounts[-1]))
    if total_candidates:
        result["total_amount"] = round(max(total_candidates), 2)

    for line in lines:
        norm = _normalize_label(line)
        if "tarjeta" in norm:
            result["payment_method"] = "Tarjeta"
            break
        if "efectivo" in norm:
            result["payment_method"] = "Efectivo"
            break

    header_done = False
    for line in lines[:20]:
        raw = " ".join(str(line or "").split()).strip()
        if not raw:
            continue
        norm = _normalize_label(raw)
        if "simplif" in norm or norm.startswith("nota de venta"):
            header_done = True
            continue
        if not header_done:
            continue
        if any(norm.startswith(prefix) for prefix in stop_prefixes):
            continue
        if len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", raw)) < 2:
            continue
        candidate = _parse_text(re.sub(r"\s+\d+[.,]\d{2}\s*[A-Z]?$", "", raw)) or _parse_text(raw)
        if candidate and 1 <= len(candidate.split()) <= 6:
            result["concept"] = _clean_pos_receipt_concept(candidate.strip(" -:|'\""))
            break

    return result


def _clean_pos_receipt_vendor(value: str) -> str:
    raw = " ".join(str(value or "").split()).strip()
    raw = re.sub(r"^[=|:>`'~.,;_\-\s]+", "", raw)
    raw = re.sub(r"[=|:>`'~.,;_\-\s]+$", "", raw)
    return raw.strip()


def _clean_pos_receipt_concept(value: str) -> str:
    raw = " ".join(str(value or "").split()).strip()
    raw = re.sub(r"\s+[><=|:`'~._-]+\s*[A-Za-z]{0,3}$", "", raw)
    raw = re.sub(r"\s+[A-Za-z]{1,2}$", "", raw)
    raw = re.sub(r"^[=|:>`'~.,;_\-\s]+", "", raw)
    raw = re.sub(r"[=|:>`'~.,;_\-\s]+$", "", raw)
    return raw.strip()


def _is_pos_receipt_vendor_noise(value: Any) -> bool:
    raw = " ".join(str(value or "").split()).strip()
    if not raw:
        return True
    norm = _normalize_label(raw)
    return (
        "simplif" in norm
        or norm.startswith("establecimiento")
        or norm.startswith("localidad")
        or "para el cliente" in norm
        or len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", raw)) < 2
    )


def _is_pos_receipt_concept_noise(value: Any) -> bool:
    raw = " ".join(str(value or "").split()).strip()
    if not raw:
        return True
    norm = _normalize_label(raw)
    return (
        ("base" in norm and "cuota" in norm)
        or norm.startswith("imp.")
        or norm.startswith("imp ")
        or "tarjeta" in norm
        or "cambio" in norm
        or "para el cliente" in norm
        or "establecimiento" in norm
        or "localidad" in norm
        or "simplif" in norm
    )


def _extract_ticket_items(lines: list[str]) -> list[dict[str, Any]]:
    if not _looks_like_ticket_document(lines):
        return []

    start_idx = None
    end_idx = len(lines)
    for idx, line in enumerate(lines):
        norm = _normalize_label(line)
        if start_idx is None and ("productos" in norm or "detalle" in norm):
            start_idx = idx + 1
            continue
        if start_idx is not None and any(
            marker in norm for marker in ("subtotal", "total", "pagos")
        ):
            end_idx = idx
            break
    if start_idx is None:
        start_idx = 0

    items: list[dict[str, Any]] = []
    idx = start_idx
    qty_desc_pattern = re.compile(
        r"^\s*(\d+(?:[.,]\d+|[.,][oøØ0]{2,3})?|[lI]\.?(?:[oøØ0]{2,3}))\s*(?:@0?x|0x|[@xX×])\s*(.+?)\s*$"
    )
    amount_pattern = re.compile(r"(?<!\d)(?:-?\d{1,3}(?:[.,]\d{3})+[.,]\d{2}|-?\d+[.,]\d{2})(?!\d)")

    while idx < end_idx:
        line = str(lines[idx] or "").strip()
        if not line:
            idx += 1
            continue
        line_norm = _normalize_label(line)
        if any(marker in line_norm for marker in ("subtotal", "total", "pagos")):
            break
        match = qty_desc_pattern.match(line)
        if match:
            quantity = _parse_loose_number(match.group(1))
            if quantity is None and re.fullmatch(r"[lI]\.?(?:[oøØ0]{2,3})", match.group(1)):
                quantity = 1.0
            description = _parse_text(match.group(2)) or match.group(2).strip()
            same_line_amounts = [
                safe_floatish(m.group(0)) for m in amount_pattern.finditer(description)
            ]
            same_line_amounts = [value for value in same_line_amounts if value is not None]
            amount = float(same_line_amounts[-1]) if same_line_amounts else None
            if amount is not None:
                description = amount_pattern.sub("", description).strip(" $€-:|")
            unit_price = None
            if amount is None:
                look_ahead = idx + 1
                while look_ahead < end_idx and not str(lines[look_ahead] or "").strip():
                    look_ahead += 1
                if look_ahead < end_idx:
                    next_line = str(lines[look_ahead] or "").strip()
                    amounts = [
                        safe_floatish(m.group(0)) for m in amount_pattern.finditer(next_line)
                    ]
                    amounts = [amount_value for amount_value in amounts if amount_value is not None]
                    if amounts:
                        amount = float(amounts[-1])
                        idx = look_ahead
            if amount is not None and quantity not in (None, 0):
                unit_price = amount / float(quantity)
            item = {
                "description": description,
                "concept": description,
                "quantity": round(float(quantity), 2) if quantity is not None else None,
                "unit_price": round(float(unit_price), 2) if unit_price is not None else None,
                "total_price": round(float(amount), 2) if amount is not None else None,
                "amount": round(float(amount), 2) if amount is not None else None,
                "raw_text": line,
            }
            if item["description"]:
                items.append(item)
        idx += 1

    if items:
        return items

    # Fallback: detect standalone amount lines after product names.
    for idx in range(start_idx, end_idx):
        line = str(lines[idx] or "").strip()
        line_norm = _normalize_label(line)
        if not line or any(marker in line_norm for marker in ("subtotal", "total", "pagos")):
            break
        if re.search(r"\d", line) and ("x " in line_norm or "@x" in line_norm or "×" in line_norm):
            desc = _parse_text(re.sub(r"^\s*\d+(?:[.,]\d+)?\s*[@xX×]\s*", "", line)) or line
            next_amount = None
            look_ahead = idx + 1
            while look_ahead < end_idx and not str(lines[look_ahead] or "").strip():
                look_ahead += 1
            if look_ahead < end_idx:
                next_line = str(lines[look_ahead] or "").strip()
                amount_matches = [
                    safe_floatish(m.group(0)) for m in amount_pattern.finditer(next_line)
                ]
                amount_matches = [value for value in amount_matches if value is not None]
                if amount_matches:
                    next_amount = float(amount_matches[-1])
            if desc and next_amount is not None:
                items.append(
                    {
                        "description": desc,
                        "concept": desc,
                        "quantity": None,
                        "unit_price": None,
                        "total_price": round(next_amount, 2),
                        "amount": round(next_amount, 2),
                        "raw_text": line,
                    }
                )

    return items


def _line_items_positive_total(items: list[dict[str, Any]]) -> float | None:
    total = 0.0
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        amount = safe_floatish(item.get("total_price"))
        if amount is None:
            amount = safe_floatish(item.get("amount"))
        if amount is None:
            quantity = safe_floatish(item.get("quantity"))
            unit_price = safe_floatish(item.get("unit_price"))
            if quantity is not None and unit_price is not None:
                amount = float(quantity) * float(unit_price)
        if amount is None or amount <= 0:
            continue
        total += float(amount)
        count += 1
    return round(total, 2) if count else None


def _extract_visual_invoice_items(ocr_text: str) -> list[dict[str, Any]]:
    try:
        from .ai_classifier import _extract_invoice_line_items_from_ocr

        return _extract_invoice_line_items_from_ocr(ocr_text, ocr_runtime={})[:50]
    except Exception:
        return []


def _infer_high_invoice_subtotal(lines: list[str]) -> float | None:
    best: float | None = None
    for line in lines:
        norm = _normalize_label(line)
        if "subtotal" not in norm and "sub total" not in norm:
            continue
        amounts = _find_amounts(line)
        for amount in amounts:
            value = float(amount)
            if value <= 0:
                continue
            if best is None or value > best:
                best = value
    return round(best, 2) if best is not None else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_fields_from_text(
    ocr_text: str,
    canonical_fields: dict[str, dict],
    field_aliases: dict[str, list[str]],
    amount_labels: dict[str, list[str]],
    pdf_config: dict | None = None,
    page_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Extract fields from OCR text using DB-configured labels and types.

    This function is the fallback extraction layer when AI is unavailable.
    All field names, aliases, and parsing behavior come from the database.
    No field names or patterns are hardcoded.

    Args:
        ocr_text:         Raw text from OCR extraction.
        canonical_fields: {field_name: {type, projection_column}} from imp_canonical_field.
        field_aliases:    {field_name: [alias, ...]} from imp_field_alias.
        amount_labels:    {field_name: [label, ...]} from imp_config amount_label_config.
        pdf_config:       Config de parseo de tablas PDF desde load_pdf_table_parse_config(db).
        page_texts:       OCR text split by page when the extractor can preserve it.

    Returns:
        Dict of extracted fields compatible with datos_extraidos.
    """
    if not ocr_text or not ocr_text.strip():
        return {}

    lines = _prepare_lines(ocr_text)
    if not lines:
        return {}

    specs = _build_specs(canonical_fields, field_aliases, amount_labels)
    all_labels = _all_known_labels_norm(specs)

    lines_norm = [_normalize_label(line) for line in lines]

    result: dict[str, Any] = {}

    for field_name, spec in specs.items():
        candidates: list[_Candidate] = []
        for i, (line, line_norm) in enumerate(zip(lines, lines_norm)):
            candidates.extend(_match_same_line(spec, line, line_norm))
            candidates.extend(_match_next_line(spec, lines, lines_norm, i, all_labels))

        best = _best_candidate(candidates, spec["type"])
        if best is not None:
            # Strip residual column-separator artifacts ("  |  ") that the OCR
            # row-reconstruction may leave for fields whose value spans across
            # what the PDF rendered as adjacent columns. This keeps text-typed
            # values (vendor/customer/...) clean even if the text contains
            # narrow column gaps that were preserved as "|" markers.
            if spec["type"] == "text" and isinstance(best, str):
                cleaned = re.sub(r"\s*\|\s*", " ", best)
                cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:;,|")
                if cleaned:
                    best = cleaned
            result[field_name] = best

    # Extract line_items from tabular OCR text
    effective_pages = _effective_page_texts(ocr_text, page_texts)
    line_items, line_item_page_groups = _extract_line_items_by_page_from_text(
        effective_pages,
        field_aliases,
        pdf_config=pdf_config,
    )
    payroll_document = _looks_like_payroll_document(lines)
    ticket_document = _looks_like_ticket_document(lines) and not payroll_document
    bank_document = _looks_like_bank_statement(lines)
    sales_summary_document = _looks_like_sales_summary_export(lines)
    payroll_items = _extract_payroll_items_relaxed(lines) if payroll_document else []
    if payroll_items:
        line_items = payroll_items
    elif ticket_document:
        ticket_items = _extract_ticket_items(lines)
        if ticket_items:
            line_items = ticket_items
    elif bank_document:
        bank_items = _extract_bank_statement_items(lines)
        if bank_items:
            line_items = bank_items
    elif not line_items:
        inline_items = _extract_inline_pipe_table(ocr_text)
        if inline_items:
            line_items = inline_items
        if not line_items:
            line_items = _extract_compact_invoice_items_relaxed(lines)
        if not line_items:
            line_items = _extract_visual_invoice_items(ocr_text)
    if line_items:
        result["line_items"] = line_items
    if line_item_page_groups:
        result["line_item_page_groups"] = line_item_page_groups

    pos_metadata = _extract_pos_receipt_metadata(lines)
    for key, value in pos_metadata.items():
        if key == "vendor":
            current_vendor = result.get("vendor")
            if current_vendor in (None, "", [], {}) or _is_pos_receipt_vendor_noise(current_vendor):
                result["vendor"] = value
            continue
        if key == "concept":
            current_concept = result.get("concept")
            if current_concept in (None, "", [], {}) or _is_pos_receipt_concept_noise(
                current_concept
            ):
                result["concept"] = value
            continue
        result.setdefault(key, value)

    payroll_metadata = _infer_payroll_metadata(lines, payroll_items if payroll_document else [])
    for key, value in payroll_metadata.items():
        if key in {"gross_pay", "deductions_total", "liquido_a_percibir", "total_amount"}:
            result[key] = value
        else:
            result.setdefault(key, value)
    if "total_amount" not in result and "liquido_a_percibir" in result:
        result["total_amount"] = result["liquido_a_percibir"]
    receipt_metadata = _infer_receipt_metadata(lines)
    for key, value in receipt_metadata.items():
        current = result.get(key)
        if current in (None, "", [], {}) or key in {"concept", "issue_date"}:
            result[key] = value
    if any(_normalize_label(line).startswith("nota de venta") for line in lines):
        result["concept"] = "NOTA DE VENTA"
    if ticket_document and line_items:
        ticket_total = 0.0
        for item in line_items:
            amount = safe_floatish(item.get("amount"))
            if amount is None:
                amount = safe_floatish(item.get("total_price"))
            if amount is not None:
                ticket_total += float(amount)
        if ticket_total > 0:
            current_total = safe_floatish(result.get("total_amount"))
            if current_total is None or abs(float(current_total)) < 0.01:
                result["total_amount"] = round(ticket_total, 2)
            if ticket_total >= 3 and any(
                "total" in _normalize_label(line) and (safe_floatish(line) or 0.0) == 0.0
                for line in lines
            ):
                result["total_amount"] = round(ticket_total)

    if "issue_date" not in result and line_items:
        for item in line_items:
            issue_date = item.get("issue_date")
            if issue_date not in (None, "", [], {}):
                result["issue_date"] = issue_date
                break

    # Unified extractors live in field_extractors and combine the AI-classifier
    # logic with the text-line inference. They are imported lazily because
    # field_extractors itself imports back into this module.
    from .field_extractors import extract_issue_date as _unified_extract_issue_date
    from .field_extractors import extract_total_amount as _unified_extract_total_amount
    from .field_extractors import extract_vendor_name as _unified_extract_vendor_name

    if "issue_date" not in result:
        inferred_date = _unified_extract_issue_date(lines=lines)
        if inferred_date is not None:
            result["issue_date"] = inferred_date

    if "total_amount" not in result:
        inferred_total = detect_document_total(
            result,
            aliases=["total_amount", "total_price", "total", "amount"],
        )
        if inferred_total is not None:
            result["total_amount"] = inferred_total
    if "total_amount" not in result:
        inferred_total = _unified_extract_total_amount(lines=lines)
        if inferred_total is not None:
            result["total_amount"] = inferred_total

    if sales_summary_document:
        summary_date = _infer_sales_summary_issue_date(lines)
        if summary_date is not None:
            result["issue_date"] = summary_date
        summary_total = _infer_sales_summary_total(lines)
        if summary_total is not None:
            result["total_amount"] = summary_total
    elif bank_document:
        bank_total = _infer_bank_statement_total(line_items if line_items else [], lines)
        if bank_total is not None:
            result["total_amount"] = bank_total

    if line_items and not (payroll_document or sales_summary_document or bank_document):
        line_items_total = _line_items_positive_total(line_items)
        current_total = safe_floatish(result.get("total_amount"))
        if line_items_total is not None and (
            current_total is None or float(current_total) < line_items_total * 0.2
        ):
            result["total_amount"] = line_items_total
    if not (payroll_document or sales_summary_document or bank_document):
        high_invoice_subtotal = _infer_high_invoice_subtotal(lines)
        current_total = safe_floatish(result.get("total_amount"))
        if high_invoice_subtotal is not None and (
            current_total is None or float(current_total) < high_invoice_subtotal * 0.2
        ):
            result["total_amount"] = high_invoice_subtotal

    if "concept" not in result:
        inferred_concept = _unified_extract_vendor_name(lines=lines)
        if inferred_concept is not None:
            result["concept"] = inferred_concept

    if bank_document and line_items:
        current_concept = _normalize_label(str(result.get("concept") or ""))
        if (
            not current_concept
            or "detalle del movimiento" in current_concept
            or "transferencias emitidas" in current_concept
            or current_concept.strip(" |") == "importe"
        ):
            first_description = str(line_items[0].get("description") or "").strip()
            if first_description:
                result["concept"] = first_description

    if "payment_method" not in result:
        inferred_payment_method = _infer_payment_method_from_lines(lines)
        if inferred_payment_method is not None:
            result["payment_method"] = inferred_payment_method

    if result:
        logged_keys = [key for key in result if key not in {"line_items", "line_item_page_groups"}]
        logger.info(
            "Text fallback extracted %d fields (line_items=%d): %s",
            len(logged_keys),
            len(line_items) if line_items else 0,
            logged_keys,
        )

    return result


def extract_line_items_table_preview_from_text(
    ocr_text: str,
    field_aliases: dict[str, list[str]],
    pdf_config: dict | None = None,
    page_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Return detected line-item table metadata from OCR text.

    This preserves the raw header labels and the canonical field mapping so
    callers can render or prompt the table in the original column order.
    """
    if not ocr_text or not ocr_text.strip():
        return {}

    effective_pages = _effective_page_texts(ocr_text, page_texts)
    line_items, line_item_page_groups = _extract_line_items_by_page_from_text(
        effective_pages,
        field_aliases,
        pdf_config=pdf_config,
    )
    if not line_items:
        line_items = _extract_inline_pipe_table(ocr_text)
        if not line_items:
            return {}
        line_item_page_groups = [
            {
                "source_page": 1,
                "header_index": 0,
                "headers": [],
                "headers_norm": [],
                "line_items": line_items,
            }
        ]

    first_group = next((group for group in line_item_page_groups if group.get("line_items")), None)
    if first_group is None:
        return {}
    header_idx = int(first_group.get("header_index") or 0)
    matched_fields = first_group.get("headers_norm") or []
    column_names = first_group.get("headers") or []

    return {
        "header_index": header_idx,
        "headers": column_names,
        "headers_norm": matched_fields,
        "line_items": line_items,
        "line_item_page_groups": line_item_page_groups,
    }


def _extract_line_items_by_page_from_text(
    page_texts: list[str],
    field_aliases: dict[str, list[str]],
    pdf_config: dict | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract line items page by page so the caller can preserve source-page evidence."""
    flat_items: list[dict[str, Any]] = []
    page_groups: list[dict[str, Any]] = []

    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text or not str(page_text).strip():
            continue

        lines = _prepare_lines(str(page_text))
        if not lines:
            continue

        lines_norm = [_normalize_label(line) for line in lines]
        header_info = _find_table_header(lines_norm, field_aliases)
        if not header_info:
            continue

        header_idx, matched_fields, column_names, _header_lines = header_info
        page_line_items = _extract_line_items_from_text(
            lines,
            lines_norm,
            field_aliases,
            pdf_config=pdf_config,
        )
        if not page_line_items:
            continue

        # Drop items that, once assembled from vertical cells, look like
        # references, totals, payment methods or page footers (URLs in any
        # cell, "See https://...", "Page 1 of 1", etc.).
        page_line_items = [item for item in page_line_items if not _item_looks_non_product(item)]
        if not page_line_items:
            continue

        page_groups.append(
            {
                "source_page": page_number,
                "header_index": header_idx,
                "headers": column_names,
                "headers_norm": matched_fields,
                "line_items": page_line_items,
            }
        )
        flat_items.extend(page_line_items)

    return flat_items, page_groups


# ---------------------------------------------------------------------------
# Line items table extraction
# ---------------------------------------------------------------------------


def _find_table_header(
    lines_norm: list[str],
    field_aliases: dict[str, list[str]],
) -> tuple[int, list[str], list[str], int] | None:
    """Find a table header row by detecting lines with multiple known column aliases.

    Returns (line_index, matched_canonical_fields, raw_column_names, header_line_count)
    or None.  ``header_line_count`` is 1 when the header is a single tabular row and
    equals ``len(raw_column_names)`` when the header is vertical (one word per line).
    """
    # Build reverse map: alias_norm → (canonical_field, priority)
    # Higher priority aliases win when multiple map to the same norm
    reverse: dict[str, str] = {}
    reverse_prio: dict[str, int] = {}
    for canonical, aliases in field_aliases.items():
        for idx, alias in enumerate(aliases):
            norm = _normalize_label(alias)
            if not norm:
                continue
            # Aliases are sorted by priority desc in the DB, so earlier = higher prio
            prio = len(aliases) - idx
            if norm not in reverse or prio > reverse_prio.get(norm, 0):
                reverse[norm] = canonical
                reverse_prio[norm] = prio

    for i, line_norm in enumerate(lines_norm):
        tokens = re.split(r"\s*\|\s*|\s{2,}|\t+", line_norm)
        if len(tokens) < 3:
            tokens = re.split(r"\s*\|\s*|\s+", line_norm)

        matched_fields: list[str] = []
        raw_names: list[str] = []
        for token in tokens:
            token_clean = token.strip().strip("|").strip()
            if not token_clean:
                continue
            canonical = reverse.get(token_clean)
            matched_fields.append(canonical or "")
            raw_names.append(token_clean)

        raw_names, matched_fields = _repair_split_header_tokens(raw_names, matched_fields, reverse)
        known_count = sum(1 for f in matched_fields if f)
        if known_count >= 2 and len(raw_names) >= 3:
            matched_fields = _dedupe_header_fields(
                matched_fields,
                raw_names,
                reverse_prio,
            )
            return i, matched_fields, raw_names, 1

    # Fallback genérico para tablas sin alias de BD: preserva encabezados crudos
    # y asigna claves canónicas solo para columnas obvias como fecha/total/cantidad.
    for i, line_norm in enumerate(lines_norm[:15]):
        tokens = re.split(r"\s*\|\s*|\t+|\s{2,}", line_norm)
        raw_names: list[str] = []
        matched_fields: list[str] = []
        for token in tokens:
            token_clean = token.strip()
            if not token_clean:
                continue
            raw_names.append(token_clean)
            matched_fields.append(_generic_header_to_canonical(token_clean) or "")

        raw_names, matched_fields = _repair_split_header_tokens(raw_names, matched_fields, reverse)
        known_count = sum(1 for f in matched_fields if f)
        if known_count >= 2 and len(raw_names) >= 3:
            return i, matched_fields, raw_names, 1

    # Fallback: try single-word-per-line header blocks
    # Some OCR outputs put each column header on a separate line
    for i, line_norm in enumerate(lines_norm):
        token = line_norm.strip()
        canonical = reverse.get(token)
        if not canonical:
            continue
        start_idx = i
        for j in range(i - 1, max(-1, i - 4), -1):
            prev_token = lines_norm[j].strip()
            if not prev_token:
                break
            if reverse.get(prev_token):
                break
            if len(prev_token.split()) > 2 or re.search(r"\d", prev_token):
                break
            start_idx = j
        # Look ahead for more consecutive header-like lines
        header_fields: list[str] = []
        header_names: list[str] = []
        for j in range(start_idx, min(start_idx + 15, len(lines_norm))):
            next_token = lines_norm[j].strip()
            next_canonical = reverse.get(next_token)
            if next_canonical:
                header_fields.append(next_canonical)
                header_names.append(next_token)
            elif len(next_token.split()) <= 2 and not re.search(r"\d", next_token):
                header_fields.append("")
                header_names.append(next_token)
            else:
                break
        if sum(1 for f in header_fields if f) >= 2 and len(header_fields) >= 3:
            header_fields = _dedupe_header_fields(
                header_fields,
                header_names,
                reverse_prio,
            )
            return start_idx, header_fields, header_names, len(header_names)

    # Generic fallback: same idea, but with common OCR header tokens even when
    # there is no DB alias coverage for the document.
    for i, line_norm in enumerate(lines_norm[:15]):
        token = line_norm.strip()
        if not _looks_like_generic_header_token(token):
            continue
        start_idx = i
        header_fields: list[str] = []
        header_names: list[str] = []
        for j in range(start_idx, min(start_idx + 15, len(lines_norm))):
            next_token = lines_norm[j].strip()
            if _looks_like_generic_header_token(next_token):
                header_fields.append(_generic_header_to_canonical(next_token) or "")
                header_names.append(next_token)
            elif len(next_token.split()) <= 2 and not re.search(r"\d", next_token):
                header_fields.append("")
                header_names.append(next_token)
            else:
                break
        if sum(1 for f in header_fields if f) >= 2 and len(header_fields) >= 3:
            return start_idx, header_fields, header_names, len(header_names)

    return None


def _dedupe_header_fields(
    matched_fields: list[str],
    column_names: list[str],
    reverse_prio: dict[str, int],
) -> list[str]:
    """When multiple columns map to the same canonical, keep the highest-priority one."""
    # Find duplicates
    field_positions: dict[str, list[int]] = {}
    for idx, field in enumerate(matched_fields):
        if field:
            field_positions.setdefault(field, []).append(idx)

    result = list(matched_fields)
    for field, positions in field_positions.items():
        if len(positions) <= 1:
            continue
        # Keep the position with highest alias priority, clear the rest
        best_pos = max(
            positions,
            key=lambda p: reverse_prio.get(column_names[p], 0),
        )
        for p in positions:
            if p != best_pos:
                result[p] = ""
    return result


def _extract_line_items_from_text(
    lines: list[str],
    lines_norm: list[str],
    field_aliases: dict[str, list[str]],
    pdf_config: dict | None = None,
) -> list[dict[str, Any]]:
    """Parse a product table from OCR text using DB field aliases as column identifiers.

    Handles two OCR output layouts:
    - Tabular: one row per line with columns separated by whitespace/tabs
    - Vertical: one cell per line (common with PDF table OCR)

    pdf_config viene de load_pdf_table_parse_config(db) y provee:
      unit_values          — valores de celda que indican unidad (ml, g, kg, ...)
      footer_skip_patterns — regex para saltar pies de página
    """
    cfg = pdf_config or {}
    raw_unit_values: list[str] = cfg.get("unit_values") or []
    unit_values_set: set[str] = {_normalize_label(v) for v in raw_unit_values if v}

    raw_footer_pats: list[str] = cfg.get("footer_skip_patterns") or []
    footer_patterns: list[re.Pattern] = []
    for pat in raw_footer_pats:
        try:
            footer_patterns.append(re.compile(pat, re.I))
        except re.error:
            pass

    header_info = _find_table_header(lines_norm, field_aliases)
    if not header_info:
        return []

    header_idx, matched_fields, column_names, header_line_count = header_info
    num_cols = len(column_names)
    data_start = header_idx + header_line_count  # skip only the actual header lines

    # Detect layout: check if the first data lines look like single values per line
    # (vertical layout) or multi-column rows (tabular layout)
    vertical = _is_vertical_layout(lines, data_start, num_cols)

    if vertical:
        return _parse_vertical_table(
            lines,
            data_start,
            num_cols,
            matched_fields,
            column_names,
            field_aliases,
            unit_values=unit_values_set,
            footer_patterns=footer_patterns,
        )
    return _parse_tabular_table(
        lines, lines_norm, data_start, num_cols, matched_fields, column_names, field_aliases
    )


def _is_vertical_layout(lines: list[str], data_start: int, num_cols: int) -> bool:
    """Detect if data rows are one-cell-per-line (vertical) vs one-row-per-line."""
    if data_start + num_cols > len(lines):
        return False
    # In vertical layout, most data lines are short single values
    single_value_count = 0
    inspected_count = 0
    for i in range(data_start, min(data_start + num_cols * 2, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        inspected_count += 1
        tokens = re.split(r"\s{2,}|\t+", line)
        if len(tokens) <= 1:
            single_value_count += 1
    required_single_value_count = max(2, int(round(num_cols * 0.7)))
    return inspected_count > 0 and single_value_count >= required_single_value_count


def _is_footer_line(line_norm: str, footer_patterns: list[re.Pattern]) -> bool:
    """Detecta líneas de pie de página usando patrones configurados en BD."""
    return any(p.search(line_norm) for p in footer_patterns)


def _is_header_repetition(lines: list[str], i: int, column_norms: list[str]) -> bool:
    """Devuelve True si las próximas len(column_norms) líneas son una repetición del encabezado."""
    if i + len(column_norms) > len(lines):
        return False
    return all(_normalize_label(lines[i + k]) == column_norms[k] for k in range(len(column_norms)))


def _parse_vertical_table(
    lines: list[str],
    data_start: int,
    num_cols: int,
    matched_fields: list[str],
    column_names: list[str],
    field_aliases: dict[str, list[str]],
    *,
    unit_values: set[str] | None = None,
    footer_patterns: list[re.Pattern] | None = None,
) -> list[dict[str, Any]]:
    """Parse table where each cell is on its own line (N lines per row).

    Maneja:
    - Encabezados repetidos entre páginas (PDFs multi-página)
    - Líneas de pie de página (patrones configurados en BD)
    - Celdas de descripción en múltiples líneas (ej: descripción larga dividida)

    unit_values y footer_patterns provienen de load_pdf_table_parse_config(db).
    """
    items: list[dict[str, Any]] = []
    max_items = 200
    column_norms = [_normalize_label(cn) for cn in column_names]
    _unit_values = unit_values if unit_values else _DEFAULT_UNIT_VALUES
    _footer_patterns = footer_patterns or []

    # Índice de la columna de descripción para detectar continuaciones
    desc_col_idx: int | None = None
    for idx, cf in enumerate(matched_fields):
        if cf == "description":
            desc_col_idx = idx
            break

    # Construir lista de líneas limpias: sin blancos, pies de página ni encabezados repetidos.
    # Parar cuando se detecta el inicio de una sección post-tabla (observaciones, firmas, etc.).
    clean: list[str] = []
    i = data_start
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        line_norm = _normalize_label(line)
        if _is_footer_line(line_norm, _footer_patterns) or any(
            p.search(line_norm) for p in _DEFAULT_FOOTER_PATTERNS
        ):
            i += 1
            continue
        if any(p.search(line) for p in _SECTION_END_PATTERNS):
            break  # fin de la tabla de ítems
        if _is_header_repetition(lines, i, column_norms):
            i += len(column_norms)
            continue
        if _is_non_product_row(line):
            i += 1
            continue
        clean.append(line)
        i += 1

    ci = 0
    while ci + num_cols <= len(clean) and len(items) < max_items:
        # Detectar descripción multi-línea: la celda inmediatamente después del
        # slot de descripción debería ser una abreviatura de unidad (ml, g, unit...).
        # Si no lo es (y no contiene dígitos ni $), es continuación de la descripción.
        extra_desc = 0
        if desc_col_idx is not None and ci + num_cols + 1 <= len(clean):
            next_after_desc = clean[ci + desc_col_idx + 1].strip()
            next_norm = _normalize_label(next_after_desc)
            if (
                next_norm not in _unit_values
                and not re.search(r"[\d$]", next_after_desc)
                and len(next_after_desc) > 3
            ):
                extra_desc = 1

        block_size = num_cols + extra_desc
        if ci + block_size > len(clean):
            break

        item: dict[str, Any] = {}
        valid = True
        src_idx = ci
        for j in range(num_cols):
            if j == desc_col_idx and extra_desc:
                # Fusionar línea actual y siguiente como descripción
                cell = (
                    (clean[src_idx].strip() + " " + clean[src_idx + 1].strip()).strip().strip("|")
                )
                src_idx += 2
            else:
                cell = clean[src_idx].strip().strip("|")
                src_idx += 1

            if not cell:
                valid = False
                break
            canonical = matched_fields[j] if j < len(matched_fields) else ""
            col_name = column_names[j] if j < len(column_names) else f"col_{j}"

            if canonical:
                if canonical in item:
                    item.setdefault("extra_columns", {})[col_name] = cell
                else:
                    item[canonical] = cell
            else:
                item.setdefault("extra_columns", {})[col_name] = cell

        # Validar que al menos un campo de precio/cantidad sea parseable como número.
        # Evita incluir bloques de sección (Observaciones, totales) que pasaron el filtro
        # de sección-end pero aún llegaron al bloque de parseo.
        if valid and (
            any(k in field_aliases for k in item) or any(k in _GENERIC_ROW_FIELDS for k in item)
        ):
            _numeric_fields = ("total_price", "quantity", "unit_price")
            _has_numeric = any(
                safe_floatish(item.get(f, "")) is not None for f in _numeric_fields if f in item
            )
            if _has_numeric:
                items.append(item)
        ci += block_size

    return items


def _parse_tabular_table(
    lines: list[str],
    lines_norm: list[str],
    data_start: int,
    num_cols: int,
    matched_fields: list[str],
    column_names: list[str],
    field_aliases: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Parse table where each row is on a single line with whitespace separators."""
    items: list[dict[str, Any]] = []
    header_set = set(column_names)

    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        line_norm = lines_norm[i]

        if _is_label_line(line_norm, header_set):
            continue

        # Skip totals, payment methods, URLs and page footers — they are not
        # product rows even when the header table parser would otherwise
        # accept them as such.
        if _is_non_product_row(line):
            continue

        tokens = re.split(r"\s*\|\s*|\s{2,}|\t+", line)
        if len(tokens) < 2:
            tokens = re.split(r"\s*\|\s*|\s{3,}", line)
        if len(tokens) < 2:
            continue

        item: dict[str, Any] = {}
        # Drop empty tokens produced by adjacent pipe separators so column
        # alignment matches the header positions instead of inheriting the
        # blank slots produced by the splitter.
        tokens = [token for token in tokens if token.strip().strip("|").strip()]
        for j, token in enumerate(tokens):
            token_val = token.strip().strip("|").strip()
            if not token_val:
                continue
            canonical = matched_fields[j] if j < len(matched_fields) else ""
            col_name = column_names[j] if j < len(column_names) else f"col_{j}"

            if canonical:
                if canonical in item:
                    item.setdefault("extra_columns", {})[col_name] = token_val
                else:
                    item[canonical] = token_val
            else:
                item.setdefault("extra_columns", {})[col_name] = token_val

        if any(k in field_aliases for k in item) or any(k in _GENERIC_ROW_FIELDS for k in item):
            items.append(item)

    return items


# ---------------------------------------------------------------------------
# Auto-learning: discover new aliases from OCR labels
# ---------------------------------------------------------------------------


def learn_labels_from_text(
    db: Any,
    ocr_text: str,
    canonical_fields: dict[str, dict],
    field_aliases: dict[str, list[str]],
    amount_labels: dict[str, list[str]],
) -> int:
    """Scan OCR text for label patterns and auto-insert new aliases into imp_field_alias.

    Detects lines like "Condicion de pago: ..." where "condicion de pago" is not
    yet a known alias but fuzzy-matches an existing canonical field's aliases.
    Inserts the new alias so future processing recognizes it automatically.

    All field names come from the database — nothing hardcoded.

    Returns the number of new aliases learned.
    """
    if not ocr_text or not ocr_text.strip():
        return 0

    from .classifier_learning import _is_safe_column_name, _normalize_alias

    lines = _prepare_lines(ocr_text)

    # Build set of all known alias norms
    known_norms: set[str] = set()
    reverse_map: dict[str, str] = {}
    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            norm = _normalize_alias(alias)
            known_norms.add(norm)
            reverse_map[norm] = canonical
    for canonical, labels in amount_labels.items():
        for label in labels:
            norm = _normalize_alias(label)
            known_norms.add(norm)
            reverse_map[norm] = canonical

    # Extract candidate labels from lines with explicit separators
    candidate_labels: list[tuple[str, str]] = []  # (raw_label, raw_value)
    for line in lines:
        # Pattern: "Label: Value" or "Label - Value"
        m = re.match(r"^(.+?)\s*[:：]\s+(.+)$", line.strip())
        if m:
            candidate_labels.append((m.group(1).strip(), m.group(2).strip()))

    if not candidate_labels:
        return 0

    from sqlalchemy import text as sa_text

    learned = 0
    for raw_label, _raw_value in candidate_labels:
        alias_norm = _normalize_alias(raw_label)
        if not alias_norm or len(alias_norm) < 3 or len(alias_norm) > 80:
            continue
        if alias_norm in known_norms:
            continue
        if not _is_safe_column_name(raw_label):
            continue

        # Try to fuzzy-match to an existing canonical field
        matched_canonical = _fuzzy_match_canonical(alias_norm, field_aliases, canonical_fields)
        if not matched_canonical:
            continue

        try:
            db.execute(
                sa_text(
                    "INSERT INTO imp_field_alias "
                    "    (tenant_id, canonical_field, alias, priority, source, "
                    "     confirmed_count, last_seen_at, active) "
                    "VALUES (NULL, :canonical, :alias, 1, 'auto_learned', 1, now(), TRUE) "
                    "ON CONFLICT (canonical_field, alias) WHERE tenant_id IS NULL "
                    "DO UPDATE SET confirmed_count = imp_field_alias.confirmed_count + 1, "
                    "    last_seen_at = now()"
                ),
                {"canonical": matched_canonical, "alias": alias_norm},
            )
            known_norms.add(alias_norm)
            learned += 1
            logger.info("Auto-learned alias: '%s' → %s", alias_norm, matched_canonical)
        except Exception as exc:
            logger.debug("Could not auto-learn alias '%s': %s", alias_norm, exc)

    if learned:
        try:
            db.commit()
        except Exception:
            pass

    return learned


def _fuzzy_match_canonical(
    alias_norm: str,
    field_aliases: dict[str, list[str]],
    canonical_fields: dict[str, dict],
) -> str | None:
    """Try to match an unknown label to a canonical field using token overlap.

    Returns the canonical field name or None.
    """
    from .classifier_learning import _normalize_alias

    alias_tokens = set(alias_norm.split())
    if not alias_tokens:
        return None

    best_field: str | None = None
    best_score = 0.0

    for canonical, aliases in field_aliases.items():
        if canonical not in canonical_fields:
            continue
        for known_alias in aliases:
            known_norm = _normalize_alias(known_alias)
            known_tokens = set(known_norm.split())
            if not known_tokens:
                continue

            # Token overlap score
            overlap = alias_tokens & known_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(alias_tokens), len(known_tokens))
            # Bonus for longer overlap
            score += len(overlap) * 0.1

            if score > best_score:
                best_score = score
                best_field = canonical

    # Require reasonable similarity
    return best_field if best_score >= 0.4 else None
