"""Security configuration for file processing."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class SecurityConfig:
    """Security configuration for file uploads and processing."""
    
    # File size limits
    max_file_size_mb: int = 16
    
    # PDF limits
    max_pdf_pages: int = 20
    
    # Allowed MIME types
    allowed_mime_types: List[str] = field(default_factory=lambda: [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
        "image/tiff",
        "image/webp",
        "image/bmp",
    ])
    
    # Security features
    enable_av_scan: bool = True  # Auto-detects ClamAV availability
    reject_pdf_with_js: bool = True
    reject_pdf_with_embeds: bool = False  # More permissive
    
    # Development bypass (DANGEROUS - only for local dev)
    bypass_security: bool = False


def get_security_config() -> SecurityConfig:
    """
    Load security configuration from environment variables.
    
    Environment variables:
        IMPORTS_SECURITY_BYPASS: Set to "1" to bypass all checks (dev only)
        IMPORTS_MAX_FILE_SIZE_MB: Maximum file size in MB (default: 16)
        IMPORTS_MAX_PDF_PAGES: Maximum PDF pages (default: 20)
        IMPORTS_ENABLE_AV_SCAN: Enable antivirus scanning (default: true)
        IMPORTS_REJECT_PDF_JS: Reject PDFs with JavaScript (default: true)
    
    Returns:
        SecurityConfig instance
    """
    return SecurityConfig(
        max_file_size_mb=int(os.getenv("IMPORTS_MAX_FILE_SIZE_MB", "16")),
        max_pdf_pages=int(os.getenv("IMPORTS_MAX_PDF_PAGES", "20")),
        enable_av_scan=os.getenv("IMPORTS_ENABLE_AV_SCAN", "true").lower() == "true",
        reject_pdf_with_js=os.getenv("IMPORTS_REJECT_PDF_JS", "true").lower() == "true",
        bypass_security=os.getenv("IMPORTS_SECURITY_BYPASS", "0") == "1",
    )
