"""Analizador AI universal para cualquier tipo de documento contable."""
from __future__ import annotations
import json
import logging
import re
from typing import Any
from app.services.ai.base import AITask
from app.services.ai.service import AIService

logger = logging.getLogger("importador.ai")

CONFIDENCE_THRESHOLD = 0.85


async def analyze_document(
    content: str,
    filename: str = "",
    format_hint: str = "",
    has_structured_rows: bool = False,
    recipe_config: dict | None = None,
) -> dict[str, Any]:
    """Analiza cualquier documento contable en una sola llamada LLM.

    Para Excel/CSV con filas ya parseadas (has_structured_rows=True):
      - Recibe cabeceras + muestra de filas
      - LLM clasifica el tipo y confirma los nombres de columnas
      - Las filas reales vienen del parser (structured_data), no del LLM

    Para PDF/imagen/XML/TXT (has_structured_rows=False):
      - Recibe texto extraído por OCR
      - LLM clasifica + extrae todos los campos

    Returns: {
        "tipo_documento": str,
        "confianza": float,
        "razonamiento": str,
        "es_tabla": bool,
        "columnas": list[str],   # si es_tabla=True
        "campos": dict,           # si es_tabla=False
        "raw_response": str,
        "model_used": str,
        "prompt_sent": str,
    }
    """
    rc = recipe_config or {}

    system_prompt = rc.get("prompt_system") or (
        "Eres un analizador de documentos contables universal. "
        "Identificas y extraes información de CUALQUIER tipo de documento: "
        "facturas, inventarios, nóminas, extractos bancarios, listas de precios, "
        "presupuestos, órdenes de compra, costeos, recibos, boletas, contratos, etc."
    )

    tabular_note = (
        "NOTA: El contenido ya está preprocesado como tabla estructurada. "
        "Si reconoces una lista o tabla, marca es_tabla=true y proporciona los nombres de columna limpios. "
        "NO necesitas devolver las filas individuales.\n\n"
        if has_structured_rows else ""
    )

    # For OCR/PDF content use more chars; for pre-structured tables 4000 is enough
    content_limit = 4000 if has_structured_rows else 7000

    user_prompt = (
        f"{tabular_note}"
        f"Archivo: {filename} | Formato: {format_hint}\n\n"
        f"Contenido:\n{content[:content_limit]}\n\n"
        "Analiza el documento y responde SOLO con JSON válido:\n"
        "{\n"
        '  "tipo_documento": "FACTURA | TICKETDEVENTA | RECIBO | BOLETA | TICKET | NOTA_CREDITO | '
        'ORDEN_COMPRA | PRESUPUESTO | INVENTARIO | LISTA_PRECIOS | COSTEO | NOMINA | '
        'EXTRACTO_BANCARIO | MOVIMIENTOS_BANCARIOS | OTRO",\n'
        '  "confianza": 0.0-1.0,\n'
        '  "razonamiento": "explicación breve",\n'
        '  "es_tabla": true o false,\n'
        '  "columnas": ["col1", "col2"],\n'
        '  "campos": {\n'
        '    "proveedor": "nombre de quien EMITE/VENDE — busca: Razón Social emisor, nombre empresa vendedora",\n'
        '    "ruc_proveedor": "RUC/NIT del emisor o null",\n'
        '    "cliente": "nombre de quien RECIBE/COMPRA — busca: DATOS DEL CLIENTE, receptor",\n'
        '    "ruc_cliente": "RUC/CI del cliente o null",\n'
        '    "numero_documento": "número de factura/pedido/ticket — busca: No., Pedido No., Factura No.",\n'
        '    "fecha": "fecha de emisión YYYY-MM-DD o null",\n'
        '    "monto_total": NÚMERO — busca VALOR TOTAL o TOTAL al FINAL del documento, NO la cantidad de productos,\n'
        '    "subtotal": número subtotal sin IVA o null,\n'
        '    "iva": número IVA o null,\n'
        '    "moneda": "USD/EUR/etc o null",\n'
        '    "lineas": [\n'
        '      {"descripcion": "nombre producto", "cantidad": número, "precio_unitario": número, "precio_total": número}\n'
        '    ]\n'
        "  }\n"
        "}\n"
        "Reglas CRÍTICAS:\n"
        "- monto_total = el GRAN TOTAL al final del documento (busca 'VALOR TOTAL', 'TOTAL A PAGAR', 'TOTAL'). "
        "  NO confundas con la cantidad de unidades de un producto.\n"
        "- lineas = cada línea de producto/servicio con su cantidad y precio por unidad\n"
        "- proveedor = la empresa que EMITE la factura (vendedor/acreedor)\n"
        "- cliente = la persona/empresa que PAGA (comprador/deudor)\n"
        "- Si es_tabla=true: solo devuelve 'columnas'; en 'campos' pon fecha y monto_total si los ves\n"
        "- Fechas: YYYY-MM-DD. Montos: número con punto decimal (ej: 2145.00). Ausentes: null\n"
        "- No inventes datos que no estén en el documento."
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
            fallback.update({"es_tabla": has_structured_rows, "columnas": [], "campos": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = full_prompt[:500]
            return fallback

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("tipo_documento"):
            parsed.setdefault("es_tabla", False)
            parsed.setdefault("columnas", [])
            parsed.setdefault("campos", {})
            parsed.setdefault("confianza", 0.7)
            parsed.setdefault("razonamiento", "")
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = full_prompt[:500]
            return parsed

        fallback = _fallback_classify(content, filename)
        fallback.update({"es_tabla": has_structured_rows, "columnas": [], "campos": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback

    except Exception as exc:
        logger.error("AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename)
        fallback.update({"es_tabla": has_structured_rows, "columnas": [], "campos": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback


def _fallback_classify(text: str, filename: str) -> dict[str, Any]:
    """Clasificación por reglas cuando el AI no está disponible."""
    text_lower = text.lower()
    fn_lower = filename.lower()

    patterns = {
        "FACTURA": ["factura", "invoice", "fact.", "f/"],
        "NOTA_CREDITO": ["nota de crédito", "nota de credito", "credit note", "nc-"],
        "RECIBO": ["recibo", "receipt", "recibo de pago"],
        "BOLETA": ["boleta", "boleta de venta"],
        "EXTRACTO_BANCARIO": ["extracto", "estado de cuenta", "bank statement"],
        "TICKET": ["ticket", "voucher"],
        "NOMINA": ["nómina", "nomina", "planilla", "rol de pagos"],
        "INVENTARIO": ["inventario", "stock", "existencias", "kardex"],
        "COSTEO": ["costeo", "costo de producción"],
        "LISTA_PRECIOS": ["lista de precios", "price list", "tarifario"],
        "MOVIMIENTOS_BANCARIOS": ["movimientos", "transacciones bancarias"],
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
    """Parsea JSON de la respuesta del LLM, manejando bloques markdown."""
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
