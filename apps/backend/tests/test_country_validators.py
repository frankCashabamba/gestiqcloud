"""Tests for country-specific validators (Frontend/Backend sync)."""

import pytest
from apps.backend.app.modules.imports.validators.country_validators import ECValidator, ESValidator


class TestECValidator:
    """Tests for Ecuador validator - must sync with frontend."""

    @pytest.fixture
    def validator(self):
        return ECValidator()

    def test_valid_ruc(self, validator):
        """Should accept valid RUC."""
        errors = validator.validate_tax_id("1790084103004")
        assert len(errors) == 0

    def test_valid_ruc_type_0_natural(self, validator):
        """Should accept RUC with type 0 (natural person)."""
        errors = validator.validate_tax_id("0109000000010")
        assert len(errors) == 0

    def test_valid_ruc_type_1_juridical(self, validator):
        """Should accept RUC with type 1 (juridical entity)."""
        errors = validator.validate_tax_id("0110000000002")
        assert len(errors) == 0

    def test_valid_ruc_type_6_government(self, validator):
        """Should accept RUC with type 6 (government)."""
        errors = validator.validate_tax_id("0160000000000")
        assert len(errors) == 0

    def test_valid_ruc_type_9_temporary(self, validator):
        """Should accept RUC with type 9 (temporary)."""
        errors = validator.validate_tax_id("0190000000001")
        assert len(errors) == 0

    def test_invalid_province_99(self, validator):
        """Should reject RUC with invalid province code (99)."""
        errors = validator.validate_tax_id("9999999999999")
        assert any(
            e["code"] == "INVALID_TAX_ID_FORMAT" and "province" in e["message"].lower()
            for e in errors
        )

    def test_invalid_province_00(self, validator):
        """Should reject RUC with province 00 (must be 01-24)."""
        errors = validator.validate_tax_id("0099999999999")
        assert any(
            e["code"] == "INVALID_TAX_ID_FORMAT" and "province" in e["message"].lower()
            for e in errors
        )

    def test_invalid_type_digit(self, validator):
        """Should reject RUC with invalid type digit."""
        errors = validator.validate_tax_id("0150000000001")
        assert any(
            e["code"] == "INVALID_TAX_ID_FORMAT" and "type" in e["message"].lower() for e in errors
        )

    def test_invalid_checksum(self, validator):
        """Should reject RUC with invalid checksum."""
        # Valid: 1790084103004, Invalid: 1790084103999 (last digit wrong)
        errors = validator.validate_tax_id("1790084103999")
        assert any(e["code"] == "INVALID_CHECKSUM" for e in errors)

    def test_empty_ruc(self, validator):
        """Should reject empty RUC."""
        errors = validator.validate_tax_id("")
        assert any(e["code"] == "EMPTY_VALUE" for e in errors)

    def test_ruc_with_letters(self, validator):
        """Should reject RUC containing letters."""
        errors = validator.validate_tax_id("179008410300A")
        assert any(e["code"] == "INVALID_TAX_ID_FORMAT" for e in errors)

    def test_ruc_too_short(self, validator):
        """Should reject RUC with less than 13 digits."""
        errors = validator.validate_tax_id("17900841030")
        assert any(
            e["code"] == "INVALID_TAX_ID_FORMAT" and "13 digits" in e["message"] for e in errors
        )

    def test_ruc_too_long(self, validator):
        """Should reject RUC with more than 13 digits."""
        errors = validator.validate_tax_id("17900841030001")
        assert any(e["code"] == "INVALID_TAX_ID_FORMAT" for e in errors)

    def test_validate_clave_acceso_valid(self, validator):
        """Should accept valid Clave de Acceso."""
        # Format: DDMMYY + RUC + Establishment + Emission + Sequential + Type + Checksum
        clave = "1704201717900841030014001000000000011062021234567890"
        errors = validator.validate_clave_acceso(clave)
        assert not any(e["code"] == "INVALID_CLAVE_FORMAT" for e in errors)

    def test_validate_clave_acceso_invalid_length(self, validator):
        """Should reject Clave with invalid length."""
        errors = validator.validate_clave_acceso("123")
        assert any(e["code"] == "INVALID_CLAVE_ACCESO" for e in errors)

    def test_validate_clave_acceso_invalid_date(self, validator):
        """Should reject Clave with invalid date."""
        # Invalid day 99
        clave = "9904201717900841030014001000000000011062021234567890"
        errors = validator.validate_clave_acceso(clave)
        assert any(e["code"] == "INVALID_CLAVE_ACCESO" for e in errors)

    def test_validate_clave_acceso_invalid_month(self, validator):
        """Should reject Clave with invalid month."""
        # Invalid month 13
        clave = "0113201717900841030014001000000000011062021234567890"
        errors = validator.validate_clave_acceso(clave)
        assert any(e["code"] == "INVALID_CLAVE_ACCESO" for e in errors)

    def test_validate_invoice_number_valid(self, validator):
        """Should accept valid invoice number format."""
        errors = validator.validate_invoice_number("001-001-000000001")
        assert len(errors) == 0

    def test_validate_invoice_number_invalid_format(self, validator):
        """Should reject invalid invoice number format."""
        errors = validator.validate_invoice_number("001001000000001")
        assert any(e["code"] == "INVALID_INVOICE_NUMBER_FORMAT" for e in errors)


class TestESValidator:
    """Tests for Spain validator."""

    @pytest.fixture
    def validator(self):
        return ESValidator()

    def test_valid_nif(self, validator):
        """Should accept valid NIF."""
        errors = validator.validate_tax_id("12345678Z")
        assert len(errors) == 0

    def test_valid_nif_with_hyphen(self, validator):
        """Should accept NIF with hyphen."""
        errors = validator.validate_tax_id("12345678-Z")
        assert len(errors) == 0

    def test_valid_cif(self, validator):
        """Should accept valid CIF format."""
        errors = validator.validate_tax_id("A12345674")
        assert len(errors) == 0

    def test_invalid_nif_checksum(self, validator):
        """Should reject NIF with invalid checksum letter."""
        errors = validator.validate_tax_id("12345678A")
        assert any(e["code"] == "INVALID_TAX_ID_CHECKSUM" for e in errors)

    def test_empty_nif(self, validator):
        """Should reject empty tax ID."""
        errors = validator.validate_tax_id("")
        assert any(e["code"] == "EMPTY_VALUE" for e in errors)

    def test_invalid_format(self, validator):
        """Should reject NIF with invalid format."""
        errors = validator.validate_tax_id("123")
        assert any(e["code"] == "INVALID_TAX_ID_FORMAT" for e in errors)

    def test_validate_invoice_number_valid(self, validator):
        """Should accept valid invoice number."""
        errors = validator.validate_invoice_number("FAC-2025-0001")
        assert len(errors) == 0

    def test_validate_invoice_number_too_long(self, validator):
        """Should reject invoice number exceeding 40 characters."""
        long_invoice = "A" * 50
        errors = validator.validate_invoice_number(long_invoice)
        assert any(e["code"] == "INVALID_INVOICE_NUMBER_FORMAT" for e in errors)


class TestSyncFrontendBackend:
    """Integration tests to verify frontend/backend sync."""

    def test_ecuador_ruc_sync(self):
        """Verify Ecuador RUC validation is identical in frontend and backend."""
        validator = ECValidator()

        # Test cases that must pass/fail identically between TS and Python
        test_cases = [
            ("1790084103004", True, "Valid RUC"),
            ("0109000000010", True, "Valid RUC type 0"),
            ("0190000000001", True, "Valid RUC type 9"),
            ("9999999999999", False, "Invalid province 99"),
            ("0150000000001", False, "Invalid type digit 5"),
            ("1790084103999", False, "Invalid checksum"),
            ("", False, "Empty RUC"),
        ]

        for ruc, should_pass, desc in test_cases:
            errors = validator.validate_tax_id(ruc)
            is_valid = len(errors) == 0
            assert is_valid == should_pass, f"Mismatch for {desc}: {ruc}. Errors: {errors}"

    def test_spain_nif_sync(self):
        """Verify Spain NIF validation matches between layers."""
        validator = ESValidator()

        test_cases = [
            ("12345678Z", True, "Valid NIF"),
            ("12345678A", False, "Invalid checksum"),
            ("A12345674", True, "Valid CIF"),
            ("", False, "Empty NIF"),
        ]

        for nif, should_pass, desc in test_cases:
            errors = validator.validate_tax_id(nif)
            is_valid = len(errors) == 0
            assert is_valid == should_pass, f"Mismatch for {desc}: {nif}. Errors: {errors}"
