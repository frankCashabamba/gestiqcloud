"""Tests for security guards - SPEC-1 compliance."""

import os
import tempfile
from unittest import mock

import pytest

from app.modules.imports.application.security_guards import (
    SecurityViolationError,
    check_file_mime,
    check_file_size,
    check_pdf_security,
    count_pdf_pages,
    scan_virus,
    validate_file_security,
)


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_pdf():
    """Create temporary PDF for testing."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # Write minimal valid PDF
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")
        f.write(b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n")
        f.write(b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n")
        f.write(b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n")
        f.write(b"0000000058 00000 n\n0000000115 00000 n\ntrailer\n")
        f.write(b"<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n")

    yield path
    if os.path.exists(path):
        os.remove(path)


class TestFileSizeCheck:
    """Test file size validation."""

    def test_file_within_limit(self, temp_file):
        """Test file within size limit passes."""
        with open(temp_file, "wb") as f:
            f.write(b"x" * 1024 * 1024)  # 1 MB

        check_file_size(temp_file, max_mb=2)  # Should not raise

    def test_file_exceeds_limit(self, temp_file):
        """Test file exceeding limit raises error."""
        with open(temp_file, "wb") as f:
            f.write(b"x" * 17 * 1024 * 1024)  # 17 MB

        with pytest.raises(SecurityViolationError) as exc_info:
            check_file_size(temp_file, max_mb=16)

        assert exc_info.value.code == "FILE_TOO_LARGE"
        assert "17" in exc_info.value.detail

    def test_nonexistent_file(self):
        """Test nonexistent file raises error."""
        with pytest.raises(SecurityViolationError) as exc_info:
            check_file_size("/nonexistent/file.txt", max_mb=16)

        assert exc_info.value.code == "FILE_ACCESS_ERROR"


class TestMimeTypeCheck:
    """Test MIME type validation."""

    @mock.patch("app.modules.imports.application.security_guards.MAGIC_AVAILABLE", True)
    @mock.patch("app.modules.imports.application.security_guards.magic")
    def test_allowed_mime_type(self, mock_magic, temp_file):
        """Test allowed MIME type passes."""
        mock_magic.Magic.return_value.from_file.return_value = "image/jpeg"

        result = check_file_mime(temp_file, ["image/jpeg", "image/png"])  # noqa: F841

        assert result == "image/jpeg"

    @mock.patch("app.modules.imports.application.security_guards.MAGIC_AVAILABLE", True)
    @mock.patch("app.modules.imports.application.security_guards.magic")
    def test_disallowed_mime_type(self, mock_magic, temp_file):
        """Test disallowed MIME type raises error."""
        mock_magic.Magic.return_value.from_file.return_value = (
            "application/x-executable"
        )

        with pytest.raises(SecurityViolationError) as exc_info:
            check_file_mime(temp_file, ["image/jpeg", "image/png"])

        assert exc_info.value.code == "INVALID_MIME_TYPE"
        assert "executable" in exc_info.value.detail.lower()

    @mock.patch(
        "app.modules.imports.application.security_guards.MAGIC_AVAILABLE", False
    )
    def test_magic_not_available(self, temp_file):
        """Test graceful degradation when magic not available."""
        result = check_file_mime(temp_file, ["image/jpeg"])  # noqa: F841

        assert result == "application/octet-stream"


class TestAntivirusScan:
    """Test antivirus scanning."""

    @mock.patch(
        "app.modules.imports.application.security_guards.CLAMD_AVAILABLE", False
    )
    def test_clamav_not_available(self, temp_file):
        """Test graceful degradation when ClamAV not available."""
        scan_virus(temp_file)  # Should not raise, just log warning

    @mock.patch("app.modules.imports.application.security_guards.CLAMD_AVAILABLE", True)
    @mock.patch("app.modules.imports.application.security_guards.clamd")
    def test_virus_not_found(self, mock_clamd, temp_file):
        """Test clean file passes scan."""
        mock_cd = mock.MagicMock()
        mock_cd.ping.return_value = True
        mock_cd.scan.return_value = {temp_file: ("OK", None)}
        mock_clamd.ClamdUnixSocket.return_value = mock_cd

        scan_virus(temp_file)  # Should not raise

    @mock.patch("app.modules.imports.application.security_guards.CLAMD_AVAILABLE", True)
    @mock.patch("app.modules.imports.application.security_guards.clamd")
    def test_virus_detected(self, mock_clamd, temp_file):
        """Test virus detection raises error."""
        mock_cd = mock.MagicMock()
        mock_cd.ping.return_value = True
        mock_cd.scan.return_value = {temp_file: ("FOUND", "Eicar-Test-Signature")}
        mock_clamd.ClamdUnixSocket.return_value = mock_cd

        with pytest.raises(SecurityViolationError) as exc_info:
            scan_virus(temp_file)

        assert exc_info.value.code == "VIRUS_DETECTED"
        assert "Eicar" in exc_info.value.detail

    @mock.patch("app.modules.imports.application.security_guards.CLAMD_AVAILABLE", True)
    @mock.patch("app.modules.imports.application.security_guards.clamd")
    def test_clamav_daemon_not_running(self, mock_clamd, temp_file):
        """Test graceful handling when ClamAV daemon not running."""
        mock_clamd.ClamdUnixSocket.return_value.ping.side_effect = Exception(
            "Connection refused"
        )
        mock_clamd.ClamdNetworkSocket.return_value.ping.side_effect = Exception(
            "Connection refused"
        )

        scan_virus(temp_file)  # Should not raise, just log warning


class TestPDFValidation:
    """Test PDF-specific validation."""

    @mock.patch(
        "app.modules.imports.application.security_guards.PYMUPDF_AVAILABLE", True
    )
    @mock.patch("app.modules.imports.application.security_guards.fitz")
    def test_pdf_page_count_within_limit(self, mock_fitz, temp_pdf):
        """Test PDF with pages within limit passes."""
        mock_doc = mock.MagicMock()
        mock_doc.__len__.return_value = 10
        mock_fitz.open.return_value = mock_doc

        count = count_pdf_pages(temp_pdf, max_pages=20)

        assert count == 10

    @mock.patch(
        "app.modules.imports.application.security_guards.PYMUPDF_AVAILABLE", True
    )
    @mock.patch("app.modules.imports.application.security_guards.fitz")
    def test_pdf_page_count_exceeds_limit(self, mock_fitz, temp_pdf):
        """Test PDF with too many pages raises error."""
        mock_doc = mock.MagicMock()
        mock_doc.__len__.return_value = 25
        mock_fitz.open.return_value = mock_doc

        with pytest.raises(SecurityViolationError) as exc_info:
            count_pdf_pages(temp_pdf, max_pages=20)

        assert exc_info.value.code == "PDF_TOO_MANY_PAGES"
        assert "25" in exc_info.value.detail

    @mock.patch(
        "app.modules.imports.application.security_guards.PYMUPDF_AVAILABLE", True
    )
    @mock.patch("app.modules.imports.application.security_guards.fitz")
    def test_pdf_security_check_no_threats(self, mock_fitz, temp_pdf):
        """Test PDF without threats passes."""
        mock_doc = mock.MagicMock()
        mock_doc.is_form_pdf = False
        mock_doc.__len__.return_value = 1
        mock_page = mock.MagicMock()
        mock_page.annots.return_value = []
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        threats = check_pdf_security(temp_pdf)

        assert threats["has_js"] is False
        assert threats["has_forms"] is False

    @mock.patch(
        "app.modules.imports.application.security_guards.PYMUPDF_AVAILABLE", True
    )
    @mock.patch("app.modules.imports.application.security_guards.fitz")
    def test_pdf_security_check_javascript(self, mock_fitz, temp_pdf):
        """Test PDF with JavaScript detected."""
        mock_doc = mock.MagicMock()
        mock_doc.is_form_pdf = False
        mock_doc.__len__.return_value = 1

        mock_annot = mock.MagicMock()
        mock_annot.info.get.return_value = "app.alert('test')"
        mock_page = mock.MagicMock()
        mock_page.annots.return_value = [mock_annot]
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        threats = check_pdf_security(temp_pdf)

        assert threats["has_js"] is True

    @mock.patch(
        "app.modules.imports.application.security_guards.PYMUPDF_AVAILABLE", False
    )
    def test_pdf_checks_disabled_when_not_available(self, temp_pdf):
        """Test graceful degradation when PyMuPDF not available."""
        count = count_pdf_pages(temp_pdf, max_pages=20)
        threats = check_pdf_security(temp_pdf)

        assert count == 0
        assert threats["has_js"] is False


class TestIntegratedValidation:
    """Test full validation workflow."""

    @mock.patch("app.modules.imports.application.security_guards.MAGIC_AVAILABLE", True)
    @mock.patch(
        "app.modules.imports.application.security_guards.CLAMD_AVAILABLE", False
    )
    @mock.patch("app.modules.imports.application.security_guards.magic")
    def test_full_validation_passes(self, mock_magic, temp_file):
        """Test full validation with all checks passing."""
        with open(temp_file, "wb") as f:
            f.write(b"test data")

        mock_magic.Magic.return_value.from_file.return_value = "image/jpeg"

        result = validate_file_security(  # noqa: F841
            temp_file,
            allowed_mimes=["image/jpeg"],
            max_mb=16,
            enable_av_scan=False,
        )

        assert "file_hash" in result
        assert "file_size" in result["checks_passed"]
        assert "mime_type" in result["checks_passed"]

    def test_bypass_mode(self, temp_file):
        """Test security bypass mode (dev only)."""
        result = validate_file_security(temp_file, bypass=True)  # noqa: F841

        assert result["bypassed"] is True

    @mock.patch("app.modules.imports.application.security_guards.MAGIC_AVAILABLE", True)
    @mock.patch("app.modules.imports.application.security_guards.magic")
    def test_validation_stops_on_first_error(self, mock_magic, temp_file):
        """Test validation stops at first failure."""
        with open(temp_file, "wb") as f:
            f.write(b"x" * 20 * 1024 * 1024)  # 20 MB

        mock_magic.Magic.return_value.from_file.return_value = "image/jpeg"

        with pytest.raises(SecurityViolationError) as exc_info:
            validate_file_security(
                temp_file,
                allowed_mimes=["image/jpeg"],
                max_mb=16,
            )

        assert exc_info.value.code == "FILE_TOO_LARGE"


class TestSecurityViolationError:
    """Test SecurityViolationError exception."""

    def test_error_structure(self):
        """Test error has required attributes."""
        err = SecurityViolationError(
            code="TEST_ERROR", detail="Test error message", file_path="/tmp/test.txt"
        )

        assert err.code == "TEST_ERROR"
        assert err.detail == "Test error message"
        assert err.file_path == "/tmp/test.txt"

    def test_error_to_dict(self):
        """Test error serialization."""
        err = SecurityViolationError(
            code="TEST_ERROR", detail="Test error message", file_path="/tmp/test.txt"
        )

        error_dict = err.to_dict()

        assert error_dict["error_type"] == "security_violation"
        assert error_dict["code"] == "TEST_ERROR"
        assert error_dict["detail"] == "Test error message"
        assert error_dict["file_path"] == "/tmp/test.txt"
