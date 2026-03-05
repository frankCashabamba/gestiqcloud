import hashlib
import json
import re
import unicodedata
from datetime import date
from typing import Literal

# Global patterns
DATE_PATTERNS = [
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
    r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",
    r"(?:\d{1,2})\s*(?:de)?\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s*\d{4}",
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    r"Date (of issue|paid)?[:\-]?\s*(\w+\s+\d{1,2},?\s+\d{4})",
    r"Fecha (de emisiÃ³n|valor|de la operaciÃ³n)?[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",
]

INVOICE_NUMBER_PATTERNS = [
    r"(?:Factura|Invoice|Receipt)[^\w]?\s*(?:N[Âºo]?)?\s*[:\-]?\s*(\w[\w\-/]*)",
    r"Invoice number\s*[:\-]?\s*(\w[\w\-/]*)",
    r"Receipt number\s*[:\-]?\s*(\w[\w\-/]*)",
    r"\bN[Âºo]?\s*[:\-]?\s*(\w[\w\-/]*)",
]

AMOUNT_PATTERNS = [
    r"Total\s*[:\-]?\s*(\$|â‚¬|usd|eur|mxn|cop)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"Total amount\s*(due)?\s*[:\-]?\s*(\$|â‚¬)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"Amount (due|paid)?\s*[:\-]?\s*(\$|â‚¬)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"Importe\s*(total|ordenado)?\s*[:\-]?\s*(\$|â‚¬)?\s*(-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"CUOTA.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
]

SUBTOTAL_PATTERNS = [
    r"Subtotal\s*[:\-]?\s*(\$|â‚¬|usd|eur|mxn|cop)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
    r"\b(\$|â‚¬|usd|eur|mxn|cop)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+Subtotal\b",
]

TAX_ID_PATTERNS = [
    # Ecuador / LATAM
    r"\bRUC\s*[:\-]?\s*(\d{13})\b",
    r"\bNIF[:\-]?\s*([A-Z0-9]{8,10})",
    r"\bVAT\s*(Number|No)?[:\-]?\s*([A-Z0-9]+)",
    r"\bCIF[:\-]?\s*([A-Z0-9]{8,10})",
    r"(\b[A-Z]\d{7}[A-Z]?\b)",
]

DECIMAL_NUMBERS = r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})"


# Utilities
def search(pattern: str, text: str, group: int = 0) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    try:
        return match.group(group).strip()
    except IndexError:
        return match.group(0).strip()


def search_multiple(patterns: list[str], text: str, group: int = 1) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.lastindex:  # Has groups
                try:
                    return match.group(group).strip()
                except IndexError:
                    continue
            else:
                if group == 0:
                    return match.group(0).strip()
                else:
                    continue  # If expecting group 1 but none exists, try next pattern
    return None


# Document type
DocumentType = Literal[
    "invoice",
    "receipt",
    "transfer",
    "pos_ticket",
    "payroll",
    "budget",
    "contract",
    "unknown",
]


def detect_document_type(text: str) -> DocumentType:
    def normalize(t: str) -> str:
        t = unicodedata.normalize("NFD", t)
        return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()

    text = normalize(text)

    def has(patterns: list[str]) -> bool:
        return any(re.search(p, text) for p in patterns)

    pos_ticket_patterns = [
        r"ticket de venta",
        r"ticket venta",
        r"n[ÂºoÂ°]?\s*r[-\s]*\d+",
        r"gracias por su compra",
        r"gracias por tu compra",
        r"estado:\s*paid",
        r"\d+[.,]?\d*\s*x\s+.+\s*[-â€“]\s*\$?\s*\d",
    ]
    receipt_patterns = [
        r"recibo",
        r"recib[oi]",
        r"reciec",
        r"receipt",
        r"recept",
        r"paid on",
        r"amount paid",
        r"payment history",
        r"payment received",
        r"thank you for your payment",
        r"visa",
        r"mastercard",
        r"paypal",
    ]
    transfer_patterns = [
        r"iban",
        r"swift",
        r"beneficiario",
        r"orden de transferencia",
        r"transferencia[s]? (emitidas|realizadas|completadas)",
        r"referencia de pago",
        r"transfer completed",
    ]
    invoice_patterns = [
        r"invoice",
        r"billing period",
        r"net amount",
        r"tax",
        r"vat",
        r"amount due",
        r"date of issue",
        r"subtotal",
        r"fecha de emision",
        r"nif",
        r"cif",
    ]
    payroll_patterns = [
        r"nomina",
        r"salario",
        r"sueldo",
        r"cotizaciones",
        r"seguridad social",
        r"retenciones irpf",
        r"base imponible",
        r"periodo de liquidacion",
    ]
    budget_patterns = [
        r"presupuesto",
        r"cotizacion",
        r"estimado",
        r"estimacion de costos",
        r"propuesta economica",
        r"valor aproximado",
    ]
    contract_patterns = [
        r"contrato",
        r"las partes acuerdan",
        r"vigencia",
        r"clausula",
        r"firmado por",
        r"obligaciones",
        r"rescision",
    ]

    if has(pos_ticket_patterns):
        return "pos_ticket"
    if has(receipt_patterns):
        return "receipt"
    if has(transfer_patterns):
        return "transfer"
    if has(invoice_patterns):
        return "invoice"
    if has(payroll_patterns):
        return "payroll"
    if has(budget_patterns):
        return "budget"
    if has(contract_patterns):
        return "contract"

    return "unknown"


# Extractors
def search_date(text: str) -> str | None:
    # 1) ISO date
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # 2) Numeric date dd/mm/yyyy or dd-mm-yyyy
    m = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # 3) Textual date in Spanish/English: "viernes, 16 de enero de 2026"
    month_map = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    m = re.search(
        r"\b(?:lunes|martes|miercoles|miÃ©rcoles|jueves|viernes|sabado|sÃ¡bado|domingo|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)?\s*,?\s*"
        r"(\d{1,2})\s+de\s+([a-zA-ZÃ¡Ã©Ã­Ã³ÃºÃÃ‰ÃÃ“ÃšÃ±Ã‘]+)\s+(?:de\s+)?(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        day = int(m.group(1))
        month_token = m.group(2).strip().lower()
        year = int(m.group(3))
        month = month_map.get(month_token)
        if month:
            try:
                return date(year, month, day).isoformat()
            except Exception:
                pass

    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                # Prefer groups that look like dates; avoid returning only month token.
                for token in reversed(match):
                    token_str = str(token).strip()
                    if re.search(r"\d{1,4}", token_str):
                        return token_str
                continue
            value = str(match).strip()
            if value:
                return value
    return None


def search_invoice_number(text: str) -> str | None:
    # Prefer strict invoice number formats first (avoid false positives like "mbres").
    t = " ".join((text or "").split())
    strong_patterns = [
        # Common LATAM/EC format: 001-001-000120085
        r"FACTURA\s*[:\-]?\s*(\d{3}\s*-\s*\d{3}\s*-\s*\d{6,12})",
        r"Factura\s*[:\-]?\s*(\d{3}\s*-\s*\d{3}\s*-\s*\d{6,12})",
        r"(?:No\.?|N[Âºo]?)\s*[:\-]?\s*(\d{3}\s*-\s*\d{3}\s*-\s*\d{6,12})",
        # Fallback: any 3-3-6+ digit pattern without explicit label
        r"\b(\d{3}\s*-\s*\d{3}\s*-\s*\d{6,12})\b",
        # Some OCRs drop hyphens/spaces: 001001000120085
        r"\b(\d{3}\s*\d{3}\s*\d{6,12})\b",
    ]
    for p in strong_patterns:
        m = re.search(p, t, flags=re.IGNORECASE)
        if not m:
            continue
        cand = m.group(1)
        cand = re.sub(r"\s*", "", cand)
        # Normalize 001001000120085 -> 001-001-000120085 when possible
        digits = re.sub(r"\D", "", cand)
        if len(digits) >= 12:
            cand = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        # Must contain enough digits to be a real invoice id
        if len(re.sub(r"\D", "", cand)) >= 10:
            return cand

    # Legacy heuristic fallback, but reject candidates that aren't number-like.
    cand = search_multiple(INVOICE_NUMBER_PATTERNS, text)
    if not cand:
        return None
    # Reject short alpha tokens.
    if re.fullmatch(r"[A-Za-z]{1,8}", cand or ""):
        return None
    # Require at least 6 digits somewhere.
    if len(re.findall(r"\d", cand)) < 6:
        return None
    return cand


def search_amount(text: str) -> str | None:
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            for group in match.groups():
                if group and re.match(DECIMAL_NUMBERS, group):
                    return group.replace(",", ".")
    return None


def search_subtotal(text: str) -> str | None:
    try:
        return search_multiple(SUBTOTAL_PATTERNS, text, group=1)
    except Exception as e:
        print("Error searching for subtotal:", e)
        return None


def search_largest_number(text: str) -> str | None:
    numbers = re.findall(DECIMAL_NUMBERS, text)
    values = [float(num.replace(",", ".")) for num in numbers if float(num.replace(",", ".")) > 0]
    return f"{max(values):.2f}" if values else None


def search_tax_id(text: str) -> str | None:
    # Prefer explicit RUC (EC) when present
    m = re.search(r"\bRUC\s*[:\-]?\s*(\d{13})\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    invoice_number = search_invoice_number(text)
    matches = re.findall(r"\b[A-Z]\d{7}[A-Z]?\b", text)
    for match in matches:
        if not invoice_number or match not in invoice_number:
            return match
    return search_multiple(TAX_ID_PATTERNS, text, group=-1)


def find_tax_id(text: str) -> str | None:
    """
    Convenience wrapper used by OCR extractors to obtain CIF/NIF/VAT IDs.
    Prefer this English name; kept separate from search_tax_id for clarity.
    """
    return search_tax_id(text)


def search_concept(text: str) -> str | None:
    match = re.search(r"(?i)concepto[:\-]?\s*(.+?)(?=\s+[A-Z][a-z]+\s*:|$)", text)
    return match.group(1).strip() if match else None


def search_description(text: str) -> str | None:
    match = re.search(r"(?i)description[:\-]?\s*(.+?)(?=\s+[A-Z][a-z]+\s*:|$)", text)
    if match:
        return match.group(1).strip()
    possible = re.findall(
        r"(ALQUILER|SERVICIO|PAGO|RENTA|SUSCRIPCIÃ“N|LICENSE|MONTHLY)",
        text,
        re.IGNORECASE,
    )
    return possible[0] if possible else None


def extract_block(lines: list[str], index: int) -> str:
    block = [lines[index].split(":", 1)[-1].strip()]
    for j in range(index + 1, min(index + 4, len(lines))):
        if not re.match(r"^\s*\w+\s*[:\-]", lines[j]):
            block.append(lines[j].strip())
        else:
            break
    return " ".join(block)


def search_issuer(text: str) -> str | None:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(
            r"^\s*(From|Issued by|Vendor|Seller|Company name)\b[:\-]?",
            line,
            re.IGNORECASE,
        ):
            return clean_company_name(extract_block(lines, i))
    # Heuristic for EC invoices: vendor name usually appears near the top, close to RUC.
    # Try: take the nearest plausible company line above the first "RUC".
    for i, line in enumerate(lines):
        if re.search(r"\bRUC\b", line, re.IGNORECASE):
            # Scan a few lines above for a strong company-name candidate.
            for j in range(max(0, i - 6), i)[::-1]:
                cand = lines[j].strip()
                if not cand or len(cand) < 6:
                    continue
                # Prefer corporate suffixes and mostly-uppercase lines.
                if re.search(
                    r"\b(S\.A\.|S\.A|CIA\.|CÃA\.|LTDA\.|LTD\.|INC\.|CORP\.|C\.A\.)\b",
                    cand,
                    re.IGNORECASE,
                ):
                    return clean_company_name(cand)
                upper_ratio = sum(1 for ch in cand if ch.isupper()) / max(len(cand), 1)
                if upper_ratio >= 0.7 and re.search(r"[A-Z]{4,}", cand):
                    return clean_company_name(cand)
            break
    # Fallback: first strong uppercase company-like line
    for line in lines[:25]:
        cand = line.strip()
        if len(cand) < 8:
            continue
        if re.search(r"\b(S\.A\.|S\.A|LTDA\.|INC\.|CORP\.)\b", cand, re.IGNORECASE):
            return clean_company_name(cand)
    return None


def search_client(text: str) -> str | None:
    lines = text.splitlines()
    # Common labeled formats
    for i, line in enumerate(lines):
        if re.search(r"^\s*(To|Bill to|Para|Destinatario|Cliente)\b[:\-]?", line, re.IGNORECASE):
            return clean_value(extract_block(lines, i))

    # Ecuador-style invoices often contain a client block like:
    # DATOS DEL CLIENTE: / RAZON SOCIAL ... then the client name on next line
    for i, line in enumerate(lines):
        if re.search(r"DATOS\s+DEL\s+CLIENTE", line, re.IGNORECASE) or re.search(
            r"RAZON\s+SOCIAL", line, re.IGNORECASE
        ):
            # Sometimes the name is on the same line after a colon
            m = re.search(r"[:\-]\s*(.+)$", line)
            if m and len(m.group(1).strip()) >= 4:
                return clean_value(m.group(1).strip())
            for j in range(i + 1, min(i + 7, len(lines))):
                cand = lines[j].strip()
                if not cand or len(cand) < 4:
                    continue
                # Skip label-only rows
                if re.search(
                    r"^(RUC|CI|C\.?I\.?|CEDULA|DIRECCION|TEL(EFONO)?|EMAIL|FECHA)\b",
                    cand,
                    re.IGNORECASE,
                ):
                    continue
                if re.search(r"RAZON\s+SOCIAL", cand, re.IGNORECASE):
                    continue
                return clean_value(cand)

    return None


def clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s@.,:/()-]", "", value)
    return value.strip()[:120]


def clean_company_name(value: str) -> str:
    """Clean a vendor/company string extracted from OCR."""
    v = clean_value(value or "")
    # Drop ISO timestamps sometimes injected by OCR or pipelines
    v = re.sub(r"\b20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[-+]\d{2}:\d{2})?\b", "", v)
    # Drop long numeric runs (barcodes / authorization codes)
    v = re.sub(r"\b\d{10,}\b", "", v)
    # Drop common invoice header tokens
    v = re.sub(
        r"\b(FACTURA|INVOICE|NUMERO|AUTORIZACION|FECHA|EMISION|PRODUCCION|AMBIENTE)\b[:\-]?",
        "",
        v,
        flags=re.IGNORECASE,
    )
    v = re.sub(r"\s{2,}", " ", v).strip(" -:/")
    return v[:120] if v else clean_value(value)


def correct_ocr_errors(text: str) -> str:
    replacements = {
        r"CONCERTO": "CONCEPTO",
        r"CONCEPTO[:;]?": "CONCEPTO:",
        r"FERHA|FECHA d2": "FECHA",
        r"Yaldr": "valor",
        r"env[oÃ³@]": "envÃ­o",
        r"operacicn|operacidn|operaciin|operarifn": "operaciÃ³n",
        r"Drdenado|Ordenadoc": "ordenado",
        r"@lqvidar|Mquidar|Gquidar|a Mquidar": "a liquidar",
        r"Contsalr|Contrzvalr|Contisvalor|Contisvalor:": "contravalor",
        r"Guenta|Cuenla|Cue": "cuenta",
        r"TITLLAR|Oltimo Beneficiarioc|Ultimd Beneficiario": "titular",
        r"GASTOSPORGVENTA|GAsTOSPORCVENTADe|GasTOS PORCVENTA|GASTOS POR CVENTA": "GASTOS POR CUENTA DE",
        r"ALQULER|ALOULER|ALQUILER HES": "ALQUILER MES",
        r"Nuesta|Nuestra|Nvestra": "Nuestra",
        r"feferencia|relerecia|referencia": "referencia",
        r"Imfone|Impone|iMporte": "Importe",
        r"liqidar|liquidr|bquidar": "liquidar",
        r"fecho": "fecha",
    }
    for error, fix in replacements.items():
        text = re.sub(error, fix, text, flags=re.IGNORECASE)
    return text


def is_valid_concept(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return False
    text_upper = text.upper()
    if any(
        p in text_upper
        for p in [
            "IBAN",
            "CUENTA",
            "ENTIDAD",
            "BENEFICIARIO",
            "TITULAR",
            "TIPO OPERACION",
        ]
    ):
        return False
    return True


def split_transfer_blocks(text: str) -> list[str]:
    """
    Splits text into blocks based on transfer headers.
    Detects typical Santander patterns: "Oficina:" followed by "TRANSFERENCIAS EMITIDAS".
    """
    text = correct_ocr_errors(text)

    # Main pattern: "Oficina:" indicates start of new transfer in Santander
    # Also detect "TRANSFERENCIAS EMITIDAS" as alternative separator
    separator_patterns = [
        r"(?=O[fl]icina:\s*\n?\s*Santander)",  # "Oficina:" with possible OCR error (l/f)
        r"(?=TRANSFERENCIAS\s+EMITIDAS\s*\n?\s*ORDEN\s+DE\s+TRANSFERENCIA)",
    ]

    # First try splitting by "Oficina:"
    office_pattern = separator_patterns[0]
    blocks = re.split(office_pattern, text, flags=re.IGNORECASE)
    blocks = [b.strip() for b in blocks if len(b.strip()) > 100]

    # If only one block, try the TRANSFERENCIAS EMITIDAS pattern
    if len(blocks) <= 1:
        transfers_pattern = separator_patterns[1]
        blocks = re.split(transfers_pattern, text, flags=re.IGNORECASE)
        blocks = [b.strip() for b in blocks if len(b.strip()) > 100]

    # Fallback: split by "Fecha de envÃ­o:" which appears at start of each transfer
    if len(blocks) <= 1:
        date_pattern = r"(?=Fecha\s+de\s+env[iÃ­]o:\s*\d{2}[-/ ]\d{2}[-/ ]\d{4})"
        blocks = re.split(date_pattern, text, flags=re.IGNORECASE)
        blocks = [b.strip() for b in blocks if len(b.strip()) > 100]

    print(f"[INFO] Blocks detected: {len(blocks)}")
    return blocks


def calculate_document_hash(tenant_id: int, data: dict) -> str:
    """
    Calculates a unique hash per company + document data.
    """
    relevant_data = {
        "tenant_id": tenant_id,
        "date": data.get("fecha"),
        "concept": data.get("concepto"),
        "amount": data.get("importe"),
        "client": data.get("cliente"),
        "type": data.get("documentoTipo"),  # Important if it varies
    }

    json_data = json.dumps(relevant_data, sort_keys=True)
    return hashlib.sha256(json_data.encode("utf-8")).hexdigest()
