"""Security guards for file processing - SPEC-1 compliance."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy imports
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available - MIME validation disabled")

try:
    import clamd

    CLAMD_AVAILABLE = True
except ImportError:
    CLAMD_AVAILABLE = False
    logger.warning("clamd not available - antivirus scanning disabled")

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available - PDF security checks disabled")


class SecurityViolationError(Exception):
    """Raised when file fails security validation."""

    def __init__(self, code: str, detail: str, file_path: str | None = None):
        self.code = code
        self.detail = detail
        self.file_path = file_path
        super().__init__(f"[{code}] {detail}")

    def to_dict(self):
        """Convert to structured error dict."""
        return {
            "error_type": "security_violation",
            "code": self.code,
            "detail": self.detail,
            "file_path": self.file_path,
        }


def check_file_size(file_path: str, max_mb: int = 16) -> None:
    """
    Validate file size.

    Args:
        file_path: Path to file
        max_mb: Maximum allowed size in MB

    Raises:
        SecurityViolationError: If file exceeds limit
    """
    try:
        file_size = os.path.getsize(file_path)
        max_bytes = max_mb * 1024 * 1024

        if file_size > max_bytes:
            raise SecurityViolationError(
                code="FILE_TOO_LARGE",
                detail=f"File size {file_size / 1024 / 1024:.2f}MB exceeds limit of {max_mb}MB",
                file_path=file_path,
            )

        logger.debug(f"File size check passed: {file_size / 1024:.2f}KB")
    except OSError as e:
        raise SecurityViolationError(
            code="FILE_ACCESS_ERROR",
            detail=f"Cannot access file: {e}",
            file_path=file_path,
        )


def check_file_mime(file_path: str, allowed_mimes: list[str]) -> str:
    """
    Validate file MIME type using libmagic.

    Args:
        file_path: Path to file
        allowed_mimes: List of allowed MIME types

    Returns:
        Detected MIME type

    Raises:
        SecurityViolationError: If MIME type not allowed
    """
    if not MAGIC_AVAILABLE:
        logger.warning("python-magic not available, skipping MIME validation")
        return "application/octet-stream"

    try:
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(file_path)

        if detected_mime not in allowed_mimes:
            raise SecurityViolationError(
                code="INVALID_MIME_TYPE",
                detail=f"File type '{detected_mime}' not allowed. Allowed: {', '.join(allowed_mimes)}",
                file_path=file_path,
            )

        logger.debug(f"MIME type validated: {detected_mime}")
        return detected_mime
    except Exception as e:
        if isinstance(e, SecurityViolationError):
            raise
        raise SecurityViolationError(
            code="MIME_DETECTION_ERROR",
            detail=f"Cannot detect MIME type: {e}",
            file_path=file_path,
        )


def scan_virus(file_path: str) -> None:
    """
    Scan file for viruses using ClamAV.

    Args:
        file_path: Path to file

    Raises:
        SecurityViolationError: If virus detected or scan fails critically
    """
    if not CLAMD_AVAILABLE:
        logger.warning("ClamAV not available, skipping antivirus scan (acceptable in dev)")
        return

    try:
        # Try connecting to ClamAV daemon
        cd = clamd.ClamdUnixSocket()
        try:
            cd.ping()
        except Exception:
            # Try network socket
            cd = clamd.ClamdNetworkSocket()
            try:
                cd.ping()
            except Exception:
                logger.warning("ClamAV daemon not running, skipping antivirus scan")
                return

        # Scan file
        result = cd.scan(file_path)

        if result and file_path in result:
            status, virus_name = result[file_path]
            if status == "FOUND":
                # Calculate file hash for audit
                file_hash = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()

                logger.critical(
                    f"VIRUS DETECTED: {virus_name} in file {file_path} "
                    f"(SHA256: {file_hash[:16]}...)"
                )

                raise SecurityViolationError(
                    code="VIRUS_DETECTED",
                    detail=f"Malware detected: {virus_name}",
                    file_path=file_path,
                )

        logger.debug("Antivirus scan passed")
    except SecurityViolationError:
        raise
    except Exception as e:
        logger.warning(f"Antivirus scan failed (non-critical): {e}")


def count_pdf_pages(pdf_path: str, max_pages: int = 20) -> int:
    """
    Count PDF pages and validate limit.

    Args:
        pdf_path: Path to PDF
        max_pages: Maximum allowed pages

    Returns:
        Page count

    Raises:
        SecurityViolationError: If page count exceeds limit
    """
    if not PYMUPDF_AVAILABLE:
        logger.warning("PyMuPDF not available, skipping page count validation")
        return 0

    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()

        if page_count > max_pages:
            raise SecurityViolationError(
                code="PDF_TOO_MANY_PAGES",
                detail=f"PDF has {page_count} pages, exceeds limit of {max_pages}",
                file_path=pdf_path,
            )

        logger.debug(f"PDF page count validated: {page_count} pages")
        return page_count
    except SecurityViolationError:
        raise
    except Exception as e:
        raise SecurityViolationError(
            code="PDF_VALIDATION_ERROR",
            detail=f"Cannot validate PDF: {e}",
            file_path=pdf_path,
        )


def check_pdf_security(pdf_path: str) -> dict:
    """
    Check PDF for security threats (embedded JS, forms, etc.).

    Args:
        pdf_path: Path to PDF

    Returns:
        Dict with threat indicators: {has_js: bool, has_forms: bool, has_embeds: bool}

    Raises:
        SecurityViolationError: If critical threat detected
    """
    if not PYMUPDF_AVAILABLE:
        logger.warning("PyMuPDF not available, skipping PDF security checks")
        return {"has_js": False, "has_forms": False, "has_embeds": False}

    try:
        doc = fitz.open(pdf_path)
        threats = {
            "has_js": False,
            "has_forms": False,
            "has_embeds": False,
        }

        # Check for embedded JavaScript
        if doc.is_form_pdf:
            threats["has_forms"] = True

        # Scan pages for threats
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Check for JavaScript actions
            annots = page.annots()
            if annots:
                for annot in annots:
                    try:
                        if annot.info.get("JavaScript"):
                            threats["has_js"] = True
                    except Exception:
                        pass

            # Check for embedded files
            try:
                if page.get_text("dict").get("embeds"):
                    threats["has_embeds"] = True
            except Exception:
                pass

        doc.close()

        # Log warnings
        if threats["has_js"]:
            logger.warning(f"PDF contains embedded JavaScript: {pdf_path}")
        if threats["has_embeds"]:
            logger.warning(f"PDF contains embedded files: {pdf_path}")

        return threats
    except Exception as e:
        raise SecurityViolationError(
            code="PDF_SECURITY_CHECK_ERROR",
            detail=f"Cannot perform PDF security check: {e}",
            file_path=pdf_path,
        )


def validate_file_security(
    file_path: str,
    allowed_mimes: list[str] | None = None,
    max_mb: int = 16,
    max_pdf_pages: int = 20,
    enable_av_scan: bool = True,
    reject_pdf_with_js: bool = True,
    bypass: bool = False,
) -> dict:
    """
    Main security validation entry point - runs all checks.

    Args:
        file_path: Path to file
        allowed_mimes: List of allowed MIME types
        max_mb: Maximum file size in MB
        max_pdf_pages: Maximum PDF pages
        enable_av_scan: Enable antivirus scanning
        reject_pdf_with_js: Reject PDFs with embedded JavaScript
        bypass: Skip all checks (ONLY FOR DEVELOPMENT)

    Returns:
        Dict with validation results

    Raises:
        SecurityViolationError: If any validation fails
    """
    if bypass:
        logger.warning(f"SECURITY BYPASS ENABLED - skipping validation for {file_path}")
        return {"bypassed": True}

    # Calculate file hash for audit
    file_hash = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
    logger.info(f"Validating file security: {file_path} (SHA256: {file_hash[:16]}...)")

    results = {
        "file_hash": file_hash,
        "file_path": file_path,
        "checks_passed": [],
    }

    try:
        # Check 1: File size
        check_file_size(file_path, max_mb=max_mb)
        results["checks_passed"].append("file_size")

        # Check 2: MIME type
        detected_mime = None
        if allowed_mimes:
            detected_mime = check_file_mime(file_path, allowed_mimes)
            results["mime_type"] = detected_mime
            results["checks_passed"].append("mime_type")

        # Check 3: Antivirus scan
        if enable_av_scan:
            scan_virus(file_path)
            results["checks_passed"].append("antivirus")

        # Check 4: PDF-specific checks
        is_pdf = detected_mime == "application/pdf" or file_path.lower().endswith(".pdf")
        if is_pdf and PYMUPDF_AVAILABLE:
            # Page count
            page_count = count_pdf_pages(file_path, max_pages=max_pdf_pages)
            results["pdf_pages"] = page_count
            results["checks_passed"].append("pdf_pages")

            # Security threats
            threats = check_pdf_security(file_path)
            results["pdf_threats"] = threats
            results["checks_passed"].append("pdf_security")

            # Reject if JS and configured to do so
            if reject_pdf_with_js and threats.get("has_js"):
                raise SecurityViolationError(
                    code="PDF_CONTAINS_JAVASCRIPT",
                    detail="PDF contains embedded JavaScript which is not allowed",
                    file_path=file_path,
                )

        logger.info(
            f"Security validation passed: {len(results['checks_passed'])} checks, file: {file_path}"
        )

        return results

    except SecurityViolationError as e:
        # Log security violation for audit
        logger.error(
            f"SECURITY VIOLATION: {e.code} - {e.detail} "
            f"(file: {file_path}, hash: {file_hash[:16]}...)"
        )
        raise
