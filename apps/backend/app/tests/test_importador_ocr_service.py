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

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(lambda img, lang=None, config=None: "...")
    })())
    monkeypatch.setitem(__import__("sys").modules, "easyocr", type("E", (), {
        "Reader": FakeReader
    })())

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result


def test_ocr_image_uses_best_tesseract_variant_when_available(monkeypatch):
    def fake_tesseract(img, lang=None, config=None):
        variant = img.info.get("ocr_variant")
        if variant == "threshold":
            return "NOTA DE VENTA 10246538 TOTAL 5.30"
        return "..."

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(fake_tesseract)
    })())

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

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(fake_tesseract)
    })())

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

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(fake_tesseract)
    })())

    img = Image.new("L", (160, 120), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result


def test_run_tesseract_tries_multiple_psm_configs(monkeypatch):
    calls: list[str | None] = []

    def fake_tesseract(_img, lang=None, config=None):
        del lang
        calls.append(config)
        if config == "--psm 11":
            return "FECHA CLIENTE NOTA DE VENTA DESCRIPCION VTOTAL 5.30"
        return ""

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(fake_tesseract)
    })())

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._run_tesseract(img)

    assert result == "FECHA CLIENTE NOTA DE VENTA DESCRIPCION VTOTAL 5.30"
    assert calls == ["--psm 6", "--psm 11"]


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
    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(fake_tesseract)
    })())

    img = Image.new("L", (160, 120), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result
