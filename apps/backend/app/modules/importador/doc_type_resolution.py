from __future__ import annotations

from typing import Any

from .document_fields import detect_document_total, get_data_value


def should_preserve_strong_preclassification(
    *,
    pre_class_doc_type: str | None,
    pre_class_confidence: float | None,
    product_like_doc_types: set[str],
    min_confidence: float,
) -> bool:
    pre_class_upper = str(pre_class_doc_type or "").strip().upper()
    if not pre_class_upper:
        return False
    try:
        confidence = float(pre_class_confidence or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return confidence >= min_confidence and pre_class_upper not in product_like_doc_types


def _confidence_from_map(
    mapping: dict[str, float],
    doc_type: str,
    default: float = 0.0,
) -> float:
    try:
        return float(mapping.get(str(doc_type or "").strip().upper(), default))
    except (TypeError, ValueError):
        return default


def _keyword_tokens(
    fallback_patterns: dict[str, list[str]] | None,
    doc_type: str,
) -> tuple[str, ...]:
    values = (fallback_patterns or {}).get(str(doc_type or "").strip().upper()) or []
    return tuple(str(item).strip().lower() for item in values if str(item).strip())


def promote_doc_type_from_text_fallback(
    *,
    current_doc_type: str,
    current_confidence: float,
    current_reasoning: str,
    fields: dict[str, Any] | None,
    content: str,
    filename: str,
    pre_class_doc_type: str | None = None,
    resolution_config: dict[str, Any] | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
) -> tuple[str, float, str, str | None]:
    if str(current_doc_type or "").strip().upper() != "OTHER":
        return current_doc_type, current_confidence, current_reasoning, None
    if not isinstance(fields, dict) or not fields:
        return current_doc_type, current_confidence, current_reasoning, None

    cfg = dict(resolution_config or {})
    pre_class_upper = str(pre_class_doc_type or "").strip().upper()
    blocked_preclass_types = {
        str(item).strip().upper()
        for item in (cfg.get("promotion_blocked_preclass_types") or [])
        if str(item).strip()
    }
    if pre_class_upper in blocked_preclass_types:
        return current_doc_type, current_confidence, current_reasoning, None

    text_context = f"{filename}\n{content}".lower()
    total_aliases = [
        str(item).strip()
        for item in (cfg.get("text_fallback_total_field_aliases") or [])
        if str(item).strip()
    ] or ["total_amount", "total_price", "total", "amount"]
    has_issue_date = bool(get_data_value(fields, "issue_date"))
    has_total = detect_document_total(fields, aliases=total_aliases) is not None
    has_vendor = bool(get_data_value(fields, "vendor", "vendor_tax_id"))
    has_vendor_tax_id = bool(get_data_value(fields, "vendor_tax_id"))
    has_customer = bool(get_data_value(fields, "customer", "customer_tax_id"))
    has_doc_number = bool(get_data_value(fields, "doc_number", "supplier_ref"))
    has_concept = bool(get_data_value(fields, "concept", "description"))
    has_payment_method = bool(get_data_value(fields, "payment_method"))
    has_gross_pay = bool(get_data_value(fields, "gross_pay"))
    has_deductions_total = bool(get_data_value(fields, "deductions_total"))
    has_net_pay = bool(get_data_value(fields, "liquido_a_percibir"))
    raw_line_items = fields.get("line_items")
    has_line_items = isinstance(raw_line_items, list) and any(
        isinstance(item, dict) for item in raw_line_items
    )
    has_payroll_evidence = has_line_items and (has_gross_pay or has_deductions_total or has_net_pay)
    invoice_support = sum(
        1 for flag in (has_issue_date, has_total, has_vendor, has_doc_number) if flag
    )
    receipt_support = sum(
        1
        for flag in (
            has_issue_date,
            has_total,
            has_vendor,
            has_customer,
            has_concept,
            has_payment_method,
        )
        if flag
    )

    keyword_confidence = {
        str(key).strip().upper(): float(value)
        for key, value in (cfg.get("text_fallback_keyword_confidence") or {}).items()
        if str(key).strip()
    }
    like_confidence = {
        str(key).strip().upper(): float(value)
        for key, value in (cfg.get("text_fallback_like_confidence") or {}).items()
        if str(key).strip()
    }
    minimal_confidence = {
        str(key).strip().upper(): float(value)
        for key, value in (cfg.get("text_fallback_minimal_confidence") or {}).items()
        if str(key).strip()
    }

    promoted_type: str | None = None
    promoted_confidence: float | None = None
    reason_tag: str | None = None

    invoice_tokens = _keyword_tokens(fallback_patterns, "INVOICE")
    receipt_tokens = _keyword_tokens(fallback_patterns, "RECEIPT")
    payroll_tokens = _keyword_tokens(fallback_patterns, "PAYROLL")
    sales_tokens = _keyword_tokens(fallback_patterns, "SALES")

    # "Factura simplificada" / "nota de venta" son recibos de punto de venta (POS), NO
    # facturas B2B. Tienen prioridad sobre el check genérico de invoice_tokens para que
    # "factura" dentro de "factura simplificada" no dispare INVOICE incorrectamente.
    _simplified_receipt_markers = (
        "factura simplificada",
        "factura simplif",
        "simplified invoice",
        "nota de venta",
        "ticket simplificado",
    )
    _pos_receipt_score = sum(
        1
        for token in (
            "establecimiento",
            "localidad",
            "localtdad",
            "para el cliente",
            "numero operacion",
            "fecha",
            "tarjeta",
            "efectivo",
            "importe moneda",
            "importe / moneda",
            "cambio",
        )
        if token in text_context
    )
    _pos_receipt_shape = "establecimiento" in text_context and _pos_receipt_score >= 4
    _is_simplified_receipt = (
        any(marker in text_context for marker in _simplified_receipt_markers) or _pos_receipt_shape
    )

    if _is_simplified_receipt:
        # Tratar como recibo con confianza media; siempre marca para revisión
        if has_total:
            promoted_type = "RECEIPT"
            promoted_confidence = _confidence_from_map(keyword_confidence, "RECEIPT", 0.62)
            reason_tag = "simplified_receipt_keyword"
    elif any(token in text_context for token in invoice_tokens):
        if has_total and (invoice_support >= 2 or has_line_items):
            promoted_type = "INVOICE"
            promoted_confidence = _confidence_from_map(keyword_confidence, "INVOICE", 0.68)
            reason_tag = "invoice_keyword"
    elif any(token in text_context for token in payroll_tokens):
        payroll_strength = sum(
            1
            for flag in (
                has_gross_pay,
                has_deductions_total,
                has_net_pay,
                has_total,
                has_issue_date,
                has_line_items,
            )
            if flag
        )
        if payroll_strength >= 3:
            promoted_type = "PAYROLL"
            promoted_confidence = 0.64
            reason_tag = "payroll_keyword"
    elif any(token in text_context for token in sales_tokens):
        if has_total and has_issue_date:
            promoted_type = "SALES"
            promoted_confidence = 0.63
            reason_tag = "sales_keyword"
    elif any(token in text_context for token in receipt_tokens):
        if has_total and receipt_support >= 2 and not has_payroll_evidence:
            promoted_type = "RECEIPT"
            promoted_confidence = _confidence_from_map(keyword_confidence, "RECEIPT", 0.66)
            reason_tag = "receipt_keyword"

    if promoted_type is None:
        if has_issue_date and has_total and (has_doc_number or (has_vendor and has_customer)):
            promoted_type = "INVOICE"
            promoted_confidence = _confidence_from_map(like_confidence, "INVOICE", 0.64)
            reason_tag = "invoice_like_fields"
        elif (
            has_total
            and has_line_items
            and has_vendor
            and (has_doc_number or has_issue_date or has_vendor_tax_id)
        ):
            promoted_type = "INVOICE"
            promoted_confidence = _confidence_from_map(like_confidence, "INVOICE", 0.64)
            reason_tag = "invoice_like_line_items"
        elif (
            has_total and (has_gross_pay or has_deductions_total or has_net_pay) and has_line_items
        ):
            promoted_type = "PAYROLL"
            promoted_confidence = 0.62
            reason_tag = "payroll_like_fields"
        elif (
            has_issue_date
            and has_total
            and (has_vendor or has_customer)
            and not any(token in text_context for token in sales_tokens)
            and not has_payroll_evidence
        ):
            promoted_type = "RECEIPT"
            promoted_confidence = _confidence_from_map(like_confidence, "RECEIPT", 0.61)
            reason_tag = "receipt_like_fields"
        elif (
            pre_class_upper == "RECEIPT"
            and has_total
            and not any(token in text_context for token in sales_tokens)
            and not has_payroll_evidence
        ):
            promoted_type = "RECEIPT"
            promoted_confidence = _confidence_from_map(minimal_confidence, "RECEIPT", 0.56)
            reason_tag = "minimal_receipt_fields"

    if not promoted_type or promoted_confidence is None:
        return current_doc_type, current_confidence, current_reasoning, None

    promoted_reasoning = (
        f"Promoted from OCR text fallback due to {reason_tag}. "
        "Heavy AI extraction did not produce a usable classification."
    )
    return (
        promoted_type,
        max(float(current_confidence or 0.0), promoted_confidence),
        promoted_reasoning,
        reason_tag,
    )


def restore_preclassified_doc_type(
    *,
    current_doc_type: str,
    current_confidence: float,
    current_reasoning: str,
    pre_class_doc_type: str | None,
    pre_class_confidence: float | None = None,
    pre_class_layer: str | None = None,
    resolution_config: dict[str, Any] | None = None,
) -> tuple[str, float, str, str | None]:
    current_upper = str(current_doc_type or "").strip().upper() or "OTHER"
    pre_class_upper = str(pre_class_doc_type or "").strip().upper()
    if not pre_class_upper or current_upper == pre_class_upper:
        return current_doc_type, current_confidence, current_reasoning, None

    try:
        normalized_pre_conf = float(pre_class_confidence or 0.0)
    except (TypeError, ValueError):
        normalized_pre_conf = 0.0
    if normalized_pre_conf <= 0:
        return current_doc_type, current_confidence, current_reasoning, None

    cfg = dict(resolution_config or {})
    stable_preclassified_types = {
        str(item).strip().upper()
        for item in (cfg.get("restore_stable_preclassified_types") or [])
        if str(item).strip()
    }
    if pre_class_upper not in stable_preclassified_types:
        return current_doc_type, current_confidence, current_reasoning, None

    restore_conflict_doc_types = {
        str(item).strip().upper()
        for item in (cfg.get("restore_conflict_doc_types") or [])
        if str(item).strip()
    }
    allow_restore = (
        current_upper == "OTHER"
        or {
            current_upper,
            pre_class_upper,
        }
        <= restore_conflict_doc_types
    )
    if not allow_restore:
        return current_doc_type, current_confidence, current_reasoning, None

    layer = str(pre_class_layer or "pre_classifier").strip() or "pre_classifier"
    reasoning = (
        f"Restored stable pre-classification {pre_class_upper} from {layer} "
        f"after weak fallback result."
    )
    return pre_class_upper, normalized_pre_conf, reasoning, "preclassification_restore"
