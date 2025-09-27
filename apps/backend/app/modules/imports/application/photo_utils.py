from __future__ import annotations

import hashlib
import os
import re
import uuid
from typing import Tuple, Dict, Any


def exif_auto_orienta(content: bytes) -> bytes:
    """Stub: return content unchanged. Hook EXIF auto-rotate here if needed."""
    return content


def guardar_adjunto_bytes(empresa_id: str | int, content: bytes, *, filename: str) -> Tuple[str, str]:
    """Persist attachment to local uploads folder and return (file_key, sha256)."""
    base_dir = os.path.join("uploads", "imports", str(empresa_id))
    os.makedirs(base_dir, exist_ok=True)
    ext = os.path.splitext(filename)[1] or ".bin"
    key = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(base_dir, key)
    with open(path, "wb") as f:
        f.write(content)
    sha = hashlib.sha256(content).hexdigest()
    file_key = f"imports/{empresa_id}/{key}"
    return file_key, sha


def ocr_texto(content: bytes) -> str:
    """Stub OCR: not performing real OCR in this environment."""
    return ""


# Very naive parsers from text to normalized dicts ---------------------------

def _find_date(text: str) -> str | None:
    # Accept ISO or dd/mm/yyyy
    m = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if m:
        return m.group(0)
    m = re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text)
    if m:
        return m.group(0)
    return None


def _find_amount(text: str) -> float | None:
    m = re.search(r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})", text)
    if not m:
        return None
    s = m.group(0).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def parse_texto_factura(text: str) -> Dict[str, Any]:
    inv = None
    m = re.search(r"(Invoice|Factura)\s*(Number|N[oº]?)?[:\-]?\s*([A-Za-z0-9\-/]+)", text, re.IGNORECASE)
    if m:
        inv = m.group(3)
    return {
        "invoice_number": inv,
        "invoice_date": _find_date(text),
        "total_amount": _find_amount(text),
    }


def parse_texto_banco(text: str) -> Dict[str, Any]:
    return {
        "transaction_date": _find_date(text),
        "amount": _find_amount(text),
        "description": (text[:120] if text else None),
    }


def parse_texto_recibo(text: str) -> Dict[str, Any]:
    return {
        "expense_date": _find_date(text),
        "amount": _find_amount(text),
        "description": (text[:120] if text else None),
    }

