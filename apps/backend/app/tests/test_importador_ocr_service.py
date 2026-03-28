from __future__ import annotations

from PIL import Image

from app.modules.importador import ocr_service


def test_ocr_image_falls_back_to_easyocr_when_tesseract_is_weak(monkeypatch):
    class FakeReader:
        def __init__(self, langs, gpu=False):
            self.langs = langs
            self.gpu = gpu

        def readtext(self, _image):
            return [(None, "NOTA DE VENTA 10246538 TOTAL 5.30", 0.99)]

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", type("P", (), {
        "image_to_string": staticmethod(lambda img, lang=None: "...")
    })())
    monkeypatch.setitem(__import__("sys").modules, "easyocr", type("E", (), {
        "Reader": FakeReader
    })())

    img = Image.new("L", (120, 80), color=255)

    result = ocr_service._ocr_image(img)

    assert "NOTA DE VENTA" in result
    assert "5.30" in result

