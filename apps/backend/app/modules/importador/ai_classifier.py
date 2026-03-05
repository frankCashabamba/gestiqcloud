"""Clasificador AI y extractor de campos para documentos."""
from __future__ import annotations
import json
import logging
import re
from typing import Any
from app.services.ai.base import AITask
from app.services.ai.service import AIService

logger = logging.getLogger("importador.ai")

CONFIDENCE_THRESHOLD = 0.85

DOC_TYPES = ["FACTURA", "RECIBO", "NOTA_CREDITO", "BOLETA", "EXTRACTO_BANCARIO", "TICKET", "OTRO"]

EXTRACTION_FIELDS = {
    "FACTURA": ["ruc", "proveedor", "fecha", "serie", "correlativo", "subtotal", "igv", "monto_total", "moneda", "descripcion"],
    "RECIBO": ["ruc", "proveedor", "fecha", "monto_total", "concepto", "moneda"],
    "NOTA_CREDITO": ["ruc", "proveedor", "fecha", "serie", "correlativo", "subtotal", "igv", "monto_total", "moneda", "motivo"],
    "BOLETA": ["ruc", "proveedor", "fecha", "serie", "correlativo", "monto_total", "moneda"],
    "EXTRACTO_BANCARIO": ["banco", "cuenta", "fecha_inicio", "fecha_fin", "saldo_inicial", "saldo_final", "moneda"],
    "TICKET": ["establecimiento", "fecha", "monto_total", "moneda"],
    "OTRO": ["fecha", "monto_total", "descripcion"],
}


async def classify_document(
    text: str,
    filename: str = "",
    format_hint: str = "",
    recipe_config: dict | None = None,
) -> dict[str, Any]:
    """Classify document type using AI.
    Returns: {"tipo_documento": str, "confianza": float, "razonamiento": str,
              "raw_response": str, "model_used": str, "prompt_sent": str}
    """
    rc = recipe_config or {}
    system_prefix = rc.get("prompt_system", "")

    prompt = ""
    if system_prefix:
        prompt += system_prefix.rstrip() + "\n\n"
    prompt += (
        "Clasifica este documento contable/financiero.\n\n"
        f"Nombre archivo: {filename}\n"
        f"Formato: {format_hint}\n\n"
        f"Texto del documento (primeros 3000 chars):\n{text[:3000]}\n\n"
        f"Tipos posibles: {DOC_TYPES}\n\n"
        "Responde SOLO con JSON válido:\n"
        '{"tipo_documento": "...", "confianza": 0.0-1.0, "razonamiento": "breve explicación"}'
    )

    model_override = rc.get("model")

    try:
        response = await AIService.query(
            task=AITask.CLASSIFICATION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=300,
            module="importador",
            enable_recovery=True,
        )

        raw_content = response.content
        model_used = response.model or "unknown"

        if response.is_error:
            logger.warning("AI classification failed: %s", response.error)
            result = _fallback_classify(text, filename)
            result["raw_response"] = response.error
            result["model_used"] = model_used
            result["prompt_sent"] = prompt[:500]
            return result

        result = _parse_json_response(raw_content)
        if result and result.get("tipo_documento") in DOC_TYPES:
            result["raw_response"] = raw_content
            result["model_used"] = model_used
            result["prompt_sent"] = prompt[:500]
            return result

        fallback = _fallback_classify(text, filename)
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = prompt[:500]
        return fallback

    except Exception as exc:
        logger.error("AI classification error: %s", exc)
        result = _fallback_classify(text, filename)
        result["raw_response"] = str(exc)
        result["model_used"] = "fallback"
        result["prompt_sent"] = prompt[:500]
        return result


async def extract_fields(
    text: str,
    tipo_documento: str,
    filename: str = "",
    recipe_config: dict | None = None,
) -> dict[str, Any]:
    """Extract structured fields from document text using AI.
    Returns: dict with field names as keys plus _raw_response, _model_used, _prompt_sent.
    """
    rc = recipe_config or {}
    fields = EXTRACTION_FIELDS.get(tipo_documento, EXTRACTION_FIELDS["OTRO"])

    if rc.get("prompt_user"):
        prompt = rc["prompt_user"].replace("{text}", text[:4000]).replace("{tipo}", tipo_documento).replace("{fields}", str(fields))
    else:
        prompt = (
            f"Extrae los siguientes campos de este documento de tipo {tipo_documento}.\n\n"
            f"Campos a extraer: {fields}\n\n"
            f"Texto del documento:\n{text[:4000]}\n\n"
            "Reglas:\n"
            "- Fechas en formato YYYY-MM-DD\n"
            "- Montos como números sin separadores de miles (usar punto decimal)\n"
            "- Si es NOTA_CREDITO, los montos deben ser NEGATIVOS\n"
            "- Si no encuentras un campo, usa null\n"
            "- RUC/DNI: solo dígitos\n\n"
            "Responde SOLO con JSON válido con los campos extraídos."
        )

    if rc.get("prompt_system"):
        prompt = rc["prompt_system"].rstrip() + "\n\n" + prompt

    try:
        response = await AIService.query(
            task=AITask.EXTRACTION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=800,
            module="importador",
            enable_recovery=True,
        )

        raw_content = response.content
        model_used = response.model or "unknown"

        if response.is_error:
            logger.warning("AI extraction failed: %s", response.error)
            return {"_raw_response": response.error, "_model_used": model_used, "_prompt_sent": prompt[:500]}

        result = _parse_json_response(raw_content)
        if result:
            result["_raw_response"] = raw_content
            result["_model_used"] = model_used
            result["_prompt_sent"] = prompt[:500]
            return result
        return {"_raw_response": raw_content, "_model_used": model_used, "_prompt_sent": prompt[:500]}

    except Exception as exc:
        logger.error("AI extraction error: %s", exc)
        return {"_raw_response": str(exc), "_model_used": "error", "_prompt_sent": prompt[:500]}


def _fallback_classify(text: str, filename: str) -> dict[str, Any]:
    """Rule-based fallback classification when AI is unavailable."""
    text_lower = text.lower()
    fn_lower = filename.lower()

    patterns = {
        "FACTURA": ["factura", "invoice", "fact.", "f/"],
        "NOTA_CREDITO": ["nota de crédito", "nota de credito", "credit note", "nc-", "nc/"],
        "RECIBO": ["recibo", "receipt", "recibo de pago"],
        "BOLETA": ["boleta", "b/v", "boleta de venta"],
        "EXTRACTO_BANCARIO": ["extracto", "estado de cuenta", "bank statement", "movimientos"],
        "TICKET": ["ticket", "voucher", "comprobante"],
    }

    best_type = "OTRO"
    best_score = 0.0

    for doc_type, keywords in patterns.items():
        matches = sum(1 for kw in keywords if kw in text_lower or kw in fn_lower)
        if matches > best_score:
            best_score = matches
            best_type = doc_type

    confidence = min(0.7, 0.3 + (best_score * 0.2)) if best_score > 0 else 0.2

    return {
        "tipo_documento": best_type,
        "confianza": confidence,
        "razonamiento": f"Clasificación por reglas (AI no disponible). Coincidencias: {int(best_score)}",
    }


def _parse_json_response(content: str) -> dict | None:
    """Parse JSON from AI response, handling markdown code blocks."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None
