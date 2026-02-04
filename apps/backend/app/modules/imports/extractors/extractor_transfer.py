import re

from app.modules.imports.extractors.utilities import (
    correct_ocr_errors,
    split_transfer_blocks,
    is_valid_concept,
    clean_value,
)
from app.modules.imports.schemas import DocumentoProcesado


def _extract_send_date(block: str) -> str:
    """Extracts the send date from the block."""
    match = re.search(
        r"Fecha\s+de\s+env[ií]o:\s*(\d{2}[-/ ]\d{2}[-/ ]\d{4})", block, re.IGNORECASE
    )
    if match:
        return clean_value(match.group(1))
    match = re.search(r"\b(\d{2}[-/ ]\d{2}[-/ ]\d{4})\b", block)
    return clean_value(match.group(1)) if match else "unknown"


def _extract_value_date(block: str) -> str | None:
    """Extracts the value date from the block."""
    match = re.search(r"Fecha\s+valor[:\s]+(\d{2}[-/ ]\d{2}[-/ ]\d{4})", block, re.IGNORECASE)
    return clean_value(match.group(1)) if match else None


def _extract_amount(block: str) -> float:
    """Extracts the amount with progressive fallback."""
    # Try known labels in priority order
    labels = [
        r"[Ii]mporte\s*(?:a\s+)?[Ll]iquidar[:\s]*",
        r"[Cc]ontra?valor[:\s]*",
        r"[Ii]mporte\s+ordenado[:\s]*",
        r"[Ii]mporte[:\s]*",
    ]

    for label in labels:
        match = re.search(rf"{label}(-?[\d.,]+)\s*EUR?", block, re.IGNORECASE)
        if match:
            value_raw = match.group(1).replace(" ", "").replace(",", ".")
            # Handle European format with dots as thousands separator
            if value_raw.count(".") > 1:
                value_raw = value_raw.replace(".", "", value_raw.count(".") - 1)
            try:
                return float(value_raw)
            except ValueError:
                continue

    # Fallback: search for pattern "XXX,XX EUR" near BENEFICIARY
    match = re.search(
        r"BENEFICIARIO.*?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*EUR", block, re.IGNORECASE | re.DOTALL
    )
    if match:
        value_raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value_raw)
        except ValueError:
            pass

    return 0.0


def _extract_orderer_iban(block: str) -> str:
    """Extracts the orderer IBAN (Cuenta:)."""
    match = re.search(r"Cuenta:\s*(ES\d{2}[\d\s*]{16,24})", block, re.IGNORECASE)
    if match:
        return clean_value(match.group(1).replace(" ", "").replace("*", ""))
    return "unknown"


def _extract_beneficiary_iban(block: str) -> str:
    """Extracts the beneficiary IBAN."""
    match = re.search(r"IBAN[:\s]*(ES\d{2}[\d\s]{16,24})", block, re.IGNORECASE)
    if match:
        return clean_value(match.group(1).replace(" ", ""))
    return "unknown"


def _extract_orderer(block: str) -> str:
    """Extracts the orderer name."""
    match = re.search(r"ORDENANTE\s*\n?\s*(.+?)\s*\n", block, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        # Clean if contains AMOUNT or other fields
        name = re.split(r"\s+(IMPORTE|BENEFICIARIO|\d)", name)[0]
        if len(name) > 3:
            return clean_value(name)

    # Alternative: search for "Titular:"
    match = re.search(r"Titular[:\s]+([A-Z\s]+?)(?:\s+Importe|\s+Tipo|\n)", block, re.IGNORECASE)
    if match:
        return clean_value(match.group(1))

    return "unknown"


def _extract_beneficiary(block: str) -> str:
    """Extracts the beneficiary name."""
    # Pattern 1: "Ultimo Beneficiario:" or OCR variants - capture until next field
    match = re.search(
        r"[UÚ]ltimo?\s+Beneficiari[oa][:\s]+([A-Z][A-Z\s]+?)(?:\s*\n|\s+CONCEPTO|\s+Contravalor|\s+Tipo)",
        block,
        re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip()
        # Clean if captured extra text
        name = re.split(r"\s+(CONCEPTO|Contravalor|Tipo|GASTOS)", name, flags=re.IGNORECASE)[0]
        if len(name) > 2:
            return clean_value(name)

    # Pattern 2: After "BENEFICIARIO" in the header
    match = re.search(r"BENEFICIARIO\s*\n?\s*(.+?)\s*\n", block, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        name = re.split(r"\s+(\d|POR CUENTA|Importe)", name)[0]
        if len(name) > 3:
            return clean_value(name)

    return "unknown"


def _extract_concept(block: str) -> str:
    """Extracts the transfer concept."""
    # Pattern 1: CONCEPT: followed by text until end of block or next field
    match = re.search(
        r"CONCEPTO[:\s]+(.+?)(?:\s*Nuestra|\s*Fecha\s+operaci|\s*Oficina|\s*$)",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        concept = match.group(1).strip()
        # Clean line breaks and extra spaces
        concept = re.sub(r"\s+", " ", concept)
        # Remove fields that might slip in
        concept = re.split(
            r"(Nuestra|Fecha operaci|referencia:|Oficina)", concept, flags=re.IGNORECASE
        )[0]
        concept = concept.strip()
        if is_valid_concept(concept):
            return clean_value(concept)

    return "Document without concept"


def _extract_reference(block: str) -> str | None:
    """Extracts the transfer reference."""
    match = re.search(r"Nuestra\s+referencia[:\s]+(\w+)", block, re.IGNORECASE)
    return match.group(1) if match else None


def extract_transfers(text: str) -> list[DocumentoProcesado]:
    text = correct_ocr_errors(text)
    blocks = split_transfer_blocks(text)
    print(f"[INFO] TOTAL BLOCKS DETECTED: {len(blocks)}")

    results: list[DocumentoProcesado] = []

    for i, block in enumerate(blocks):
        print(f"\n--- BLOCK {i + 1} ---")
        print(block[:500])
        try:
            date = _extract_send_date(block)
            amount = _extract_amount(block)
            orderer_iban = _extract_orderer_iban(block)
            beneficiary_iban = _extract_beneficiary_iban(block)
            beneficiary = _extract_beneficiary(block)
            concept = _extract_concept(block)
            reference = _extract_reference(block)

            # Use beneficiary IBAN as main account
            account = beneficiary_iban if beneficiary_iban != "unknown" else orderer_iban

            results.append(
                DocumentoProcesado(
                    fecha=date,
                    concepto=concept,
                    tipo="gasto",
                    importe=amount,
                    cuenta=account,
                    categoria="otros",
                    cliente=beneficiary,
                    invoice=reference,
                    documentoTipo="transfer",
                    origen="ocr",
                )
            )
        except re.error as rex:
            print(f"[ERROR] Regex error in extract_transfers: {rex}")
            continue
        except Exception as e:
            print(f"[ERROR] Error in block {i + 1}: {e}")
            continue

    return results
