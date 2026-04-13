"""Tests de integración real con documentos de ejemplo.

Cubren la cadena completa de extracción sin IA:
  1. invoice_rescue_from_ocr  → regex heurísticos sobre texto OCR
  2. extract_fields_from_text → extractor por etiquetas configurado con specs mínimos

Documentos usados:
  - factura_proveedor_stock_alto_insumos.pdf  (PDF texto, 3 páginas, 55 ítems, $16,567.49)
  - 08122025.pdf                              (PDF vectorial — se usa OCR simulado de Tesseract)
  - Molinos Miraflores                        (foto de factura — OCR simulado)

Estrategia:
  - Para el PDF de texto se usa fitz (PyMuPDF) para extraer el texto real del PDF.
  - Para documentos sin texto embebido se usa un string fixture que simula la salida
    típica de Tesseract para ese documento (el texto fue verificado manualmente contra
    el documento original).
  - Ningún test requiere base de datos ni conexión a la IA.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from app.modules.importador.invoice_ocr_rescue import (
    invoice_rescue_from_ocr,
    _rescue_vendor,
    _rescue_doc_number,
    _rescue_amounts,
)
from app.modules.importador.text_fallback_extractor import extract_fields_from_text

# ── Rutas a los documentos reales ─────────────────────────────────────────────

_IMPORT_DIR = pathlib.Path(__file__).parents[4] / "importacion"

# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_pdf_text(path: pathlib.Path) -> str:
    """Extrae texto de un PDF usando PyMuPDF. Devuelve '' si falla o no hay texto."""
    try:
        import fitz  # type: ignore[import]

        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def _pdf_available(path: pathlib.Path) -> bool:
    return path.exists()


# ── Texto del PDF de factura de proveedor (extraído del PDF real) ──────────────

@pytest.fixture(scope="module")
def factura_pdf_text() -> str:
    path = _IMPORT_DIR / "factura_proveedor_stock_alto_insumos.pdf"
    text = _extract_pdf_text(path) if _pdf_available(path) else ""
    if not text.strip():
        pytest.skip("factura_proveedor_stock_alto_insumos.pdf no disponible o sin texto embebido")
    return text


# ── OCR simulado para 08122025.pdf  ───────────────────────────────────────────
# El archivo es un PDF vectorial producido por "Microsoft: Print To PDF".
# El texto de abajo reproduce lo que Tesseract extrae de la imagen renderizada.

_TICKET_OCR_TEXT = """
TICKET DE VENTA
Fecha: 08/12/2025
N° R-0013

Descripcion          Cant    Precio
tapados              10.00   0.15

Subtotal             1.50
TOTAL                $ 1.50

Gracias por su compra
""".strip()


# ── OCR simulado para foto Molinos Miraflores ──────────────────────────────────

_MOLINOS_OCR_TEXT = """
MOLINOS MIRAFLORES S.A.
RUC: 1890004195001
Factura: 001-001-000120085
Fecha: 15/03/2026

Cliente: Retail Reposteria y Bazar Central
RUC Cliente: 0998754231001

Descripcion          Cant    P.Unit    Total
Harina especial kg   500     2.85      1425.00
Harina integral kg   200     3.60       720.00

Subtotal: 2145.00
IVA 0%: 0.00
Total a pagar: 2145.00
""".strip()


# ══════════════════════════════════════════════════════════════════════════════
# Specs mínimos para extract_fields_from_text (sin base de datos)
# ══════════════════════════════════════════════════════════════════════════════

_CANONICAL_FIELDS_MINIMAL: dict[str, dict] = {
    "vendor":         {"type": "text"},
    "vendor_tax_id":  {"type": "text"},
    "doc_number":     {"type": "text"},
    "issue_date":     {"type": "date"},
    "total_amount":   {"type": "numeric"},
    "subtotal":       {"type": "numeric"},
    "tax_amount":     {"type": "numeric"},
}

_FIELD_ALIASES_MINIMAL: dict[str, list[str]] = {
    "vendor":         ["proveedor", "empresa", "razon social"],
    "vendor_tax_id":  ["RUC", "NIT", "CIF"],
    "doc_number":     ["factura no", "factura no.", "N° factura", "No. factura", "No.", "N°"],
    "issue_date":     ["fecha de emision", "fecha emision", "fecha"],
    "total_amount":   ["total", "total a pagar", "importe total", "valor total"],
    "subtotal":       ["subtotal", "sub total", "base imponible"],
    "tax_amount":     ["IVA", "impuesto", "IVA 12%"],
}

_AMOUNT_LABELS_MINIMAL: dict[str, list[str]] = {
    "total_amount":   ["total", "total a pagar", "valor total"],
    "subtotal":       ["subtotal", "sub total"],
    "tax_amount":     ["IVA", "IVA 12%"],
}


# ══════════════════════════════════════════════════════════════════════════════
# Tests: factura de proveedor real (PDF texto)
# ══════════════════════════════════════════════════════════════════════════════

class TestFacturaProveedorRescue:
    """invoice_rescue_from_ocr sobre el texto extraído del PDF real."""

    @pytest.mark.no_db
    def test_texto_contiene_datos_clave(self, factura_pdf_text):
        """Verificación básica: el texto extraído incluye los datos esperados."""
        assert "FAC-2026-0487" in factura_pdf_text
        assert "1792845612001" in factura_pdf_text
        assert "16,567.49" in factura_pdf_text

    @pytest.mark.no_db
    def test_rescue_vendor_encuentra_distribuidora(self, factura_pdf_text):
        vendor = _rescue_vendor(factura_pdf_text)
        assert vendor is not None
        assert "Distribuidora" in vendor or "Integral Andina" in vendor

    @pytest.mark.no_db
    def test_rescue_doc_number_encuentra_fac(self, factura_pdf_text):
        doc_number = _rescue_doc_number(factura_pdf_text)
        assert doc_number == "FAC-2026-0487"

    @pytest.mark.no_db
    def test_rescue_amounts_subtotal(self, factura_pdf_text):
        amounts = _rescue_amounts(factura_pdf_text)
        assert "subtotal" in amounts
        assert abs(amounts["subtotal"] - 14792.40) < 1.0

    @pytest.mark.no_db
    def test_rescue_amounts_tax(self, factura_pdf_text):
        amounts = _rescue_amounts(factura_pdf_text)
        assert "tax_amount" in amounts
        assert abs(amounts["tax_amount"] - 1775.09) < 1.0

    @pytest.mark.no_db
    def test_invoice_rescue_completo(self, factura_pdf_text):
        """Llamada completa: debe encontrar vendor, doc_number, subtotal, tax_amount."""
        rescued = invoice_rescue_from_ocr(factura_pdf_text)
        assert rescued.get("vendor"), "vendor no encontrado"
        assert rescued.get("doc_number") == "FAC-2026-0487"
        assert "subtotal" in rescued
        assert "tax_amount" in rescued

    @pytest.mark.no_db
    def test_invoice_rescue_no_sobreescribe_campos_existentes(self, factura_pdf_text):
        """Si ya hay campos, rescue no los pisa."""
        existing = {"doc_number": "YA-EXISTE", "vendor": "Proveedor previo"}
        rescued = invoice_rescue_from_ocr(factura_pdf_text, existing)
        # doc_number y vendor no deben aparecer en rescued (ya existen)
        assert "doc_number" not in rescued
        assert "vendor" not in rescued

    @pytest.mark.no_db
    def test_texto_contiene_55_items(self, factura_pdf_text):
        """La factura tiene 55 líneas de producto — el texto debe reflejarlo."""
        assert "55 productos" in factura_pdf_text or "55" in factura_pdf_text


class TestFacturaProveedorExtractFields:
    """extract_fields_from_text sobre el texto real con specs mínimos."""

    @pytest.mark.no_db
    def test_extrae_total_amount(self, factura_pdf_text):
        result = extract_fields_from_text(
            factura_pdf_text,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        total = result.get("total_amount")
        assert total is not None, "total_amount no extraído"
        assert abs(float(total) - 16567.49) < 1.0, f"total_amount incorrecto: {total}"

    @pytest.mark.no_db
    def test_extrae_subtotal(self, factura_pdf_text):
        result = extract_fields_from_text(
            factura_pdf_text,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        subtotal = result.get("subtotal")
        assert subtotal is not None
        assert abs(float(subtotal) - 14792.40) < 1.0, f"subtotal incorrecto: {subtotal}"

    @pytest.mark.no_db
    def test_extrae_issue_date(self, factura_pdf_text):
        result = extract_fields_from_text(
            factura_pdf_text,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        date = result.get("issue_date")
        assert date is not None, "issue_date no extraída"
        # Fecha en el PDF: 03/04/2026 → esperamos 2026-04-03
        assert "2026" in str(date), f"año incorrecto en issue_date: {date}"

    @pytest.mark.no_db
    def test_pre_extraction_bypass_triggers(self, factura_pdf_text):
        """Simula la lógica del bypass pre-IA: con total + 2 campos más, se evita la IA."""
        result = extract_fields_from_text(
            factura_pdf_text,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        # Campos fuertes: total_amount, subtotal, tax_amount, issue_date → ≥ 3
        strong_fields = {
            k for k in ("total_amount", "subtotal", "tax_amount", "issue_date", "doc_number")
            if result.get(k) not in (None, "", [], {})
        }
        assert len(strong_fields) >= 3, (
            f"Solo se encontraron {len(strong_fields)} campos fuertes: {strong_fields}. "
            "El bypass pre-IA requiere al menos 3."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Tests: ticket 08122025 (OCR simulado)
# ══════════════════════════════════════════════════════════════════════════════

class TestTicketOCRSimulado:
    """invoice_rescue_from_ocr sobre texto simulado del ticket vectorial."""

    @pytest.mark.no_db
    def test_rescue_doc_number_r0013_no_encontrado(self):
        """R-0013 tiene un primer grupo de solo 1 caracter — el patrón requiere 3+.
        La función rescue devuelve None en este caso (comportamiento esperado).
        Documentos con números cortos como R-XXXX no los detecta el rescue.
        """
        doc_number = _rescue_doc_number(_TICKET_OCR_TEXT)
        assert doc_number is None

    @pytest.mark.no_db
    def test_rescue_amounts_subtotal_ticket(self):
        amounts = _rescue_amounts(_TICKET_OCR_TEXT)
        # El ticket tiene Subtotal 1.50 y TOTAL 1.50
        assert "subtotal" in amounts
        assert abs(amounts["subtotal"] - 1.50) < 0.01

    @pytest.mark.no_db
    def test_invoice_rescue_ticket_completo(self):
        rescued = invoice_rescue_from_ocr(_TICKET_OCR_TEXT)
        # doc_number no se encuentra (R-0013 tiene primer grupo de 1 char, necesita 3+)
        # subtotal sí se encuentra porque hay línea "Subtotal 1.50"
        assert "subtotal" in rescued
        assert abs(rescued["subtotal"] - 1.50) < 0.01

    @pytest.mark.no_db
    def test_extract_fields_ticket_total(self):
        result = extract_fields_from_text(
            _TICKET_OCR_TEXT,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        total = result.get("total_amount")
        assert total is not None, "total_amount no encontrado en ticket"
        # Con type='numeric' el extractor parsea el valor como float
        assert abs(float(total) - 1.50) < 0.01, f"total_amount incorrecto: {total}"

    @pytest.mark.no_db
    def test_extract_fields_ticket_issue_date(self):
        result = extract_fields_from_text(
            _TICKET_OCR_TEXT,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        date = result.get("issue_date")
        assert date is not None, "issue_date no extraída del ticket"
        assert "2025" in str(date), f"año incorrecto: {date}"


# ══════════════════════════════════════════════════════════════════════════════
# Tests: foto factura Molinos Miraflores (OCR simulado)
# ══════════════════════════════════════════════════════════════════════════════

class TestMolinosMirafloresOCR:
    """Tests sobre el texto OCR simulado de la foto de Molinos Miraflores."""

    @pytest.mark.no_db
    def test_rescue_vendor_molinos(self):
        vendor = _rescue_vendor(_MOLINOS_OCR_TEXT)
        assert vendor is not None
        assert "MOLINOS" in vendor or "MIRAFLORES" in vendor

    @pytest.mark.no_db
    def test_rescue_doc_number_factura_molinos(self):
        doc_number = _rescue_doc_number(_MOLINOS_OCR_TEXT)
        assert doc_number is not None
        # El número 001-001-000120085 tiene 15 dígitos (sin guiones = 15) → debería pasar
        assert "001-001-000120085" in doc_number or doc_number == "001-001-000120085"

    @pytest.mark.no_db
    def test_rescue_amounts_molinos(self):
        amounts = _rescue_amounts(_MOLINOS_OCR_TEXT)
        assert "subtotal" in amounts
        assert abs(amounts["subtotal"] - 2145.00) < 1.0

    @pytest.mark.no_db
    def test_extract_fields_molinos_total(self):
        result = extract_fields_from_text(
            _MOLINOS_OCR_TEXT,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        total = result.get("total_amount")
        assert total is not None, "total_amount no encontrado"
        assert abs(float(total) - 2145.00) < 1.0

    @pytest.mark.no_db
    def test_extract_fields_molinos_vendor_tax_id(self):
        result = extract_fields_from_text(
            _MOLINOS_OCR_TEXT,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        ruc = result.get("vendor_tax_id")
        assert ruc is not None, "vendor_tax_id (RUC) no extraído"
        assert "1890004195001" in str(ruc)

    @pytest.mark.no_db
    def test_extract_fields_molinos_issue_date(self):
        result = extract_fields_from_text(
            _MOLINOS_OCR_TEXT,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        date = result.get("issue_date")
        assert date is not None
        assert "2026" in str(date)

    @pytest.mark.no_db
    def test_pre_extraction_bypass_molinos(self):
        """Con 3 campos fuertes el bypass pre-IA debe activarse."""
        result = extract_fields_from_text(
            _MOLINOS_OCR_TEXT,
            _CANONICAL_FIELDS_MINIMAL,
            _FIELD_ALIASES_MINIMAL,
            _AMOUNT_LABELS_MINIMAL,
        )
        strong = {
            k for k in ("total_amount", "subtotal", "tax_amount", "issue_date", "vendor_tax_id")
            if result.get(k) not in (None, "", [], {})
        }
        assert len(strong) >= 3, (
            f"Solo {len(strong)} campos fuertes: {strong}. "
            "El bypass pre-IA requiere al menos 3."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Tests: archivo PDF real disponible en disco
# ══════════════════════════════════════════════════════════════════════════════

class TestPDFRealDisponibilidad:
    """Verificaciones básicas de que los archivos PDF existen y PyMuPDF puede abrirlos."""

    @pytest.mark.no_db
    def test_factura_pdf_existe(self):
        path = _IMPORT_DIR / "factura_proveedor_stock_alto_insumos.pdf"
        assert path.exists(), f"PDF de factura no encontrado en {path}"

    @pytest.mark.no_db
    def test_ticket_pdf_existe(self):
        path = _IMPORT_DIR / "08122025.pdf"
        assert path.exists(), f"PDF de ticket no encontrado en {path}"

    @pytest.mark.no_db
    def test_factura_pdf_pymupdf_extrae_texto(self):
        path = _IMPORT_DIR / "factura_proveedor_stock_alto_insumos.pdf"
        if not path.exists():
            pytest.skip("PDF no disponible")
        text = _extract_pdf_text(path)
        assert len(text) > 500, f"Texto extraído demasiado corto: {len(text)} chars"
        assert "FAC-2026-0487" in text

    @pytest.mark.no_db
    def test_ticket_pdf_es_vectorial_sin_texto(self):
        """El ticket 08122025.pdf es un PDF vectorial — PyMuPDF no extrae texto."""
        path = _IMPORT_DIR / "08122025.pdf"
        if not path.exists():
            pytest.skip("PDF no disponible")
        text = _extract_pdf_text(path)
        # El ticket no tiene texto embebido — solo gráficos vectoriales
        assert len(text.strip()) == 0, (
            f"Se esperaba 0 chars de texto (PDF vectorial), pero se extrajeron {len(text)} chars"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Tests: _rescue_doc_number — lógica del filtro de dígitos
# ══════════════════════════════════════════════════════════════════════════════

class TestRescueDocNumberFiltros:
    """Verifica que el filtro de longitud de dígitos no descarte números válidos."""

    @pytest.mark.no_db
    def test_fac_2026_0487_aceptado(self):
        text = "Factura No. FAC-2026-0487\nFecha: 03/04/2026"
        assert _rescue_doc_number(text) == "FAC-2026-0487"

    @pytest.mark.no_db
    def test_formato_ecuador_001_001_12_digitos_aceptado(self):
        """001-001-000120085 tiene 15 dígitos sin guiones → dentro del filtro 10-15."""
        text = "Factura: 001-001-000120085\nRUC: 1890004195001"
        result = _rescue_doc_number(text)
        assert result is not None
        assert "001-001-000120085" in result

    @pytest.mark.no_db
    def test_r_0013_no_detectado_primer_grupo_corto(self):
        """R-0013 no se detecta: el primer componente 'R' tiene solo 1 caracter.
        El patrón requiere [A-Z0-9]{3,} en el primer grupo (mínimo 3 caracteres).
        Formatos como 'R-XXXX' son demasiado cortos para el rescuedor regex.
        """
        text = "N° R-0013\nFecha: 08/12/2025"
        assert _rescue_doc_number(text) is None

    @pytest.mark.no_db
    def test_numero_cedula_pura_rechazado(self):
        """Un número de 10 dígitos sin guiones se rechaza por el filtro."""
        text = "No. 1792845612\nFecha: 01/01/2026"
        result = _rescue_doc_number(text)
        # No debe devolver el número de cédula puro (sin guiones, 10 dígitos)
        assert result is None or "-" in str(result)
