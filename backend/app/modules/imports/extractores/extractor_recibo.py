from typing import List
from app.modules.imports.schemas import DocumentoProcesado
from app.modules.imports.extractores.utilidades import buscar_multiple, es_concepto_valido
import re


def extraer_recibo(texto: str) -> List[DocumentoProcesado]:
    # Limpieza básica del texto
    texto = texto.replace('€', 'EUR').replace('$', 'USD')
    texto = re.sub(r'[^\x00-\x7F]+', ' ', texto)  # Quitar caracteres raros

    # Fecha de pago
    fecha = buscar_multiple([
        r"Date\s*paid[:\-]?\s*(\w+\s+\d{1,2},?\s+\d{4})",
        r"paid\s*on\s*(\w+\s+\d{1,2},?\s+\d{4})",
        r"\b(\d{2}/\d{2}/\d{4})\b",
        r"\b(\d{2}-\d{2}-\d{4})\b",
        r"(\d{4}-\d{2}-\d{2})",
    ], texto)

    # Importe pagado
    importe = buscar_multiple([
        r"Amount\s*paid[^0-9]*([\d]{1,4}[.,]\d{2})",
        r"Total[:;\s]*([\d]{1,4}[.,]\d{2})",
        r"([\d]{1,4}[.,]\d{2})\s*(USD|EUR)?",
    ], texto) or "0.00"

    # Cliente
    cliente = buscar_multiple([
        r"Bill\s*to\s+([^\s@]+@[^\s]+)",
        r"Bill\s*to[:;\s]*\n?(.+)",
        r"Cliente[:;\s]*(.+)",
        r"CDAD\.?\s+(.{3,80})",
        r"([A-Z][A-Za-z]+ [A-Z][A-Za-z]+)",
    ], texto) or "desconocido"

    # Concepto
    # Concepto
    concepto = buscar_multiple([
        r"(CUOTA\s+[A-Z]{3,}\.?\s*/?\s*\d{4})",
        r"(SERVICIOS\s+[^\n]{3,80})",
        r"(ALQUILER\s+[^\n]{3,80})",
        r"Description\s+Qty\s+Unit price\s+Amount\s+([\s\S]{10,100})",
        r"(Servers[^\n]{0,80})",
        r"(Postgres[^\n]{0,80})",
    ], texto)

    concepto_raw = concepto or ""
    concepto_final = concepto_raw if es_concepto_valido(concepto_raw) else "Documento sin concepto"

    return [DocumentoProcesado(
        fecha=fecha or "desconocida",
        concepto=concepto_final,
        tipo="gasto",  # o ingreso, si lo deseas inferir por algún criterio
        importe=float(importe.replace(",", ".")),
        cuenta="desconocida",
        categoria="otros",
        cliente=cliente,
        invoice=None,
        documentoTipo="recibo",
        origen="ocr"
    )]
