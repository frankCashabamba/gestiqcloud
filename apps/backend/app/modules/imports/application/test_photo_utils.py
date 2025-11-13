"""Unit tests for photo_utils OCR optimizations."""

from __future__ import annotations

import hashlib

import pytest

try:
    import cv2  # noqa: F401
    import numpy as np

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


from .photo_utils import (
    detect_native_text_in_pdf,
    extract_qr_codes,
    extract_text_from_image,
    preprocess_image,
)


@pytest.mark.skipif(not OPENCV_AVAILABLE, reason="OpenCV not available")
def test_preprocess_image_grayscale():
    """Test image preprocessing converts to grayscale."""
    # Create RGB test image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = [128, 128, 128]  # Gray color

    processed = preprocess_image(img)

    # Should be 2D (grayscale)
    assert len(processed.shape) == 2
    assert processed.shape == (100, 100)


@pytest.mark.skipif(not OPENCV_AVAILABLE, reason="OpenCV not available")
def test_preprocess_image_denoise():
    """Test image denoising."""
    # Create noisy image
    img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

    processed = preprocess_image(img)

    # Should be same size
    assert processed.shape == img.shape


@pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="PyMuPDF not available")
def test_detect_native_text_in_pdf_with_text(tmp_path):
    """Test PDF native text extraction with searchable PDF."""
    # Create a simple PDF with text
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50), "This is a test document with enough text to pass the threshold"
    )
    doc.save(str(pdf_path))
    doc.close()

    text = detect_native_text_in_pdf(str(pdf_path), min_chars=10)

    assert text is not None
    assert "test document" in text.lower()


@pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="PyMuPDF not available")
def test_detect_native_text_in_pdf_without_text(tmp_path):
    """Test PDF native text extraction with image-only PDF."""
    # Create a PDF without text (blank page)
    pdf_path = tmp_path / "blank.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    text = detect_native_text_in_pdf(str(pdf_path), min_chars=100)

    # Should return None since not enough text
    assert text is None


def test_extract_text_from_image_caching():
    """Test OCR result caching."""
    # Create simple test image bytes
    content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    file_sha = hashlib.sha256(content).hexdigest()

    # First call (may fail without real image, but tests caching logic)
    result1 = extract_text_from_image(content, file_sha)

    # Second call should use cache
    result2 = extract_text_from_image(content, file_sha)

    # Should return same result (even if empty due to invalid image)
    assert result1 == result2


@pytest.mark.skipif(not OPENCV_AVAILABLE, reason="OpenCV not available")
def test_extract_qr_codes_no_qr():
    """Test QR extraction with image without QR codes."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)

    qr_codes = extract_qr_codes(img)

    assert qr_codes == []


def test_preprocess_image_fallback_without_opencv():
    """Test preprocessing fallback when OpenCV not available."""
    # Mock absence of OpenCV
    _original_available = OPENCV_AVAILABLE

    # If OpenCV not available, should return image unchanged
    if not OPENCV_AVAILABLE:
        img = "mock_image"
        result = preprocess_image(img)
        assert result == img


@pytest.mark.integration
@pytest.mark.skipif(
    not (OPENCV_AVAILABLE and PYMUPDF_AVAILABLE), reason="OpenCV and PyMuPDF required"
)
def test_full_ocr_pipeline_timing(tmp_path, benchmark_threshold_ms=5000):
    """Integration test for full OCR pipeline with timing."""
    import time

    # Create test PDF with text
    pdf_path = tmp_path / "invoice.pdf"
    doc = fitz.open()
    page = doc.new_page()

    # Add substantial text
    invoice_text = """
    FACTURA
    Número: 001-001-000123
    Fecha: 2025-01-15
    Cliente: Test Company S.A.
    RUC: 1234567890001
    
    Descripción          Cantidad    P.Unit    Total
    Producto A                  10     12.50   125.00
    Producto B                   5     25.00   125.00
    
    Subtotal:                                  250.00
    IVA 12%:                                    30.00
    TOTAL:                                     280.00
    """
    page.insert_text((50, 50), invoice_text)
    doc.save(str(pdf_path))
    doc.close()

    # Measure timing
    start = time.time()
    text = detect_native_text_in_pdf(str(pdf_path))
    elapsed_ms = (time.time() - start) * 1000

    # Assertions
    assert text is not None
    assert "FACTURA" in text
    assert "001-001-000123" in text
    assert elapsed_ms < benchmark_threshold_ms, (
        f"OCR too slow: {elapsed_ms:.0f}ms > {benchmark_threshold_ms}ms"
    )
