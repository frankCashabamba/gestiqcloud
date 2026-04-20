from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image, ImageDraw

from app.modules.importador import ocr_service
from app.modules.importador.services.document_routing_agent import build_document_routing_decision

_IMPORT_DIR = Path(__file__).resolve().parents[4] / "importacion"


def test_ocr_image_skips_easyocr_fallback_when_tesseract_is_weak(monkeypatch):
    constructor_calls = {"count": 0}

    class FakeReader:
        def __init__(self, langs, gpu=False):
            constructor_calls["count"] += 1
            self.langs = langs
            self.gpu = gpu

        def readtext(self, _image):
            raise AssertionError("easyocr no deberia ejecutarse")

    monkeypatch.setitem(
        __import__("sys").modules, "easyocr", type("E", (), {"Reader": FakeReader})()
    )
    monkeypatch.setattr(ocr_service, "_run_tesseract", lambda variant, psm_modes=None: "...")
    ocr_service._EASYOCR_READERS.clear()

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._ocr_image(img)

    assert result == "..."
    assert constructor_calls["count"] == 0


def test_run_easyocr_reuses_reader_instance(monkeypatch):
    constructor_calls = {"count": 0}

    class FakeReader:
        def __init__(self, langs, gpu=False):
            constructor_calls["count"] += 1
            self.langs = langs
            self.gpu = gpu

        def readtext(self, _image):
            return [(None, "NOTA", 0.99)]

    ocr_service._EASYOCR_READERS.clear()
    monkeypatch.setitem(
        __import__("sys").modules, "easyocr", type("E", (), {"Reader": FakeReader})()
    )

    img = Image.new("L", (120, 80), color=255)

    assert ocr_service._run_easyocr(img) == "NOTA"
    assert ocr_service._run_easyocr(img) == "NOTA"
    assert constructor_calls["count"] == 1


def test_extract_csv_builds_virtual_sheet_context():
    result = ocr_service._extract_csv(b"fecha,total\n2026-04-01,12.5\n2026-04-02,8.0\n")

    assert result["format"] == "CSV"
    assert result["sheet_used"] == "CSV"
    assert result["structured_data"][0]["fecha"] == "2026-04-01"
    assert result["sheet_profiles"]["CSV"]["headers"] == ["fecha", "total"]
    assert result["sheet_profiles"]["CSV"]["rows_counted"] == 2


def test_extract_csv_sales_summary_promotes_routing_fields():
    path = _IMPORT_DIR / "Ventas_2026-02-21_2026-03-23.csv"
    result = ocr_service._extract_csv(path.read_bytes())

    assert result["format"] == "CSV"
    assert result["sheet_used"] == "CSV"
    assert len(result["structured_data"]) == 3

    metadata = result["sheet_metadata"]["CSV"]
    assert metadata["issue_date"] == "2026-03-22"
    assert abs(float(metadata["total_amount"]) - 158.04) < 0.01


def test_sales_csv_routes_without_review():
    path = _IMPORT_DIR / "Ventas_2026-02-21_2026-03-23.csv"
    result = ocr_service._extract_csv(path.read_bytes())
    metadata = result["sheet_metadata"]["CSV"]

    decision = build_document_routing_decision(
        source_doc_type="SALES",
        ai_confidence=0.72,
        extracted_data=metadata,
        canonical_document={"fields": metadata},
        category_keywords={},
        db=None,
        tenant_id=None,
    )

    assert decision.document_type == "sales_report"
    assert decision.suggested_destination == "expense"
    assert decision.required_fields_ok is True
    assert decision.needs_human_review is False


def test_extract_xml_ubl_builds_virtual_sheet_context():
    xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>F001-123</cbc:ID>
  <cbc:IssueDate>2026-04-01</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>Proveedor Demo</cbc:Name></cac:PartyName>
      <cac:PartyTaxScheme><cbc:CompanyID>0999999999001</cbc:CompanyID></cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:TaxTotal><cbc:TaxAmount>1.50</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount>10.00</cbc:TaxExclusiveAmount>
    <cbc:PayableAmount>11.50</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>"""

    result = ocr_service._extract_xml(xml_bytes)

    assert result["format"] == "XML_UBL"
    assert result["sheet_used"] == "XML"
    assert result["structured_data"][0]["documento"] == "F001-123"
    assert result["sheet_profiles"]["XML"]["headers"] == [
        "documento",
        "fecha",
        "moneda",
        "tipo_documento",
        "ruc",
        "proveedor",
        "subtotal",
        "monto",
        "igv",
    ]


def test_extract_xml_facturae_builds_structured_context():
    xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<Facturae xmlns="http://www.facturae.gob.es/formato">
  <Invoices>
    <Invoice>
      <InvoiceHeader>
        <InvoiceNumber>2024-001</InvoiceNumber>
        <InvoiceSeriesCode>A</InvoiceSeriesCode>
      </InvoiceHeader>
      <InvoiceIssueData>
        <IssueDate>2025-07-25</IssueDate>
      </InvoiceIssueData>
      <Items>
        <InvoiceLine>
          <ItemDescription>Harina</ItemDescription>
          <Quantity>1</Quantity>
          <UnitPriceWithoutTax>10.00</UnitPriceWithoutTax>
          <TotalAmountWithoutTax>10.00</TotalAmountWithoutTax>
          <TaxesOutputs>
            <Tax>
              <TaxRate>21</TaxRate>
              <TaxAmount><TotalAmount>2.10</TotalAmount></TaxAmount>
            </Tax>
          </TaxesOutputs>
        </InvoiceLine>
      </Items>
      <InvoiceTotals>
        <TotalGrossAmount>10.00</TotalGrossAmount>
      </InvoiceTotals>
    </Invoice>
  </Invoices>
</Facturae>
<Signature>
  <SignedInfo>MockSignatureInfo</SignedInfo>
</Signature>"""

    result = ocr_service._extract_xml(xml_bytes)

    assert result["format"] == "XML_FACTURAE"
    assert result["sheet_used"] == "XML"
    assert result["sheet_metadata"]["XML"]["documento"] == "2024-001 A"
    assert result["sheet_metadata"]["XML"]["fecha"] == "2025-07-25"
    assert result["structured_data"][0]["descripcion"] == "Harina"
    assert result["structured_data"][0]["total"] == "10.00"


def test_store_cached_extraction_skips_parse_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(ocr_service, "_ocr_cache_dir", lambda: tmp_path)

    file_bytes = b"<?xml version='1.0'?><Facturae></Facturae>"
    cache_path = ocr_service._ocr_cache_path(file_bytes)

    ocr_service._store_cached_extraction(
        file_bytes,
        {
            "text": "preview",
            "pages": 1,
            "structured_data": None,
            "format": "XML_PARSE_ERROR",
        },
    )

    assert not cache_path.exists()

    ocr_service._store_cached_extraction(
        file_bytes,
        {
            "text": "preview",
            "pages": 1,
            "structured_data": [{"documento": "2024-001 A"}],
            "format": "XML_FACTURAE",
        },
    )

    assert cache_path.exists()


def test_extract_text_from_file_rehydrates_cached_csv_context(monkeypatch, tmp_path):
    file_bytes = b"Fecha,Pedidos,Items,Total\n2026-03-22,11,268.000,$79.24\n"

    monkeypatch.setattr(ocr_service, "_ocr_cache_dir", lambda: tmp_path)
    cache_path = ocr_service._ocr_cache_path(file_bytes)
    cache_path.write_text(
        (
            '{"version":"'
            + ocr_service.OCR_EXTRACTION_CACHE_VERSION
            + '","text":"cached","pages":1,"structured_data":[{"Fecha":"2026-03-22","Pedidos":"11","Items":"268.000","Total":"$79.24"}],"format":"CSV"}'
        ),
        encoding="utf-8",
    )

    result = asyncio.run(
        ocr_service.extract_text_from_file(file_bytes, "Ventas_2026-02-21_2026-03-23.csv")
    )

    assert result["_cache_hit"] is True
    assert result["sheet_used"] == "CSV"
    assert result["sheet_profiles"]["CSV"]["headers"] == ["Fecha", "Pedidos", "Items", "Total"]


def test_ocr_image_uses_best_tesseract_variant_when_available(monkeypatch):
    def fake_tesseract(img, lang=None, config=None):
        variant = img.info.get("ocr_variant")
        if variant == "threshold":
            return "NOTA DE VENTA 10246538 TOTAL 5.30"
        return "..."

    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        type("P", (), {"image_to_string": staticmethod(fake_tesseract)})(),
    )

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result


def test_ocr_image_can_use_rotated_trimmed_variant(monkeypatch):
    def fake_tesseract(img, lang=None, config=None):
        variant = img.info.get("ocr_variant")
        if variant == "trimmed_rot90":
            return "NOTA DE VENTA 2048 TOTAL 5.30"
        return "..."

    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        type("P", (), {"image_to_string": staticmethod(fake_tesseract)})(),
    )

    img = Image.new("L", (240, 120), color=255)
    for x in range(60, 180):
        for y in range(20, 100):
            img.putpixel((x, y), 200)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result


def test_ocr_image_can_use_small_deskew_variant(monkeypatch):
    def fake_tesseract(img, lang=None, config=None):
        del lang, config
        variant = img.info.get("ocr_variant")
        if variant == "autocontrast_rot+2":
            return "NOTA DE VENTA CLIENTE DESCRIPCION TOTAL 5.30"
        return "..."

    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        type("P", (), {"image_to_string": staticmethod(fake_tesseract)})(),
    )

    img = Image.new("L", (160, 120), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result


def test_run_tesseract_tries_multiple_psm_configs(monkeypatch):
    calls: list[str | None] = []
    langs: list[str | None] = []

    def fake_tesseract(_img, lang=None, config=None):
        langs.append(lang)
        calls.append(config)
        if config == "--psm 11":
            return "FECHA CLIENTE NOTA DE VENTA DESCRIPCION VTOTAL 5.30"
        return ""

    monkeypatch.setattr(
        ocr_service,
        "_ocr_runtime_config",
        lambda: {
            "primary_psm_modes": ["6", "11"],
            "tesseract_languages": ["spa", "eng"],
            "weak_text_min_words": 4,
            "weak_text_min_chars": 24,
        },
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        type("P", (), {"image_to_string": staticmethod(fake_tesseract)})(),
    )

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._run_tesseract(img)

    assert result == "FECHA CLIENTE NOTA DE VENTA DESCRIPCION VTOTAL 5.30"
    assert calls == ["--psm 6", "--psm 11"]
    assert langs == ["spa+eng", "spa+eng"]


def test_run_easyocr_uses_runtime_gpu_flag(monkeypatch):
    seen_gpu: list[bool] = []

    class FakeReader:
        def __init__(self, langs, gpu=False):
            del langs
            seen_gpu.append(gpu)

        def readtext(self, _image):
            return [(None, "NOTA", 0.99)]

    ocr_service._EASYOCR_READERS.clear()
    monkeypatch.setattr(
        ocr_service,
        "_ocr_runtime_config",
        lambda: {
            "easyocr_languages": ["es", "en"],
            "easyocr_gpu": True,
        },
    )
    monkeypatch.setitem(
        __import__("sys").modules, "easyocr", type("E", (), {"Reader": FakeReader})()
    )

    img = Image.new("L", (120, 80), color=255)

    assert ocr_service._run_easyocr(img) == "NOTA"
    assert seen_gpu == [True]


def test_iter_small_rotations_uses_runtime_angles(monkeypatch):
    monkeypatch.setattr(
        ocr_service,
        "_ocr_runtime_config",
        lambda: {
            "small_rotation_angles": ["-1.5", "3"],
        },
    )

    img = Image.new("L", (120, 80), color=255)

    variants = ocr_service._iter_small_rotations(img, label_prefix="base")

    labels = [variant.info.get("ocr_variant") for variant in variants]
    assert labels == ["base_rot-2", "base_rot+3"]


def test_extract_pdf_prefers_embedded_text_when_quality_is_good(monkeypatch):
    pixmap_calls: list[int] = []

    class FakePage:
        def get_text(self, *args, **kwargs):
            return "Factura 001-2026-0001 Cliente RUC Total 5.30"

        def get_pixmap(self, dpi=300):
            pixmap_calls.append(dpi)
            raise AssertionError("OCR should not run for strong embedded text")

    class FakeDoc:
        def __iter__(self):
            yield FakePage()

        def __len__(self):
            return 1

        def close(self):
            return None

    class FakeFitz:
        @staticmethod
        def open(stream=None, filetype=None):
            del stream, filetype
            return FakeDoc()

    monkeypatch.setitem(__import__("sys").modules, "fitz", FakeFitz())
    monkeypatch.setattr(
        ocr_service,
        "_ocr_runtime_config",
        lambda: {
            "pdf_render_dpi": 240,
            "weak_text_min_words": 2,
            "weak_text_min_chars": 8,
            "ocr_min_quality": 0.45,
        },
    )
    monkeypatch.setattr(
        ocr_service,
        "_estimate_text_quality",
        lambda text, ocr_runtime=None: {"score": 0.95, "words": 20.0, "chars": float(len(text))},
    )

    result = asyncio.run(ocr_service._extract_pdf(b"%PDF-1.4 fake"))

    assert result["format"] == "PDF"
    assert result["text"] == "Factura 001-2026-0001 Cliente RUC Total 5.30"
    assert result["page_texts"] == ["Factura 001-2026-0001 Cliente RUC Total 5.30"]
    assert pixmap_calls == []


def test_extract_pdf_uses_multiple_dpi_candidates_when_embedded_text_is_weak(monkeypatch):
    dpi_calls: list[int] = []

    class FakePixmap:
        def __init__(self, width: int, height: int):
            self.width = width
            self.height = height
            self.samples = bytes([255, 255, 255] * width * height)

    class FakePage:
        def get_text(self, *args, **kwargs):
            return "borroso"

        def get_pixmap(self, dpi=300):
            dpi_calls.append(dpi)
            width = 2 if dpi < 300 else 4
            return FakePixmap(width, 2)

    class FakeDoc:
        def __iter__(self):
            yield FakePage()

        def __len__(self):
            return 1

        def close(self):
            return None

    class FakeFitz:
        @staticmethod
        def open(stream=None, filetype=None):
            del stream, filetype
            return FakeDoc()

    def fake_text_quality(text, ocr_runtime=None):
        del ocr_runtime
        if text == "borroso":
            return {"score": 0.05, "words": 1.0, "chars": float(len(text))}
        if "EXTRA" in text:
            return {"score": 0.95, "words": 7.0, "chars": float(len(text))}
        return {"score": 0.2, "words": 3.0, "chars": float(len(text))}

    monkeypatch.setitem(__import__("sys").modules, "fitz", FakeFitz())
    monkeypatch.setattr(
        ocr_service,
        "_ocr_runtime_config",
        lambda: {
            "pdf_render_dpi": 240,
            "weak_text_min_words": 2,
            "weak_text_min_chars": 8,
            "ocr_min_quality": 0.45,
        },
    )
    monkeypatch.setattr(ocr_service, "_estimate_text_quality", fake_text_quality)
    monkeypatch.setattr(
        ocr_service,
        "_ocr_image",
        lambda img: (
            "NOTA DE VENTA CLIENTE DESCRIPCION TOTAL 5.30 EXTRA"
            if img.width >= 4
            else "NOTA DE VENTA TOTAL 5.30"
        ),
    )

    result = asyncio.run(ocr_service._extract_pdf(b"%PDF-1.4 fake"))

    assert result["format"] == "PDF_OCR"
    assert dpi_calls == [240, 360]
    assert result["page_texts"] == ["NOTA DE VENTA CLIENTE DESCRIPCION TOTAL 5.30 EXTRA"]
    assert "EXTRA" in result["text"]


def test_extract_excel_uses_runtime_limits(monkeypatch):
    monkeypatch.setattr(
        ocr_service,
        "_ocr_runtime_config",
        lambda: {
            "excel_max_header_scan_rows": 2,
            "excel_max_preview_rows_per_sheet": 1,
            "excel_scan_rows_multiplier": 2,
            "excel_max_text_chars": 20,
        },
    )

    def fake_iter_xlsx_rows(_file_bytes):
        rows = iter(
            [
                ("titulo", None),
                ("SKU", "Descripcion"),
                ("A1", "Producto 1"),
                ("A2", "Producto 2"),
                ("A3", "Producto 3"),
            ]
        )
        yield "Hoja1", (5, 2), rows

    monkeypatch.setattr(ocr_service, "_iter_xlsx_rows", fake_iter_xlsx_rows)

    result = ocr_service._extract_excel(b"fake-xlsx")

    assert len(result["structured_data"]) == 1
    assert result["sheet_profiles"]["Hoja1"]["rows_counted"] == 2
    assert len(result["text"]) == 20


def test_extract_text_from_file_reuses_cached_extraction_by_hash(monkeypatch, tmp_path):
    calls = {"count": 0}

    async def fake_extract_image(_file_bytes: bytes):
        calls["count"] += 1
        return {
            "text": "NOTA DE VENTA CLIENTE DESCRIPCION TOTAL 5.30",
            "pages": 1,
            "structured_data": None,
            "format": "IMAGE_OCR",
            "vision_image_bytes": b"jpeg-preview",
        }

    monkeypatch.setattr(ocr_service, "_ocr_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(ocr_service, "_extract_image", fake_extract_image)

    file_bytes = b"fake-image-binary"

    first = asyncio.run(ocr_service.extract_text_from_file(file_bytes, "nota.jpeg"))
    second = asyncio.run(ocr_service.extract_text_from_file(file_bytes, "nota.jpeg"))

    assert calls["count"] == 1
    assert first["text"] == second["text"]
    assert second["vision_image_bytes"] == b"jpeg-preview"


def test_extract_text_from_file_does_not_cache_empty_extraction(monkeypatch, tmp_path):
    calls = {"count": 0}

    async def fake_extract_image(_file_bytes: bytes):
        calls["count"] += 1
        return {
            "text": "",
            "pages": 1,
            "structured_data": None,
            "format": "IMAGE_OCR",
        }

    monkeypatch.setattr(ocr_service, "_ocr_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(ocr_service, "_extract_image", fake_extract_image)

    file_bytes = b"fake-empty-image"

    first = asyncio.run(ocr_service.extract_text_from_file(file_bytes, "nota.jpeg"))
    second = asyncio.run(ocr_service.extract_text_from_file(file_bytes, "nota.jpeg"))

    assert first["text"] == ""
    assert second["text"] == ""
    assert calls["count"] == 2


def test_extract_text_from_file_bypasses_cache_when_requested(monkeypatch, tmp_path):
    calls = {"count": 0}

    async def fake_extract_image(_file_bytes: bytes):
        calls["count"] += 1
        return {
            "text": "OCR from bypass",
            "pages": 1,
            "structured_data": None,
            "format": "IMAGE_OCR",
        }

    monkeypatch.setattr(ocr_service, "_ocr_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(ocr_service, "_extract_image", fake_extract_image)

    file_bytes = b"fake-image-binary"

    first = asyncio.run(
        ocr_service.extract_text_from_file(file_bytes, "nota.jpeg", bypass_cache=True)
    )
    second = asyncio.run(
        ocr_service.extract_text_from_file(file_bytes, "nota.jpeg", bypass_cache=True)
    )

    assert calls["count"] == 2
    assert first["text"] == "OCR from bypass"
    assert second["text"] == "OCR from bypass"
    assert first["_cache_bypassed"] is True
    assert second["_cache_bypassed"] is True


def test_rectify_document_perspective_detects_skewed_document():
    img = Image.new("RGB", (400, 300), color=(25, 25, 25))
    draw = ImageDraw.Draw(img)
    draw.polygon(
        [(80, 40), (330, 25), (350, 255), (55, 275)],
        fill=(245, 245, 245),
        outline=(220, 220, 220),
    )

    rectified, changed = ocr_service._rectify_document_perspective(img)

    assert changed is True
    assert rectified.width >= 220
    assert rectified.height >= 180


def test_ocr_image_can_use_perspective_variant(monkeypatch):
    original = ocr_service._rectify_document_perspective

    def fake_rectify(img):
        rectified, _ = original(img)
        if rectified.size == img.size:
            rectified = img.resize((img.width - 20, img.height - 10))
        return rectified, True

    def fake_tesseract(img, lang=None, config=None):
        del lang, config
        variant = img.info.get("ocr_variant")
        if variant == "perspective":
            return "NOTA DE VENTA DESCRIPCION TOTAL 5.30"
        return "..."

    monkeypatch.setattr(ocr_service, "_rectify_document_perspective", fake_rectify)
    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        type("P", (), {"image_to_string": staticmethod(fake_tesseract)})(),
    )

    img = Image.new("L", (160, 120), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result
