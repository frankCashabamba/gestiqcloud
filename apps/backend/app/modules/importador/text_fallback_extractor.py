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

from .document_fields import safe_floatish

logger = logging.getLogger("importador.text_fallback")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_label(text: str) -> str:
    """Lowercase + strip accents + collapse whitespace for label matching."""
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(normalized.lower().split())


def _prepare_lines(ocr_text: str) -> list[str]:
    """Split OCR text into clean lines, preserving originals for value extraction."""
    return [line for line in ocr_text.splitlines() if line.strip()]


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
        max_capture = 1 if spec["type"] in ("numeric", "date") else 2
        value_parts: list[str] = []
        for j in range(index + 1, min(index + 1 + max_capture, len(lines))):
            next_norm = lines_norm[j]
            if _is_label_line(next_norm, all_labels):
                break
            value_parts.append(lines[j].strip())
        if not value_parts:
            continue
        raw_value = " ".join(value_parts)
        score = 15 + len(label_norm)
        candidates.append((raw_value, score))
    return candidates


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------


def _parse_value(raw: str, field_type: str) -> Any | None:
    """Parse a raw text candidate according to canonical field type."""
    if field_type == "numeric":
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_fields_from_text(
    ocr_text: str,
    canonical_fields: dict[str, dict],
    field_aliases: dict[str, list[str]],
    amount_labels: dict[str, list[str]],
    pdf_config: dict | None = None,
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
            result[field_name] = best

    # Extract line_items from tabular OCR text
    line_items = _extract_line_items_from_text(
        lines, lines_norm, field_aliases, pdf_config=pdf_config
    )
    if line_items:
        result["line_items"] = line_items

    if result:
        logger.info(
            "Text fallback extracted %d fields (line_items=%d): %s",
            len(result),
            len(line_items) if line_items else 0,
            [k for k in result if k != "line_items"],
        )

    return result


# ---------------------------------------------------------------------------
# Line items table extraction
# ---------------------------------------------------------------------------


def _find_table_header(
    lines_norm: list[str],
    field_aliases: dict[str, list[str]],
) -> tuple[int, list[str], list[str]] | None:
    """Find a table header row by detecting lines with multiple known column aliases.

    Returns (line_index, matched_canonical_fields, raw_column_names) or None.
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
        tokens = re.split(r"\s{2,}|\t+", line_norm)
        if len(tokens) < 3:
            continue

        matched_fields: list[str] = []
        raw_names: list[str] = []
        for token in tokens:
            token_clean = token.strip()
            if not token_clean:
                continue
            canonical = reverse.get(token_clean)
            matched_fields.append(canonical or "")
            raw_names.append(token_clean)

        known_count = sum(1 for f in matched_fields if f)
        if known_count >= 2 and len(raw_names) >= 3:
            matched_fields = _dedupe_header_fields(
                matched_fields,
                raw_names,
                reverse_prio,
            )
            return i, matched_fields, raw_names

    # Fallback: try single-word-per-line header blocks
    # Some OCR outputs put each column header on a separate line
    for i, line_norm in enumerate(lines_norm):
        token = line_norm.strip()
        canonical = reverse.get(token)
        if not canonical:
            continue
        # Look ahead for more consecutive header-like lines
        header_fields: list[str] = [canonical]
        header_names: list[str] = [token]
        for j in range(i + 1, min(i + 15, len(lines_norm))):
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
            return i, header_fields, header_names

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

    header_idx, matched_fields, column_names = header_info
    num_cols = len(column_names)
    data_start = header_idx + num_cols  # skip header lines

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
        lines, lines_norm, header_idx + 1, num_cols, matched_fields, column_names, field_aliases
    )


def _is_vertical_layout(lines: list[str], data_start: int, num_cols: int) -> bool:
    """Detect if data rows are one-cell-per-line (vertical) vs one-row-per-line."""
    if data_start + num_cols > len(lines):
        return False
    # In vertical layout, most data lines are short single values
    single_value_count = 0
    for i in range(data_start, min(data_start + num_cols * 2, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        tokens = re.split(r"\s{2,}|\t+", line)
        if len(tokens) <= 1:
            single_value_count += 1
    return single_value_count >= num_cols


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
    _unit_values = unit_values or set()
    _footer_patterns = footer_patterns or []

    # Índice de la columna de descripción para detectar continuaciones
    desc_col_idx: int | None = None
    for idx, cf in enumerate(matched_fields):
        if cf == "description":
            desc_col_idx = idx
            break

    # Construir lista de líneas limpias: sin blancos, pies de página ni encabezados repetidos
    clean: list[str] = []
    i = data_start
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        line_norm = _normalize_label(line)
        if _is_footer_line(line_norm, _footer_patterns):
            i += 1
            continue
        if _is_header_repetition(lines, i, column_norms):
            i += len(column_norms)
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
                cell = (clean[src_idx].strip() + " " + clean[src_idx + 1].strip()).strip()
                src_idx += 2
            else:
                cell = clean[src_idx].strip()
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

        if valid and any(k in field_aliases for k in item):
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

        tokens = re.split(r"\s{2,}|\t+", line)
        if len(tokens) < 2:
            tokens = re.split(r"\s{3,}", line)
        if len(tokens) < 2:
            continue

        item: dict[str, Any] = {}
        for j, token in enumerate(tokens):
            token_val = token.strip()
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

        if any(k in field_aliases for k in item):
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
