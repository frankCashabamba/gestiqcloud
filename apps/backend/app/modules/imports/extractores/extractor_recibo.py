import re
from typing import Any

from app.modules.imports.domain.canonical_schema import CanonicalDocument, build_routing_proposal
from app.modules.imports.extractores.utilidades import buscar_multiple, es_concepto_valido


def extraer_recibo(texto: str, country: str = "EC") -> list[dict[str, Any]]:
    """
    Extrae datos de recibo/ticket y retorna schema canónico.

    Args:
        texto: Texto OCR del documento
        country: País del documento (EC, ES, etc.)

    Returns:
        Lista con un CanonicalDocument tipo "expense_receipt"
    """
    # Limpieza básica del texto
    texto = texto.replace("€", "EUR").replace("$", "USD")
    texto = re.sub(r"[^\x00-\x7F]+", " ", texto)  # Quitar caracteres raros

    # Fecha de pago
    fecha = buscar_multiple(
        [
            r"Date\s*paid[:\-]?\s*(\w+\s+\d{1,2},?\s+\d{4})",
            r"paid\s*on\s*(\w+\s+\d{1,2},?\s+\d{4})",
            r"\b(\d{2}/\d{2}/\d{4})\b",
            r"\b(\d{2}-\d{2}-\d{4})\b",
            r"(\d{4}-\d{2}-\d{2})",
        ],
        texto,
    )

    # Importe pagado
    importe_str = (
        buscar_multiple(
            [
                r"Amount\s*paid[^0-9]*([\d]{1,4}[.,]\d{2})",
                r"Total[:;\s]*([\d]{1,4}[.,]\d{2})",
                r"([\d]{1,4}[.,]\d{2})\s*(USD|EUR)?",
            ],
            texto,
        )
        or "0.00"
    )

    importe = float(importe_str.replace(",", "."))

    # Cliente/Proveedor
    cliente = (
        buscar_multiple(
            [
                r"Bill\s*to\s+([^\s@]+@[^\s]+)",
                r"Bill\s*to[:;\s]*\n?(.+)",
                r"Cliente[:;\s]*(.+)",
                r"CDAD\.?\s+(.{3,80})",
                r"([A-Z][A-Za-z]+ [A-Z][A-Za-z]+)",
            ],
            texto,
        )
        or "desconocido"
    )

    # Concepto
    concepto = buscar_multiple(
        [
            r"(CUOTA\s+[A-Z]{3,}\.?\s*/?\s*\d{4})",
            r"(SERVICIOS\s+[^\n]{3,80})",
            r"(ALQUILER\s+[^\n]{3,80})",
            r"Description\s+Qty\s+Unit price\s+Amount\s+([\s\S]{10,100})",
            r"(Servers[^\n]{0,80})",
            r"(Postgres[^\n]{0,80})",
        ],
        texto,
    )

    concepto_raw = concepto or ""
    concepto_final = concepto_raw if es_concepto_valido(concepto_raw) else "Documento sin concepto"

    # Construir schema canónico
    subtotal = importe / 1.12  # Asume IVA 12% incluido
    tax = importe - subtotal

    canonical: CanonicalDocument = {
        "doc_type": "expense_receipt",
        "country": country,
        "currency": "USD" if country == "EC" else "EUR",
        "issue_date": fecha or None,
        "vendor": {
            "name": cliente,
        },
        "totals": {
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": importe,
            "tax_breakdown": [
                {
                    "rate": 12.0 if country == "EC" else 21.0,
                    "amount": round(tax, 2),
                    "code": f"IVA{12 if country == 'EC' else 21}-{country}",
                }
            ],
        },
        "lines": [
            {
                "desc": concepto_final,
                "qty": 1.0,
                "unit_price": importe,
                "total": importe,
                "tax_code": f"IVA{12 if country == 'EC' else 21}",
            }
        ],
        "payment": {
            "method": "cash",  # Asume efectivo por defecto para recibos
        },
        "source": "ocr",
        "confidence": 0.6,
    }

    # Propuesta de enrutamiento
    canonical["routing_proposal"] = build_routing_proposal(
        canonical, category_code="OTROS", account="6290", confidence=0.60
    )

    return [canonical]
