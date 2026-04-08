from __future__ import annotations

import asyncio

from PIL import Image, ImageDraw

from app.modules.importador import ocr_service


def test_ocr_image_falls_back_to_easyocr_when_tesseract_is_weak(monkeypatch):
    class FakeReader:
        def __init__(self, langs, gpu=False):
            self.langs = langs
            self.gpu = gpu

        def readtext(self, _image):
            return [(None, "NOTA DE VENTA 10246538 TOTAL 5.30", 0.99)]

    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        type(
            "P", (), {"image_to_string": staticmethod(lambda img, lang=None, config=None: "...")}
        )(),
    )
    monkeypatch.setitem(
        __import__("sys").modules, "easyocr", type("E", (), {"Reader": FakeReader})()
    )

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result


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


def test_extract_pdf_uses_configured_dpi(monkeypatch):
    dpi_calls: list[int] = []

    class FakePixmap:
        width = 2
        height = 2
        samples = bytes([255, 255, 255] * 4)

    class FakePage:
        def get_text(self, *args, **kwargs):
            return ""

        def get_pixmap(self, dpi=300):
            dpi_calls.append(dpi)
            return FakePixmap()

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
    monkeypatch.setattr(ocr_service, "_ocr_runtime_config", lambda: {"pdf_render_dpi": 240})
    monkeypatch.setattr(ocr_service, "_ocr_image", lambda img: "OCR OK")

    result = asyncio.run(ocr_service._extract_pdf(b"%PDF-1.4 fake"))

    assert result["format"] == "PDF_OCR"
    assert dpi_calls == [240]


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
