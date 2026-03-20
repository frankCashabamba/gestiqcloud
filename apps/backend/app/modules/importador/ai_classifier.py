"""Universal AI analyzer for any accounting document in any language."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
from typing import Any

from app.services.ai.base import AITask
from app.services.ai.service import AIService

logger = logging.getLogger("importador.ai")

CONFIDENCE_THRESHOLD = 0.85

# Minimal emergency patterns — used ONLY when both AI and DB are unavailable.
# Extend document types via DB migration (sector_field_defaults), not here.
_EMERGENCY_PATTERNS: dict[str, list[str]] = {
    "INVOICE": ["invoice", "factura", "rechnung", "fattura", "fatura", "facture"],
    "RECEIPT": ["receipt", "recibo", "reçu", "quittung", "boleta", "ticket"],
    "BANK_STATEMENT": [
        "bank statement",
        "extracto",
        "kontoauszug",
        "état de compte",
        "estado de cuenta",
    ],
    "PAYROLL": ["payroll", "nomina", "planilla", "lohnabrechnung"],
    "INVENTORY": ["inventory", "inventario", "stock", "bestandsliste"],
    "COSTING": ["costing", "costeo", "kalkulation", "receta"],
}


def _ocr_quality_threshold() -> float:
    raw = (os.getenv("IMPORTADOR_OCR_MIN_QUALITY") or "").strip()
    if not raw:
        return 0.45
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.45


def _estimate_text_quality(text: str) -> dict[str, float]:
    """Estimate whether OCR text is good enough to avoid a vision pass."""
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
        if not (ch.isalnum() or ch.isspace() or ch in ".,;:/-_#%()[]{}+*'\"@")
    )

    alpha_ratio = alpha_chars / max(alnum_chars, 1)
    weird_ratio = weird_chars / max(chars, 1)
    length_score = min(chars / 1200.0, 1.0)
    word_score = min(word_count / 180.0, 1.0)
    alpha_score = min(alpha_ratio / 0.6, 1.0)
    noise_penalty = min(weird_ratio / 0.2, 1.0)

    score = (
        (length_score * 0.35)
        + (word_score * 0.35)
        + (alpha_score * 0.2)
        + ((1 - noise_penalty) * 0.1)
    )
    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "chars": float(chars),
        "words": float(word_count),
        "alpha_ratio": round(alpha_ratio, 3),
        "weird_ratio": round(weird_ratio, 3),
    }


def _should_use_vision_fallback(
    content: str,
    format_hint: str,
    image_bytes: bytes | None,
) -> bool:
    """Use vision only when OCR text is too weak and we have an image payload."""
    if not image_bytes:
        return False

    normalized_format = str(format_hint or "").strip().upper()
    if normalized_format not in {"IMAGE_OCR", "PDF_OCR", "JPG", "PNG", "IMG", "PDF"}:
        return False

    quality = _estimate_text_quality(content)
    score = quality["score"]
    min_quality = _ocr_quality_threshold()
    needs_vision = score < min_quality or quality["words"] < 18

    logger.info(
        "OCR quality for %s: score=%.3f words=%s chars=%s threshold=%.2f vision=%s",
        normalized_format or "UNKNOWN",
        score,
        int(quality["words"]),
        int(quality["chars"]),
        min_quality,
        "yes" if needs_vision else "no",
    )
    return needs_vision


def _build_structured_classification_prompt(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None,
) -> str:
    rc = recipe_config or {}
    system_prefix = str(rc.get("prompt_system") or "").strip()
    current_year = datetime.datetime.now().year

    prompt = (
        "Classify this structured accounting dataset.\n"
        "The content contains column headers and a few sample rows, not the full file.\n"
        "Return ONLY valid JSON with keys: doc_type, confidence, reasoning.\n"
        f"File: {filename} | Format: {format_hint}\n"
        f"Current year: {current_year}\n\n"
        f"Structured preview:\n{content[:2500]}\n\n"
        "Use concise uppercase labels such as INVOICE, RECEIPT, CREDIT_NOTE, "
        "BANK_STATEMENT, BANK_MOVEMENTS, INVENTORY, PRICE_LIST, COSTING, PAYROLL, OTHER."
    )

    if system_prefix:
        prompt = system_prefix + "\n\n" + prompt
    return prompt


def _build_dynamic_fields_prompt(
    canonical_fields: dict[str, dict] | None,
    field_descriptions: dict[str, str] | None = None,
) -> str:
    descriptions = field_descriptions or {}
    if not canonical_fields:
        return (
            '    "vendor": "issuing/selling party name or null",\n'
            '    "vendor_tax_id": "tax ID of the issuer or null",\n'
            '    "customer": "receiving/buying party name or null",\n'
            '    "customer_tax_id": "tax ID of the buyer or null",\n'
            '    "doc_number": "document reference number or null",\n'
            '    "issue_date": "YYYY-MM-DD or null",\n'
            '    "total_amount": NUMBER or null,\n'
            '    "subtotal": NUMBER or null,\n'
            '    "tax_amount": NUMBER or null,\n'
            '    "currency": "ISO 4217 code or null",\n'
            '    "payment_method": "payment method exactly as printed or null",\n'
            '    "payment_terms": "payment terms exactly as printed or null",\n'
            '    "line_items": [{"description":"...","quantity":number,"unit_price":number,"total_price":number}] or []'
        )

    lines: list[str] = []
    for field_name in sorted(canonical_fields.keys()):
        meta = canonical_fields.get(field_name) or {}
        field_type = str(meta.get("type") or "text").strip().lower()
        custom_description = str(descriptions.get(field_name) or "").strip()
        if custom_description:
            rendered = f'"{custom_description}"'
        elif field_name == "line_items" or field_type == "list":
            rendered = '[{"description":"...","quantity":number,"unit_price":number,"total_price":number}] or []'
        elif field_type == "numeric":
            rendered = "NUMBER or null"
        elif field_type == "date":
            rendered = '"YYYY-MM-DD or null"'
        elif field_type == "payment_method":
            rendered = '"payment method exactly as printed or null"'
        else:
            rendered = '"text/value as printed or null"'
        lines.append(f'    "{field_name}": {rendered}')
    return ",\n".join(lines)


async def _analyze_structured_document(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Cheap classification path for already structured datasets."""
    prompt = _build_structured_classification_prompt(content, filename, format_hint, recipe_config)

    try:
        response = await AIService.query(
            task=AITask.CLASSIFICATION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=220,
            module="importador",
            enable_recovery=True,
        )
        raw_content = response.content
        model_used = response.model or "unknown"

        if response.is_error:
            fallback = _fallback_classify(content, filename, fallback_patterns)
            fallback.update({"is_table": True, "columns": [], "fields": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = prompt[:500]
            return fallback

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            parsed.setdefault("confidence", 0.7)
            parsed.setdefault("reasoning", "")
            parsed["is_table"] = True
            parsed["columns"] = []
            parsed["fields"] = {}
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = prompt[:500]
            return parsed

        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": True, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = prompt[:500]
        return fallback
    except Exception as exc:
        logger.error("Structured AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": True, "columns": [], "fields": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = prompt[:500]
        return fallback


def _clean_vision_fields(fields: dict) -> None:
    """Post-process vision model output to fix common mistakes in-place."""
    for key in ("total_amount", "subtotal", "tax_amount"):
        val = fields.get(key)
        if isinstance(val, str):
            cleaned = val.replace(",", "").replace(" ", "").strip()
            try:
                fields[key] = float(cleaned)
            except (ValueError, TypeError):
                pass

    for key in ("vendor_tax_id", "customer_tax_id"):
        val = fields.get(key)
        if isinstance(val, str):
            fields[key] = re.sub(r"[^0-9]", "", val) or None

    date_val = fields.get("issue_date")
    if isinstance(date_val, str):
        if "T" in date_val:
            date_val = date_val.split("T")[0]
        date_val = date_val.strip()[:10]
        fields["issue_date"] = date_val if re.match(r"^\d{4}-\d{2}-\d{2}$", date_val) else date_val

    items = fields.get("line_items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            for k in ("quantity", "unit_price", "total_price"):
                v = item.get(k)
                if isinstance(v, str):
                    try:
                        item[k] = float(v.replace(",", "").strip())
                    except (ValueError, TypeError):
                        pass

    for key in ("payment_method", "payment_terms"):
        val = fields.get(key)
        if isinstance(val, str):
            cleaned = re.sub(
                r"^(payment\s*(method|type|terms?)|metodo\s+de\s+pago|forma\s+de\s+pago|tipo\s+de\s+pago)\s*[:\-]\s*",
                "",
                val.strip(),
                flags=re.IGNORECASE,
            )
            fields[key] = cleaned or val.strip()


def _build_additional_field_hints(recipe_config: dict | None) -> str:
    rc = recipe_config or {}
    field_descriptions = rc.get("field_descriptions") or {}
    if not isinstance(field_descriptions, dict):
        return ""

    lines: list[str] = []
    for raw_key, raw_value in field_descriptions.items():
        key = str(raw_key or "").strip()
        value = str(raw_value or "").strip()
        if not key or not value or key in {"subtotal", "tax_amount"}:
            continue
        lines.append(f'- "{key}": {value}')

    if not lines:
        return ""
    return "Learned hints from previously confirmed similar documents:\n" + "\n".join(lines)


def _resize_image_for_vision(image_bytes: bytes, max_dim: int = 1024) -> bytes:
    """Resize image so its longest side is at most max_dim pixels.

    Vision models don't need full-resolution photos — 1024px is sufficient
    to read invoice/receipt text. Keeping this small reduces base64 payload
    and inference time in Ollama, avoiding ReadTimeout on large WhatsApp images.
    """
    import io as _io

    from PIL import Image as _Image

    img = _Image.open(_io.BytesIO(image_bytes))
    w, h = img.size

    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, _Image.LANCZOS)
    else:
        new_size = (w, h)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = _io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    result = buf.getvalue()
    logger.debug(
        "Vision image %dx%d→%dx%d (%d→%d bytes)",
        w,
        h,
        new_size[0],
        new_size[1],
        len(image_bytes),
        len(result),
    )
    return result


async def _analyze_with_vision(
    image_bytes: bytes,
    filename: str,
    format_hint: str,
    recipe_config: dict | None = None,
) -> dict[str, Any] | None:
    """Try to analyze a document image using a vision-capable model via Ollama.

    Returns None if no vision model is available, letting the caller fall back
    to the text-based OCR path.
    """
    import base64
    import os

    import httpx

    ollama_url = (
        os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434"
    ).rstrip("/")
    vision_model = os.getenv("OLLAMA_VISION_MODEL", "minicpm-v")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            tags_resp = await client.get(f"{ollama_url}/api/tags")
            if tags_resp.status_code != 200:
                return None
            available = [m["name"].split(":")[0] for m in tags_resp.json().get("models", [])]
            if vision_model.split(":")[0] not in available:
                logger.info("Vision model '%s' not available, falling back to OCR", vision_model)
                return None
    except Exception:
        return None

    rc = recipe_config or {}
    system_prompt = rc.get("prompt_system") or (
        "You are a universal accounting document analyzer with vision capabilities. "
        "You can read documents in ANY language. Extract all visible information accurately."
    )

    _fd = rc.get("field_descriptions") or {}
    _f_subtotal = _fd.get("subtotal") or "taxable base before tax. Number or null"
    _f_tax = _fd.get("tax_amount") or "total tax (VAT/IVA/IGV/GST). Number or null if absent"
    learned_hints = _build_additional_field_hints(recipe_config)

    current_year = datetime.datetime.now().year

    user_prompt = (
        f"File: {filename} | Format: {format_hint}\n"
        f"CONTEXT: Current year is {current_year}. Most documents are from {current_year - 1}-{current_year}.\n\n"
        "Read this document image VERY carefully, character by character. "
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "doc_type": "INVOICE, RECEIPT, TICKET, CREDIT_NOTE, PURCHASE_ORDER, QUOTE, '
        "DELIVERY_NOTE, INVENTORY, PRICE_LIST, COSTING, PAYROLL, BANK_STATEMENT, "
        'BANK_MOVEMENTS, or any descriptive label",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "reasoning": "brief explanation",\n'
        '  "is_table": false,\n'
        '  "columns": [],\n'
        '  "fields": {\n'
        '    "vendor": "issuing/selling party company name",\n'
        '    "vendor_tax_id": "RUC/NIT/CIF/tax ID of the ISSUER — digits only, no slashes",\n'
        '    "customer": "receiving/buying party FULL name as printed",\n'
        '    "customer_tax_id": "RUC/CI/tax ID of the BUYER — digits only, no slashes",\n'
        '    "doc_number": "full document/invoice number including series (e.g. 001-001-000120085)",\n'
        '    "issue_date": "YYYY-MM-DD — read the YEAR very carefully (20XX not 201X)",\n'
        '    "total_amount": 2145.00,\n'
        f'    "subtotal": {_f_subtotal},\n'
        f'    "tax_amount": {_f_tax},\n'
        '    "currency": "ISO 4217 — Ecuador=USD, Peru=PEN, Chile=CLP, Colombia=COP, Spain=EUR",\n'
        '    "payment_method": "cash, transfer, card, credit, cheque, etc. as printed on the document, or null",\n'
        '    "payment_terms": "payment condition/terms if visible (e.g. contado, credito 30 dias), or null",\n'
        '    "line_items": [\n'
        '      {"description": "product name only", "quantity": 50.00, "unit_price": 42.90, "total_price": 2145.00}\n'
        "    ]\n"
        "  }\n"
        "}\n"
        "CRITICAL RULES:\n"
        '- ALL amounts MUST be plain numbers with dot decimal (2145.00 NOT "2,145.00").\n'
        "- Dates MUST be YYYY-MM-DD only (no time, no timezone). Read the year VERY carefully.\n"
        f"- YEAR: We are in {current_year}. If you read '16' as year, it is almost certainly '26' (20{current_year % 100}). Double-check!\n"
        "- doc_number: use the FULL number with series/sequence as printed.\n"
        "- customer: read the ACTUAL customer name, not the field label.\n"
        "- payment_method/payment_terms: extract them when the document shows them.\n"
        "- line_items: only list actual PRODUCTS, not the customer name.\n"
        "- Tax IDs: digits only, no slashes or special characters.\n"
        "- Do NOT invent data absent from the document. Use null for missing fields."
    )

    custom_user = rc.get("prompt_user")
    if custom_user:
        user_prompt += f"\n\nAdditional instructions:\n{custom_user}"
    if learned_hints:
        user_prompt += f"\n\n{learned_hints}"

    img_b64 = base64.b64encode(_resize_image_for_vision(image_bytes)).decode("utf-8")

    payload = {
        "model": vision_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
                "images": [img_b64],
            },
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 600},
    }

    try:
        timeout_secs = float(os.getenv("OLLAMA_TIMEOUT", "300"))
        timeout = httpx.Timeout(timeout_secs, read=timeout_secs)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        raw_content = (data.get("message") or {}).get("content", "")
        model_used = data.get("model") or vision_model

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            # Images are never tabular structured data — force is_table=False
            # so fields are stored as invoice/receipt fields, not as row data.
            parsed["is_table"] = False
            parsed["columns"] = []
            parsed.setdefault("fields", {})
            parsed.setdefault("confidence", 0.8)
            parsed.setdefault("reasoning", "Vision model analysis")
            _clean_vision_fields(parsed.get("fields") or {})
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = (system_prompt + "\n\n" + user_prompt)[:500]
            logger.info("Vision analysis succeeded with %s for %s", model_used, filename)
            return parsed

        logger.warning("Vision model returned unparseable response for %s", filename)
        return None

    except Exception as exc:
        logger.warning("Vision analysis failed for %s: %s", filename, exc, exc_info=True)
        return None


async def analyze_document(
    content: str,
    filename: str = "",
    format_hint: str = "",
    has_structured_rows: bool = False,
    recipe_config: dict | None = None,
    image_bytes: bytes | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
    canonical_fields: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Analyzes any accounting document with a single LLM call.

    Works with documents in ANY language (Spanish, English, German, French, etc.).
    The AI reads whatever is in the document and maps it to standard neutral output keys.

    For Excel/CSV with pre-parsed rows (has_structured_rows=True):
      - Receives headers + sample rows
      - LLM classifies the type and confirms column names
      - Actual rows come from the parser (structured_data), not the LLM

    For PDF/image/XML/TXT (has_structured_rows=False):
      - Receives text extracted by OCR
      - LLM classifies + extracts all fields

    Returns: {
        "doc_type": str,
        "confidence": float,
        "reasoning": str,
        "is_table": bool,
        "columns": list[str],   # if is_table=True
        "fields": dict,         # if is_table=False
        "raw_response": str,
        "model_used": str,
        "prompt_sent": str,
    }
    """
    if has_structured_rows:
        return await _analyze_structured_document(
            content,
            filename,
            format_hint,
            recipe_config,
            fallback_patterns=fallback_patterns,
        )

    if not has_structured_rows and _should_use_vision_fallback(content, format_hint, image_bytes):
        vision_result = await _analyze_with_vision(
            image_bytes, filename, format_hint, recipe_config
        )
        if vision_result:
            return vision_result

    rc = recipe_config or {}

    system_prompt = rc.get("prompt_system") or (
        "You are a universal accounting document analyzer. "
        "You identify and extract information from ANY type of document regardless of language: "
        "invoices, inventories, payrolls, bank statements, price lists, budgets, "
        "purchase orders, costing sheets, receipts, contracts, etc. "
        "Always respond with valid JSON using the exact output keys specified, regardless of the document language."
    )

    # Field descriptions can be customized per tenant via recipe_config["field_descriptions"].
    # Defaults are intentionally generic — locale-specific hints belong in the DB config.
    _fd = rc.get("field_descriptions") or {}
    _f_subtotal = _fd.get("subtotal") or (
        "taxable base amount before tax (subtotal, net, base imponible, or similar). Number or null"
    )
    _f_tax = _fd.get("tax_amount") or (
        "total tax amount (VAT/IVA/IGV/GST/TVA or equivalent). Use 0 if present but zero. Number or null if absent"
    )
    learned_hints = _build_additional_field_hints(recipe_config)
    dynamic_fields_prompt = _build_dynamic_fields_prompt(
        canonical_fields,
        {
            **_fd,
            "subtotal": _f_subtotal,
            "tax_amount": _f_tax,
        },
    )

    tabular_note = (
        "NOTE: Content is already pre-processed as a structured table. "
        "If you recognize a list or table, set is_table=true and provide clean column names. "
        "Do NOT return individual rows.\n\n"
        if has_structured_rows
        else ""
    )

    content_limit = 4000 if has_structured_rows else 7000

    current_year = datetime.datetime.now().year

    user_prompt = (
        f"{tabular_note}"
        f"File: {filename} | Format: {format_hint}\n"
        f"CONTEXT: Current year is {current_year}. Most documents are from {current_year - 1}-{current_year}.\n\n"
        f"Content:\n{content[:content_limit]}\n\n"
        "Analyze the document and respond ONLY with valid JSON:\n"
        "{\n"
        '  "doc_type": "A short uppercase label describing the document type in English. '
        "Use standard terms when they clearly apply (e.g. INVOICE, RECEIPT, TICKET, CREDIT_NOTE, "
        "PURCHASE_ORDER, QUOTE, DELIVERY_NOTE, INVENTORY, PRICE_LIST, COSTING, PAYROLL, "
        "BANK_STATEMENT, BANK_MOVEMENTS) or any descriptive label that fits (e.g. EXPENSE_REPORT, "
        'CONTRACT, PROFORMA, CUSTOMS_DECLARATION). Use OTHER only if truly unclassifiable.",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "reasoning": "brief explanation of classification",\n'
        '  "is_table": true or false,\n'
        '  "columns": ["col1", "col2"],\n'
        '  "fields": {\n'
        '    "vendor": "issuing/selling party name — regardless of document language",\n'
        '    "vendor_tax_id": "tax ID / VAT / RUC / SIRET / USt-IdNr of the issuer, or null",\n'
        '    "customer": "receiving/buying party name, or null",\n'
        '    "customer_tax_id": "tax ID of the buyer, or null",\n'
        '    "doc_number": "document reference number, or null",\n'
        '    "issue_date": "YYYY-MM-DD or null",\n'
        '    "total_amount": NUMBER — the GRAND TOTAL at the END of the document (not a product quantity),\n'
        f'    "subtotal": {_f_subtotal},\n'
        f'    "tax_amount": {_f_tax},\n'
        '    "currency": "ISO 4217 code (USD, EUR, GBP, CNY, MXN…) or null",\n'
        '    "payment_method": "payment method/type exactly as printed (cash, transfer, card, credit, cheque, etc.) or null",\n'
        '    "payment_terms": "payment condition/terms if visible (contado, credito, net 30, etc.) or null",\n'
        '    "line_items": [\n'
        '      {"description": "...", "quantity": number, "unit_price": number, "total_price": number}\n'
        "    ]\n"
        "  }\n"
        "}\n"
        "CRITICAL rules:\n"
        "- The document may be in ANY language (Spanish, French, Chinese, Arabic, German…). "
        "  Read whatever is there and map to the output keys above — do NOT require English input.\n"
        "- total_amount = GRAND TOTAL at the bottom (not a quantity of items).\n"
        "- vendor = the entity that ISSUES/SIGNS the document.\n"
        "- If is_table=true: only fill 'columns'; in 'fields' include issue_date and total_amount if visible.\n"
        "- payment_method/payment_terms: extract them when visible instead of omitting them.\n"
        "- Dates: YYYY-MM-DD. Amounts: number with dot decimal (e.g. 2145.00). Missing fields: null.\n"
        f"- YEAR: We are in {current_year}. If you read '16' as year, it is almost certainly '26' (20{current_year % 100}). Double-check!\n"
        "- Do NOT invent data absent from the document."
    )

    custom_user_prompt = rc.get("prompt_user")
    if custom_user_prompt:
        user_prompt += f"\n\nAdditional extraction instructions:\n{custom_user_prompt}"
    if canonical_fields:
        user_prompt += (
            "\n\nConfigured canonical fields from database (prefer these keys and types):\n"
            + dynamic_fields_prompt
        )
    if learned_hints:
        user_prompt += f"\n\n{learned_hints}"

    full_prompt = system_prompt.rstrip() + "\n\n" + user_prompt

    try:
        response = await AIService.query(
            task=AITask.EXTRACTION,
            prompt=full_prompt,
            temperature=0.1,
            max_tokens=1500,
            module="importador",
            enable_recovery=True,
        )

        raw_content = response.content
        model_used = response.model or "unknown"

        if response.is_error:
            logger.warning("AI analysis failed: %s", response.error)
            fallback = _fallback_classify(content, filename, fallback_patterns)
            fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = full_prompt[:500]
            return fallback

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            parsed.setdefault("is_table", False)
            parsed.setdefault("columns", [])
            parsed.setdefault("fields", {})
            parsed.setdefault("confidence", 0.7)
            parsed.setdefault("reasoning", "")
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = full_prompt[:500]
            return parsed

        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback

    except Exception as exc:
        logger.error("AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback


def _fallback_classify(
    text: str,
    filename: str,
    extra_patterns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Rule-based classification used only when the AI service is unavailable.

    Uses _EMERGENCY_PATTERNS (universal cross-language terms) plus any
    tenant-specific patterns passed via extra_patterns.
    """
    text_lower = text.lower()
    fn_lower = filename.lower()

    patterns = {**_EMERGENCY_PATTERNS, **(extra_patterns or {})}

    best_type = "OTHER"
    best_score = 0.0
    for doc_type, keywords in patterns.items():
        matches = sum(1 for kw in keywords if kw in text_lower or kw in fn_lower)
        if matches > best_score:
            best_score = matches
            best_type = doc_type

    confidence = min(0.7, 0.3 + (best_score * 0.2)) if best_score > 0 else 0.2
    return {
        "doc_type": best_type,
        "confidence": confidence,
        "reasoning": f"Rule-based fallback (AI unavailable). Matches: {int(best_score)}",
    }


def _parse_json_response(content: str) -> dict | None:
    """Parses JSON from LLM response, handling markdown code blocks."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
    return None
