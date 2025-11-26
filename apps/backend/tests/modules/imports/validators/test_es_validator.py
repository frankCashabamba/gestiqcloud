from app.modules.imports.validators import ESValidator


class TestESValidator:
    """Tests para validador de España (AEAT)."""

    def setup_method(self):
        """Initialize the Spain validator."""
        self.validator = ESValidator()

    def test_validate_nif_valid(self):
        errors = self.validator.validate_tax_id("12345678Z")  # noqa: F841
        assert len(errors) == 0

    def test_validate_nif_invalid_letter(self):
        errors = self.validator.validate_tax_id("12345678X")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_TAX_ID_CHECKSUM"

    def test_validate_nie_valid(self):
        errors = self.validator.validate_tax_id("X1234567L")  # noqa: F841
        assert len(errors) == 0

    def test_validate_nie_invalid_letter(self):
        errors = self.validator.validate_tax_id("X1234567Z")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_TAX_ID_CHECKSUM"

    def test_validate_cif_valid_number(self):
        errors = self.validator.validate_tax_id("A12345674")  # noqa: F841
        assert len(errors) == 0

    def test_validate_cif_valid_letter(self):
        errors = self.validator.validate_tax_id("A12345674")  # noqa: F841
        assert len(errors) == 0

    def test_validate_cif_invalid_control(self):
        errors = self.validator.validate_tax_id("A12345679")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_TAX_ID_CHECKSUM"

    def test_validate_tax_id_invalid_format(self):
        errors = self.validator.validate_tax_id("123ABC")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_TAX_ID_FORMAT"

    def test_validate_tax_id_empty(self):
        errors = self.validator.validate_tax_id("")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "EMPTY_VALUE"

    def test_validate_tax_rates_valid(self):
        errors = self.validator.validate_tax_rates([0.0, 4.0, 10.0, 21.0])  # noqa: F841
        assert len(errors) == 0

    def test_validate_tax_rates_invalid(self):
        errors = self.validator.validate_tax_rates([5.0, 12.0, 16.0])  # noqa: F841
        assert len(errors) == 3
        assert all(e["code"] == "INVALID_TAX_RATE" for e in errors)

    def test_validate_invoice_number_valid_formats(self):
        valid_numbers = [
            "FAC-2025-001",
            "2025/123",
            "A1234567890",
            "INV-001-2025",
        ]
        for number in valid_numbers:
            errors = self.validator.validate_invoice_number(number)  # noqa: F841
            assert len(errors) == 0, f"Failed for: {number}"

    def test_validate_invoice_number_too_long(self):
        errors = self.validator.validate_invoice_number("A" * 31)  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_INVOICE_NUMBER_FORMAT"

    def test_validate_invoice_number_invalid_chars(self):
        errors = self.validator.validate_invoice_number("FAC@2025#001")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_INVOICE_NUMBER_FORMAT"

    def test_validate_invoice_number_empty(self):
        errors = self.validator.validate_invoice_number("")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "EMPTY_VALUE"


class TestESValidatorPerformance:
    """Tests de performance para validador ES."""

    def test_validation_performance(self):
        """Validación de un item debe ser <10ms."""
        import time

        validator = ESValidator()

        start = time.perf_counter()
        for _ in range(100):
            validator.validate_tax_id("12345678Z")
            validator.validate_tax_rates([0.0, 21.0])
            validator.validate_invoice_number("FAC-2025-001")
        end = time.perf_counter()

        avg_time_ms = (end - start) / 100 * 1000
        assert avg_time_ms < 10, f"Validación tomó {avg_time_ms:.2f}ms (límite: 10ms)"
