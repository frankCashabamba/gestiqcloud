"""Universal AI analyzer for any accounting document in any language."""

from __future__ import annotations

import json
import logging
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


async def analyze_document(
    content: str,
    filename: str = "",
    format_hint: str = "",
    has_structured_rows: bool = False,
    recipe_config: dict | None = None,
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
    rc = recipe_config or {}

    system_prompt = rc.get("prompt_system") or (
        "You are a universal accounting document analyzer. "
        "You identify and extract information from ANY type of document regardless of language: "
        "invoices, inventories, payrolls, bank statements, price lists, budgets, "
        "purchase orders, costing sheets, receipts, contracts, etc. "
        "Always respond with valid JSON using the exact output keys specified, regardless of the document language."
    )

    tabular_note = (
        "NOTE: Content is already pre-processed as a structured table. "
        "If you recognize a list or table, set is_table=true and provide clean column names. "
        "Do NOT return individual rows.\n\n"
        if has_structured_rows
        else ""
    )

    content_limit = 4000 if has_structured_rows else 7000

    user_prompt = (
        f"{tabular_note}"
        f"File: {filename} | Format: {format_hint}\n\n"
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
        '    "subtotal": number before tax, or null,\n'
        '    "tax_amount": total tax/VAT/IVA/GST/TVA amount, or null,\n'
        '    "currency": "ISO 4217 code (USD, EUR, GBP, CNY, MXN…) or null",\n'
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
        "- Dates: YYYY-MM-DD. Amounts: number with dot decimal (e.g. 2145.00). Missing fields: null.\n"
        "- Do NOT invent data absent from the document."
    )

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
            fallback = _fallback_classify(content, filename)
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

        fallback = _fallback_classify(content, filename)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback

    except Exception as exc:
        logger.error("AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename)
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
