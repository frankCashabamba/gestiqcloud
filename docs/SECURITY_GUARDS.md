# Security Guards for File Processing — SPEC-1 Compliance

## Overview

Security guards provide defense-in-depth validation for user-uploaded files (PDFs, images) before OCR processing. Implements **SPEC-1** requirements for ClamAV scanning, libmagic MIME validation, size/page limits, and PDF threat detection.

## Architecture

```
User Upload → Security Guards → OCR Processing
                    ↓
            [Size] [MIME] [AV] [PDF]
                    ↓
              Pass / Reject
```

### Components

1. **`security_guards.py`** — Core validation functions
2. **`security_config.py`** — Configuration from environment
3. **`sandbox.py`** — PDF sanitization (optional)
4. **`photo_utils.py`** — Integration point

## Security Checks

### 1. File Size Validation

**Function**: `check_file_size(file_path, max_mb=16)`

- Validates file does not exceed configured limit
- Default: **16 MB** (configurable via `IMPORTS_MAX_FILE_SIZE_MB`)
- **Error Code**: `FILE_TOO_LARGE`, `FILE_ACCESS_ERROR`

### 2. MIME Type Validation

**Function**: `check_file_mime(file_path, allowed_mimes)`

- Uses **libmagic** (not file extension) to detect true file type
- Prevents disguised executables (e.g., `.exe` renamed to `.pdf`)
- Default allowed types: `application/pdf`, `image/jpeg`, `image/png`, `image/tiff`, `image/webp`, `image/bmp`
- **Error Code**: `INVALID_MIME_TYPE`, `MIME_DETECTION_ERROR`
- **Graceful degradation**: Logs warning if `python-magic` not available

### 3. Antivirus Scanning

**Function**: `scan_virus(file_path)`

- Scans file using **ClamAV** daemon (clamd)
- Tries Unix socket → Network socket → Graceful skip if unavailable
- Logs **critical alert** with file SHA256 if virus detected
- **Error Code**: `VIRUS_DETECTED`
- **Graceful degradation**: Logs warning if ClamAV not running (acceptable in dev)

### 4. PDF Page Count

**Function**: `count_pdf_pages(pdf_path, max_pages=20)`

- Validates PDF does not exceed page limit (prevents DoS via 1000-page PDFs)
- Default: **20 pages** (configurable via `IMPORTS_MAX_PDF_PAGES`)
- **Error Code**: `PDF_TOO_MANY_PAGES`, `PDF_VALIDATION_ERROR`

### 5. PDF Security Threats

**Function**: `check_pdf_security(pdf_path)`

- Detects embedded JavaScript (XSS vector)
- Detects form fields with actions
- Detects embedded files
- Returns threat indicators: `{has_js: bool, has_forms: bool, has_embeds: bool}`
- **Error Code**: `PDF_CONTAINS_JAVASCRIPT` (if `reject_pdf_with_js=true`)

## Error Codes Reference

| Code | Description | Severity | Action |
|------|-------------|----------|--------|
| `FILE_TOO_LARGE` | File exceeds size limit (default 16MB) | ERROR | Reject upload, prompt user to compress |
| `FILE_ACCESS_ERROR` | Cannot read file (permissions/not found) | ERROR | Check file path and permissions |
| `INVALID_MIME_TYPE` | File type not allowed (e.g., executable) | ERROR | Reject upload, show allowed types |
| `MIME_DETECTION_ERROR` | Cannot detect file type | ERROR | File may be corrupt |
| `VIRUS_DETECTED` | Malware found by ClamAV | CRITICAL | Reject upload, log for audit |
| `PDF_TOO_MANY_PAGES` | PDF exceeds page limit (default 20) | ERROR | Reject upload, split PDF |
| `PDF_VALIDATION_ERROR` | Cannot validate PDF structure | ERROR | PDF may be corrupt |
| `PDF_CONTAINS_JAVASCRIPT` | Embedded JS detected | WARNING/ERROR | Reject if `reject_pdf_with_js=true`, else sanitize |
| `PDF_SECURITY_CHECK_ERROR` | Cannot perform security scan | ERROR | PDF may be corrupt |

## Configuration

### Environment Variables

```bash
# Size/page limits
IMPORTS_MAX_FILE_SIZE_MB=16        # Default: 16MB
IMPORTS_MAX_PDF_PAGES=20           # Default: 20 pages

# Security features
IMPORTS_ENABLE_AV_SCAN=true        # Enable ClamAV (auto-detects availability)
IMPORTS_REJECT_PDF_JS=true         # Reject PDFs with JavaScript

# Development bypass (DANGEROUS - never use in production)
IMPORTS_SECURITY_BYPASS=1          # Skip ALL checks (dev only)
```

### Python API

```python
from app.modules.imports.application.security_config import get_security_config

config = get_security_config()
print(config.max_file_size_mb)      # 16
print(config.allowed_mime_types)    # ['application/pdf', 'image/jpeg', ...]
```

## Usage

### Basic Validation

```python
from app.modules.imports.application.security_guards import (
    validate_file_security,
    SecurityViolationError
)

try:
    result = validate_file_security(
        "/tmp/upload.pdf",
        allowed_mimes=["application/pdf"],
        max_mb=16,
        max_pdf_pages=20,
        enable_av_scan=True,
        reject_pdf_with_js=True,
    )
    
    print(f"✓ Validation passed: {result['checks_passed']}")
    print(f"  File hash: {result['file_hash']}")
    
except SecurityViolationError as e:
    print(f"✗ Security violation: {e.code}")
    print(f"  Detail: {e.detail}")
    
    # Structured error for API response
    error_dict = e.to_dict()
    # {
    #   "error_type": "security_violation",
    #   "code": "VIRUS_DETECTED",
    #   "detail": "Malware detected: Eicar-Test-Signature",
    #   "file_path": "/tmp/upload.pdf"
    # }
```

### Integrated with OCR (photo_utils.py)

Security checks run automatically before OCR:

```python
from app.modules.imports.application.photo_utils import ocr_texto

try:
    text = ocr_texto(file_bytes, filename="invoice.pdf")
    print(f"Extracted: {len(text)} chars")
    
except SecurityViolationError as e:
    # Handle security rejection
    return {"error": e.to_dict()}
```

## PDF Sanitization (Optional)

For PDFs with **non-critical threats** (e.g., JavaScript in trusted sources), use sandbox:

```python
from app.modules.imports.application.sandbox import sandbox_pdf

# Remove JS, forms, embeds
safe_path = sandbox_pdf("/tmp/input.pdf", output_path="/tmp/safe.pdf")

# Process sanitized PDF
text = ocr_texto(Path(safe_path).read_bytes(), filename="safe.pdf")
```

## Performance

Target: **<100ms** for typical files

| Check | Typical Duration | Notes |
|-------|------------------|-------|
| File size | <1ms | Simple stat |
| MIME type | 5-15ms | libmagic reads file header |
| Antivirus | 20-80ms | Depends on file size, ClamAV load |
| PDF pages | 10-30ms | PyMuPDF loads document |
| PDF security | 15-50ms | Scans annotations/objects |

## Auditing & Logging

All security violations logged with:
- **File SHA256** (for audit trail)
- Error code and detail
- File path (not logged in production for PII)

Example log:
```
2025-10-17 14:32:15 ERROR [security_guards] SECURITY VIOLATION: VIRUS_DETECTED - Malware detected: Eicar-Test-Signature (file: /tmp/upload.pdf, hash: 275a021bbfb6...)
```

## Testing

Run security guards tests:

```bash
cd apps/backend
pytest tests/modules/imports/test_security_guards.py -v
```

### Test Coverage

- ✅ File size: within limit / exceeds limit / nonexistent file
- ✅ MIME type: allowed / disallowed / magic not available
- ✅ Antivirus: clean / virus detected / daemon not running / clamd not installed
- ✅ PDF pages: within limit / exceeds limit
- ✅ PDF security: no threats / JavaScript detected / PyMuPDF not available
- ✅ Integrated: full validation passes / bypass mode / stops on first error

## ClamAV Setup (Production)

### Installation

```bash
# Run automated setup
sudo ops/scripts/setup_clamav.sh

# Or manually:
sudo apt-get install clamav clamav-daemon clamav-freshclam  # Debian/Ubuntu
sudo yum install clamav clamd                                 # RHEL/CentOS
```

### Configuration

Edit `/etc/clamav/clamd.conf`:

```conf
LocalSocket /var/run/clamav/clamd.ctl
MaxFileSize 32M
MaxScanSize 128M
```

### Start & Enable

```bash
sudo systemctl enable clamav-daemon
sudo systemctl start clamav-daemon
sudo systemctl status clamav-daemon

# Update virus definitions
sudo freshclam
```

### Health Check

```bash
# Test scan
echo "X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" | clamdscan -

# Expected: "Eicar-Test-Signature FOUND"
```

## Security Best Practices

1. **Never bypass in production** — `IMPORTS_SECURITY_BYPASS=1` is for local dev only
2. **Keep ClamAV updated** — Run `freshclam` daily (setup script configures cron)
3. **Log violations to audit system** — Security events should trigger alerts
4. **Rate limit uploads** — Prevent DoS via repeated large file uploads
5. **Store file hashes** — Enables deduplication and abuse tracking
6. **Isolate processing** — Run OCR workers in sandboxed containers

## Limitations

- **MIME validation**: Can be bypassed by polyglot files (very rare in practice)
- **ClamAV**: Only detects known malware signatures (zero-days pass)
- **PDF sanitization**: Does not guarantee 100% safety (manual review for sensitive PDFs)
- **Performance**: Very large files (>50MB) may timeout (enforce strict limits)

## Troubleshooting

### "ClamAV not available" warnings

**Cause**: `clamd` package not installed or daemon not running

**Solution**:
```bash
sudo ops/scripts/setup_clamav.sh
# OR
sudo systemctl start clamav-daemon
```

**Workaround**: Set `IMPORTS_ENABLE_AV_SCAN=false` (not recommended for production)

### "python-magic not available" warnings

**Cause**: `python-magic-bin` not installed

**Solution**:
```bash
pip install python-magic-bin  # Windows compatible
# OR
pip install python-magic       # Linux (requires libmagic)
```

### PDF validation fails for valid PDFs

**Cause**: Encrypted/password-protected PDFs not supported

**Solution**: Ask user to decrypt PDF before upload

### Performance degradation

**Cause**: ClamAV scanning large files

**Solution**:
- Reduce `IMPORTS_MAX_FILE_SIZE_MB` to 8-10 MB
- Increase ClamAV `MaxThreads` in `/etc/clamav/clamd.conf`
- Scale out workers

## Roadmap

- [ ] Support for encrypted PDFs (password prompt)
- [ ] Deep content inspection (detect phishing URLs in text)
- [ ] Integration with VirusTotal API (multi-engine scanning)
- [ ] Machine learning-based anomaly detection
- [ ] Quarantine system for suspicious files
- [ ] File reputation scoring (hash-based)

## References

- ClamAV: https://www.clamav.net/
- python-magic: https://github.com/ahupp/python-magic
- PyMuPDF: https://pymupdf.readthedocs.io/
- OWASP File Upload Security: https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
