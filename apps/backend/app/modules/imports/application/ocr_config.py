"""OCR Configuration for imports module."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class OCRConfig:
    """Configuration for OCR processing."""
    
    ocr_lang: str
    ocr_psm: int
    ocr_dpi: int
    ocr_workers: int
    max_pages: int
    omp_thread_limit: int
    enable_cache: bool
    skip_native_pdf: bool
    enable_qr: bool

    @classmethod
    def from_env(cls) -> OCRConfig:
        """Load OCR config from environment variables."""
        return cls(
            ocr_lang=os.getenv("IMPORTS_OCR_LANG", "spa+eng"),
            ocr_psm=int(os.getenv("IMPORTS_OCR_PSM", "6")),
            ocr_dpi=int(os.getenv("IMPORTS_OCR_DPI", "200")),
            ocr_workers=int(os.getenv("IMPORTS_OCR_WORKERS", "2")),
            max_pages=int(os.getenv("IMPORTS_MAX_PAGES", "20")),
            omp_thread_limit=int(os.getenv("OMP_THREAD_LIMIT", "1")),
            enable_cache=os.getenv("IMPORTS_OCR_CACHE", "1") == "1",
            skip_native_pdf=os.getenv("IMPORTS_SKIP_NATIVE_PDF", "1") == "1",
            enable_qr=os.getenv("IMPORTS_ENABLE_QR", "1") == "1",
        )


_CONFIG: OCRConfig | None = None


def get_ocr_config() -> OCRConfig:
    """Get cached OCR configuration."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = OCRConfig.from_env()
    return _CONFIG
