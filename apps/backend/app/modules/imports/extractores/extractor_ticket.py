"""Extractor para tickets de venta POS (impresoras térmicas 58mm/80mm)."""

import re
from typing import Any

from app.modules.imports.domain.canonical_schema import CanonicalDocument, build_routing_proposal
from app.modules.imports.extractores.utilidades import buscar_multiple
from app.modules.imports.schemas import DocumentoProcesado


def extraer_ticket_documentos(texto: str, country: str = "EC") -> list[DocumentoProcesado]:
    """
    Wrapper que devuelve DocumentoProcesado para compatibilidad con services.procesar_documento.
    """
    resultados_canonicos = extraer_ticket(texto, country)
    documentos = []
    
    for canonical in resultados_canonicos:
        totals = canonical.get("totals", {})
        doc = DocumentoProcesado(
            tipo="ticket_pos",
            importe=totals.get("total", 0.0),
            cliente=None,
            invoice=canonical.get("invoice_number"),
            fecha=canonical.get("issue_date"),
            cuenta=None,
            concepto="Ticket de venta POS",
            categoria="ventas",
            origen="ocr",
            documentoTipo="ticket_pos",
        )
        documentos.append(doc)
    
    return documentos


def extraer_ticket(texto: str, country: str = "EC") -> list[dict[str, Any]]:
    """
    Extrae datos de un ticket POS térmico y retorna schema canónico.

    Formato esperado:
        TICKET DE VENTA
        Nº R-0005
        31/10/2025 23:50
        10.000x tapados - $1.50
        1.000x aceite grande - $2.50
        Total: $0.00
        ¡Gracias por su compra!

    Args:
        texto: Texto OCR del ticket
        country: País del documento (EC, ES, etc.)

    Returns:
        Lista con un CanonicalDocument tipo "expense_receipt"
    """
    texto_limpio = texto.replace("€", "EUR").replace("$", " ")
    texto_limpio = re.sub(r"[^\x00-\x7F]+", " ", texto_limpio)

    numero_ticket = buscar_multiple(
        [
            r"N[ºo°]?\s*R[-\s]*(\d+)",
            r"Ticket\s*(?:N[ºo°]?)?\s*[:\-]?\s*(\w+)",
            r"R[-\s]*(\d{4,})",
        ],
        texto,
    )

    fecha_hora = buscar_multiple(
        [
            r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})",
            r"(\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2})",
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})",
            r"(\d{2}/\d{2}/\d{4})",
            r"(\d{2}-\d{2}-\d{4})",
        ],
        texto,
    )

    fecha_iso = None
    if fecha_hora:
        fecha_match = re.match(r"(\d{2})[/-](\d{2})[/-](\d{4})", fecha_hora)
        if fecha_match:
            dia, mes, anio = fecha_match.groups()
            fecha_iso = f"{anio}-{mes}-{dia}"

    lineas_productos = _extraer_lineas_productos(texto)

    total_str = buscar_multiple(
        [
            r"Total[:\s]*\$?\s*([\d.,]+)",
            r"TOTAL[:\s]*\$?\s*([\d.,]+)",
            r"Total\s*[:\-]?\s*([\d]{1,6}[.,]\d{2})",
        ],
        texto,
    )
    total = _parsear_importe(total_str) if total_str else 0.0

    if total == 0.0 and lineas_productos:
        total = sum(line.get("total", 0.0) for line in lineas_productos)

    subtotal = total / 1.12
    tax = total - subtotal

    canonical: CanonicalDocument = {
        "doc_type": "expense_receipt",
        "country": country,
        "currency": "USD" if country == "EC" else "EUR",
        "issue_date": fecha_iso,
        "invoice_number": f"R-{numero_ticket}" if numero_ticket else None,
        "vendor": {
            "name": "POS Venta",
        },
        "totals": {
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(total, 2),
            "tax_breakdown": [
                {
                    "rate": 12.0 if country == "EC" else 21.0,
                    "amount": round(tax, 2),
                    "code": f"IVA{12 if country == 'EC' else 21}-{country}",
                }
            ],
        },
        "lines": lineas_productos if lineas_productos else [
            {
                "desc": "Ticket POS",
                "qty": 1.0,
                "unit_price": total,
                "total": total,
                "tax_code": f"IVA{12 if country == 'EC' else 21}",
            }
        ],
        "payment": {
            "method": "cash",
        },
        "metadata": {
            "ticket_number": numero_ticket,
            "datetime_raw": fecha_hora,
            "source_type": "ticket_pos",
        },
        "source": "ocr",
        "confidence": 0.65,
    }

    canonical["routing_proposal"] = build_routing_proposal(
        canonical, category_code="VENTAS", account="4100", confidence=0.65
    )

    return [canonical]


def _extraer_lineas_productos(texto: str) -> list[dict[str, Any]]:
    """
    Extrae líneas de productos del formato POS.

    Formatos soportados:
        10.000x tapados - $1.50
        1.000x aceite grande - $2.50
        2 x Coca Cola - 3.50
        3x Pan - $0.25
    """
    lineas = []

    patrones = [
        r"([\d.,]+)\s*x\s+(.+?)\s*[-–]\s*\$?\s*([\d.,]+)",
        r"([\d.,]+)\s*x\s*(.+?)\s+\$?\s*([\d.,]+)",
        r"(\d+)\s+(.+?)\s+\$?\s*([\d.,]+)$",
    ]

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue

        for patron in patrones:
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                cantidad_str, descripcion, precio_str = match.groups()

                cantidad = _parsear_cantidad(cantidad_str)
                precio = _parsear_importe(precio_str)
                descripcion = descripcion.strip()

                if descripcion.lower() in ("total", "subtotal", "iva", "tax"):
                    continue

                lineas.append({
                    "desc": descripcion,
                    "qty": cantidad,
                    "unit_price": precio,
                    "total": round(cantidad * precio, 2),
                    "tax_code": "IVA12",
                })
                break

    return lineas


def _parsear_cantidad(valor: str) -> float:
    """Parsea cantidad con soporte para separadores de miles."""
    valor = valor.replace(",", ".").replace(" ", "")
    valor = re.sub(r"\.(?=\d{3}(?:\.|$))", "", valor)
    try:
        return float(valor)
    except ValueError:
        return 1.0


def _parsear_importe(valor: str) -> float:
    """Parsea importe monetario."""
    if not valor:
        return 0.0
    valor = valor.replace(",", ".").replace(" ", "")
    valor = re.sub(r"\.(?=\d{3}(?:\.|$))", "", valor)
    try:
        return float(valor)
    except ValueError:
        return 0.0


def extraer(documento: dict[str, Any]) -> dict[str, Any]:
    """
    Función wrapper compatible con el mapa de extractores de task_extract.

    Args:
        documento: Dict con 'text' del OCR

    Returns:
        Dict con datos extraídos del ticket
    """
    texto = documento.get("text", "") or documento.get("ocr_text", "")
    country = documento.get("country", "EC")

    resultados = extraer_ticket(texto, country)

    if resultados:
        return resultados[0]

    return {
        "doc_type": "expense_receipt",
        "country": country,
        "error": "No se pudo extraer datos del ticket",
    }
