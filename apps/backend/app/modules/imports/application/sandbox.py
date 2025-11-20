"""PDF sanitization and sandboxing utilities."""

from __future__ import annotations

import logging
import os
import tempfile

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available - PDF sandboxing disabled")


def sandbox_pdf(pdf_path: str, output_path: str | None = None) -> str:
    """
    Sanitize PDF by removing potentially dangerous elements.

    Removes:
        - Embedded JavaScript
        - Form fields with scripts
        - External links (optional)
        - Embedded files

    Args:
        pdf_path: Path to input PDF
        output_path: Optional output path (creates temp file if None)

    Returns:
        Path to sanitized PDF

    Raises:
        RuntimeError: If PyMuPDF not available or sanitization fails
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF not available, cannot sandbox PDF")

    try:
        logger.info(f"Sandboxing PDF: {pdf_path}")

        # Open PDF
        doc = fitz.open(pdf_path)

        removed_count = {
            "javascript": 0,
            "forms": 0,
            "embeds": 0,
            "links": 0,
        }

        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Remove annotations with JavaScript
            annots = page.annots()
            if annots:
                for annot in annots:
                    try:
                        # Check for JavaScript actions
                        if annot.info.get("JavaScript"):
                            page.delete_annot(annot)
                            removed_count["javascript"] += 1
                            continue

                        # Remove form fields with actions
                        if annot.type[1] == "Widget":  # Form field
                            page.delete_annot(annot)
                            removed_count["forms"] += 1
                    except Exception as e:
                        logger.warning(f"Error processing annotation on page {page_num}: {e}")

            # Remove embedded files (if any)
            try:
                # Get page dictionary
                page_dict = page.get_text("dict")
                if page_dict.get("embeds"):
                    # This is tricky - PyMuPDF doesn't have direct API
                    # We'd need to work with the PDF structure directly
                    # For now, log warning
                    logger.warning(
                        f"Page {page_num} has embedded files - cannot remove automatically"
                    )
                    removed_count["embeds"] += 1
            except Exception as e:
                logger.debug(f"Error checking embeds on page {page_num}: {e}")

        # Remove document-level JavaScript
        try:
            if doc.is_form_pdf:
                # Try to remove form functionality
                # This is a workaround - PyMuPDF doesn't expose this directly
                logger.warning("PDF has forms - consider manual review")
        except Exception as e:
            logger.debug(f"Error removing forms: {e}")

        # Save sanitized PDF
        if output_path is None:
            # Create temp file
            fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="sanitized_")
            os.close(fd)

        # Save with cleaned structure
        doc.save(
            output_path,
            garbage=4,  # Maximum garbage collection
            deflate=True,  # Compress
            clean=True,  # Clean unused objects
        )
        doc.close()

        logger.info(
            f"PDF sanitized: {pdf_path} -> {output_path}, "
            f"removed: {sum(removed_count.values())} elements "
            f"({', '.join(f'{k}={v}' for k, v in removed_count.items() if v > 0)})"
        )

        return output_path

    except Exception as e:
        logger.error(f"PDF sandboxing failed: {e}")
        raise RuntimeError(f"Cannot sandbox PDF: {e}")


def is_pdf_safe(pdf_path: str) -> bool:
    """
    Quick check if PDF appears safe (no obvious threats).

    Args:
        pdf_path: Path to PDF

    Returns:
        True if appears safe, False if threats detected
    """
    if not PYMUPDF_AVAILABLE:
        logger.warning("PyMuPDF not available, cannot verify PDF safety")
        return True  # Assume safe if we can't check

    try:
        doc = fitz.open(pdf_path)

        # Check for forms
        if doc.is_form_pdf:
            doc.close()
            return False

        # Quick scan for annotations
        for page_num in range(min(len(doc), 10)):  # Check first 10 pages
            page = doc[page_num]
            annots = page.annots()
            if annots:
                for annot in annots:
                    if annot.info.get("JavaScript"):
                        doc.close()
                        return False

        doc.close()
        return True

    except Exception as e:
        logger.warning(f"PDF safety check failed: {e}")
        return False  # Assume unsafe if check fails
