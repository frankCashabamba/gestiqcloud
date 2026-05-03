"""OpenCV-based image preprocessing for OCR.

Pipeline applied (in order):
    1. grayscale
    2. CLAHE (Contrast Limited Adaptive Histogram Equalization) - normalizes
       uneven illumination typical in phone photos / WhatsApp images.
    3. median blur - removes salt-and-pepper noise without blurring strokes.
    4. adaptive threshold (Gaussian) - binarizes to a clean B/W image,
       which is what Tesseract works best on.

Designed to be production-safe:
    * Lazy imports cv2/numpy so the module is loadable without OCR deps.
    * Each stage is wrapped: if any step fails we log and return the best
      partial result (or the original PIL image) so OCR never crashes.
    * Pure function, no I/O on the hot path. A path-returning helper is
      provided for callers/CLI/tests that prefer to work with files.
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger("importador.image_preprocess")

# Defaults tuned for WhatsApp / phone-camera photos of receipts and invoices.
DEFAULT_CLAHE_CLIP_LIMIT = 2.0
DEFAULT_CLAHE_TILE_GRID = (8, 8)
DEFAULT_MEDIAN_KERNEL = 3            # 3x3 median: removes spike noise
DEFAULT_ADAPTIVE_BLOCK_SIZE = 31     # odd, ~font-height in px after CLAHE
DEFAULT_ADAPTIVE_C = 10              # bias subtracted from local mean


def _load_cv2() -> tuple[Any, Any]:
    """Lazy import; returns (cv2, numpy) or (None, None) if unavailable."""
    try:
        import cv2  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415

        return cv2, np
    except Exception:  # pragma: no cover - environment without opencv
        return None, None


def preprocess_for_ocr(
    file_bytes: bytes,
    *,
    clahe_clip_limit: float = DEFAULT_CLAHE_CLIP_LIMIT,
    clahe_tile_grid: tuple[int, int] = DEFAULT_CLAHE_TILE_GRID,
    median_kernel: int = DEFAULT_MEDIAN_KERNEL,
    adaptive_block_size: int = DEFAULT_ADAPTIVE_BLOCK_SIZE,
    adaptive_c: int = DEFAULT_ADAPTIVE_C,
    apply_threshold: bool = True,
) -> tuple[Image.Image, dict[str, Any]]:
    """Run the OpenCV preprocessing pipeline on raw image bytes.

    Returns
    -------
    (image, metadata):
        image:    PIL.Image (mode ``L`` if any cv2 step succeeded, otherwise the
                  original RGB image) ready to be fed to Tesseract.
        metadata: ``{"applied": [<stage names>], ...}``. Empty ``applied`` list
                  means cv2 was unavailable or the pipeline fell back early.

    Never raises: failures degrade gracefully so the OCR caller can carry on.
    """
    pil_original = Image.open(io.BytesIO(file_bytes))
    cv2, np = _load_cv2()
    if cv2 is None or np is None:
        return pil_original, {"applied": [], "fallback_reason": "cv2_missing"}

    applied: list[str] = []
    arr = np.array(pil_original.convert("RGB"))

    try:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        applied.append("grayscale")
    except Exception:
        logger.warning("preprocess_for_ocr: grayscale failed", exc_info=True)
        return pil_original, {"applied": applied, "fallback_reason": "grayscale_failed"}

    try:
        clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_tile_grid)
        gray = clahe.apply(gray)
        applied.append("clahe")
    except Exception:
        logger.warning("preprocess_for_ocr: clahe failed", exc_info=True)

    if median_kernel and median_kernel >= 3:
        try:
            kernel = median_kernel if median_kernel % 2 == 1 else median_kernel + 1
            gray = cv2.medianBlur(gray, kernel)
            applied.append(f"median_blur:{kernel}")
        except Exception:
            logger.warning("preprocess_for_ocr: median_blur failed", exc_info=True)

    if apply_threshold and adaptive_block_size and adaptive_block_size >= 3:
        try:
            block = adaptive_block_size if adaptive_block_size % 2 == 1 else adaptive_block_size + 1
            gray = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block,
                int(adaptive_c),
            )
            applied.append(f"adaptive_threshold:{block}/{adaptive_c}")
        except Exception:
            logger.warning("preprocess_for_ocr: adaptive_threshold failed", exc_info=True)

    return Image.fromarray(gray, mode="L"), {
        "applied": applied,
        "clahe_clip_limit": clahe_clip_limit,
        "median_kernel": median_kernel,
        "adaptive_block_size": adaptive_block_size,
    }


def preprocess_to_path(
    file_bytes: bytes,
    dest: str | Path | None = None,
    **options: Any,
) -> Path:
    """Convenience: preprocess and write the result to disk.

    Returns the destination path. Useful for tools that pipe a file path into
    Tesseract directly (or for debugging).
    """
    img, _ = preprocess_for_ocr(file_bytes, **options)
    if dest is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        path = Path(tmp.name)
    else:
        path = Path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
