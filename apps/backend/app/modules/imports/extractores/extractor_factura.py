from typing import Any

from app.modules.imports.domain.canonical_schema import CanonicalDocument, build_routing_proposal
from app.modules.imports.extractores.utilidades import (
    buscar_cif,
    buscar_cliente,
    buscar_concepto,
    buscar_descripcion,
    buscar_emisor,
    buscar_fecha,
    buscar_importe,
    buscar_numero_factura,
    buscar_numero_mayor,
    buscar_subtotal,
    es_concepto_valido,
)


def extraer_factura(texto: str, country: str = "EC") -> list[dict[str, Any]]:
    """
    Extrae datos de factura y retorna schema canónico.

    Args:
        texto: Texto OCR del documento
        country: País del documento (EC, ES, etc.)

    Returns:
        Lista con un CanonicalDocument tipo "invoice"
    """
    try:
        fecha = buscar_fecha(texto)
        numero = buscar_numero_factura(texto)
        cif = buscar_cif(texto)

        total_raw = buscar_importe(texto) or buscar_numero_mayor(texto) or "0.00"
        try:
            total = float(total_raw.replace(",", "."))
        except Exception:
            total = 0.0

        subtotal_raw = buscar_subtotal(texto)
        subtotal = 0.0
        if subtotal_raw:
            try:
                subtotal = float(subtotal_raw.strip().replace(",", "."))
            except Exception:
                subtotal = total / 1.12  # Asume IVA 12% EC como fallback

        descripcion = buscar_descripcion(texto)
        concepto = buscar_concepto(texto)
        emisor = buscar_emisor(texto)
        cliente = buscar_cliente(texto)

        concepto_final = concepto or descripcion or ""
        if not es_concepto_valido(concepto_final):
            concepto_final = "Documento sin concepto"

        # Construir schema canónico
        tax = total - subtotal if subtotal > 0 else 0.0

        canonical: CanonicalDocument = {
            "doc_type": "invoice",
            "country": country,
            "currency": "USD" if country == "EC" else "EUR",
            "issue_date": fecha or None,
            "invoice_number": numero,
            "vendor": {
                "name": emisor or "Proveedor desconocido",
                "tax_id": cif,
                "country": country,
            },
            "buyer": {
                "name": cliente or "Cliente desconocido",
            },
            "totals": {
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "tax_breakdown": (
                    [
                        {
                            "rate": 12.0 if country == "EC" else 21.0,
                            "amount": tax,
                            "code": f"IVA{12 if country == 'EC' else 21}-{country}",
                            "base": subtotal,
                        }
                    ]
                    if tax > 0
                    else []
                ),
            },
            "lines": [
                {
                    "desc": concepto_final,
                    "qty": 1.0,
                    "unit_price": total,
                    "total": total,
                    "tax_code": f"IVA{12 if country == 'EC' else 21}",
                    "tax_amount": tax,
                }
            ],
            "source": "ocr",
            "confidence": 0.7,  # Confianza media para OCR
        }

        # Añadir propuesta de enrutamiento
        canonical["routing_proposal"] = build_routing_proposal(
            canonical,
            category_code="OTROS",
            account="6290",  # Cuenta de gastos generales
            confidence=0.65,
        )

        return [canonical]

    except Exception as e:
        print("❌ Error en extraer_factura:", e)
        return []
