import re

from app.modules.imports.extractores.utilidades import (
    clean_value,
    correct_ocr_errors,
    is_valid_concept,
    split_transfer_blocks,
)
from app.modules.imports.schemas import DocumentoProcesado


def _extraer_fecha_envio(bloque: str) -> str:
    """Extrae la fecha de envío del bloque."""
    match = re.search(
        r"Fecha\s+de\s+env[ií]o:\s*(\d{2}[-/ ]\d{2}[-/ ]\d{4})", bloque, re.IGNORECASE
    )
    if match:
        return clean_value(match.group(1))
    match = re.search(r"\b(\d{2}[-/ ]\d{2}[-/ ]\d{4})\b", bloque)
    return clean_value(match.group(1)) if match else "desconocida"


def _extraer_fecha_valor(bloque: str) -> str | None:
    """Extrae la fecha valor del bloque."""
    match = re.search(r"Fecha\s+valor[:\s]+(\d{2}[-/ ]\d{2}[-/ ]\d{4})", bloque, re.IGNORECASE)
    return clean_value(match.group(1)) if match else None


def _extraer_importe(bloque: str) -> float:
    """Extrae el importe con fallback progresivo."""
    # Intentar etiquetas conocidas en orden de prioridad
    etiquetas = [
        r"[Ii]mporte\s*(?:a\s+)?[Ll]iquidar[:\s]*",
        r"[Cc]ontra?valor[:\s]*",
        r"[Ii]mporte\s+ordenado[:\s]*",
        r"[Ii]mporte[:\s]*",
    ]

    for etiqueta in etiquetas:
        match = re.search(rf"{etiqueta}(-?[\d.,]+)\s*EUR?", bloque, re.IGNORECASE)
        if match:
            valor_raw = match.group(1).replace(" ", "").replace(",", ".")
            # Manejar formato europeo con puntos como separador de miles
            if valor_raw.count(".") > 1:
                valor_raw = valor_raw.replace(".", "", valor_raw.count(".") - 1)
            try:
                return float(valor_raw)
            except ValueError:
                continue

    # Fallback: buscar patrón "XXX,XX EUR" cerca de BENEFICIARIO
    match = re.search(
        r"BENEFICIARIO.*?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*EUR", bloque, re.IGNORECASE | re.DOTALL
    )
    if match:
        valor_raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(valor_raw)
        except ValueError:
            pass

    return 0.0


def _extraer_iban_ordenante(bloque: str) -> str:
    """Extrae el IBAN del ordenante (Cuenta:)."""
    match = re.search(r"Cuenta:\s*(ES\d{2}[\d\s*]{16,24})", bloque, re.IGNORECASE)
    if match:
        return clean_value(match.group(1).replace(" ", "").replace("*", ""))
    return "desconocida"


def _extraer_iban_beneficiario(bloque: str) -> str:
    """Extrae el IBAN del beneficiario."""
    match = re.search(r"IBAN[:\s]*(ES\d{2}[\d\s]{16,24})", bloque, re.IGNORECASE)
    if match:
        return clean_value(match.group(1).replace(" ", ""))
    return "desconocida"


def _extraer_ordenante(bloque: str) -> str:
    """Extrae el nombre del ordenante."""
    match = re.search(r"ORDENANTE\s*\n?\s*(.+?)\s*\n", bloque, re.IGNORECASE)
    if match:
        nombre = match.group(1).strip()
        # Limpiar si contiene IMPORTE u otros campos
        nombre = re.split(r"\s+(IMPORTE|BENEFICIARIO|\d)", nombre)[0]
        if len(nombre) > 3:
            return clean_value(nombre)

    # Alternativa: buscar "Titular:"
    match = re.search(r"Titular[:\s]+([A-Z\s]+?)(?:\s+Importe|\s+Tipo|\n)", bloque, re.IGNORECASE)
    if match:
        return clean_value(match.group(1))

    return "desconocido"


def _extraer_beneficiario(bloque: str) -> str:
    """Extrae el nombre del beneficiario."""
    # Patrón 1: "Ultimo Beneficiario:" o variantes OCR - capturar hasta siguiente campo
    match = re.search(
        r"[UÚ]ltimo?\s+Beneficiari[oa][:\s]+([A-Z][A-Z\s]+?)(?:\s*\n|\s+CONCEPTO|\s+Contravalor|\s+Tipo)",
        bloque,
        re.IGNORECASE,
    )
    if match:
        nombre = match.group(1).strip()
        # Limpiar si capturó texto extra
        nombre = re.split(r"\s+(CONCEPTO|Contravalor|Tipo|GASTOS)", nombre, flags=re.IGNORECASE)[0]
        if len(nombre) > 2:
            return clean_value(nombre)

    # Patrón 2: Después de "BENEFICIARIO" en el encabezado
    match = re.search(r"BENEFICIARIO\s*\n?\s*(.+?)\s*\n", bloque, re.IGNORECASE)
    if match:
        nombre = match.group(1).strip()
        nombre = re.split(r"\s+(\d|POR CUENTA|Importe)", nombre)[0]
        if len(nombre) > 3:
            return clean_value(nombre)

    return "desconocido"


def _extraer_concepto(bloque: str) -> str:
    """Extrae el concepto de la transferencia."""
    # Patrón 1: CONCEPTO: seguido del texto hasta fin de bloque o siguiente campo
    match = re.search(
        r"CONCEPTO[:\s]+(.+?)(?:\s*Nuestra|\s*Fecha\s+operaci|\s*Oficina|\s*$)",
        bloque,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        concepto = match.group(1).strip()
        # Limpiar saltos de línea y espacios extras
        concepto = re.sub(r"\s+", " ", concepto)
        # Eliminar campos que se pueden colar
        concepto = re.split(
            r"(Nuestra|Fecha operaci|referencia:|Oficina)", concepto, flags=re.IGNORECASE
        )[0]
        concepto = concepto.strip()
        if is_valid_concept(concepto):
            return clean_value(concepto)

    return "Documento sin concepto"


def _extraer_referencia(bloque: str) -> str | None:
    """Extrae la referencia de la transferencia."""
    match = re.search(r"Nuestra\s+referencia[:\s]+(\w+)", bloque, re.IGNORECASE)
    return match.group(1) if match else None


def extract_transfers(text: str) -> list[DocumentoProcesado]:
    text = correct_ocr_errors(text)
    bloques = split_transfer_blocks(text)
    print(f"[INFO] TOTAL BLOQUES DETECTADOS: {len(bloques)}")

    resultados: list[DocumentoProcesado] = []

    for i, bloque in enumerate(bloques):
        print(f"\n--- BLOQUE {i + 1} ---")
        print(bloque[:500])
        try:
            fecha = _extraer_fecha_envio(bloque)
            importe = _extraer_importe(bloque)
            iban_ordenante = _extraer_iban_ordenante(bloque)
            iban_beneficiario = _extraer_iban_beneficiario(bloque)
            beneficiario = _extraer_beneficiario(bloque)
            concepto = _extraer_concepto(bloque)
            referencia = _extraer_referencia(bloque)

            # Usar IBAN del beneficiario como cuenta principal
            cuenta = iban_beneficiario if iban_beneficiario != "desconocida" else iban_ordenante

            resultados.append(
                DocumentoProcesado(
                    fecha=fecha,
                    concepto=concepto,
                    tipo="gasto",
                    importe=importe,
                    cuenta=cuenta,
                    categoria="otros",
                    cliente=beneficiario,
                    invoice=referencia,
                    documentoTipo="transferencia",
                    origen="ocr",
                )
            )
        except re.error as rex:
            print(f"[ERROR] Error regex en extraer_transferencias: {rex}")
            continue
        except Exception as e:
            print(f"[ERROR] Error en bloque {i + 1}: {e}")
            continue

    return resultados
