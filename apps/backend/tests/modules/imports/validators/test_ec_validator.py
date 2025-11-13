from app.modules.imports.validators import ECValidator


class TestECValidator:
    """Tests para validador de Ecuador (SRI)."""

    def setup_method(self):
        self.validator = ECValidator()

    def test_validate_ruc_natural_valid(self):
        errors = self.validator.validate_tax_id("1713175071001")  # noqa: F841
        assert len(errors) == 0

    def test_validate_ruc_juridica_valid(self):
        errors = self.validator.validate_tax_id("1792146739001")  # noqa: F841
        assert len(errors) == 0

    def test_validate_ruc_publica_valid(self):
        errors = self.validator.validate_tax_id("1760001550001")  # noqa: F841
        assert len(errors) == 0

    def test_validate_ruc_invalid_length(self):
        errors = self.validator.validate_tax_id("12345678")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_TAX_ID_FORMAT"

    def test_validate_ruc_invalid_checksum(self):
        errors = self.validator.validate_tax_id("1713175071009")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_TAX_ID_CHECKSUM"

    def test_validate_ruc_empty(self):
        errors = self.validator.validate_tax_id("")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "EMPTY_VALUE"

    def test_validate_tax_rates_iva_valid(self):
        errors = self.validator.validate_tax_rates([0.0, 12.0, 15.0])  # noqa: F841
        assert len(errors) == 0

    def test_validate_tax_rates_ice_valid(self):
        errors = self.validator.validate_tax_rates([10.0, 30.0, 100.0])  # noqa: F841
        assert len(errors) == 0

    def test_validate_tax_rates_invalid(self):
        errors = self.validator.validate_tax_rates([16.0, 21.0])  # noqa: F841
        assert len(errors) == 2
        assert all(e["code"] == "INVALID_TAX_RATE" for e in errors)

    def test_validate_invoice_number_valid(self):
        errors = self.validator.validate_invoice_number("001-001-000000123")  # noqa: F841
        assert len(errors) == 0

    def test_validate_invoice_number_invalid_format(self):
        errors = self.validator.validate_invoice_number("FAC-2025-001")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_INVOICE_NUMBER_FORMAT"

    def test_validate_invoice_number_empty(self):
        errors = self.validator.validate_invoice_number("")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "EMPTY_VALUE"

    def test_validate_clave_acceso_valid(self):
        clave = "0801202501179214673900110010010000000011234567818"
        errors = self.validator.validate_clave_acceso(clave)  # noqa: F841
        assert len(errors) == 0

    def test_validate_clave_acceso_invalid_length(self):
        errors = self.validator.validate_clave_acceso("123456789")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_CLAVE_ACCESO"

    def test_validate_clave_acceso_invalid_checksum(self):
        clave = "0801202501179214673900110010010000000011234567819"
        errors = self.validator.validate_clave_acceso(clave)  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "INVALID_CLAVE_ACCESO"

    def test_validate_clave_acceso_empty(self):
        errors = self.validator.validate_clave_acceso("")  # noqa: F841
        assert len(errors) == 1
        assert errors[0]["code"] == "EMPTY_VALUE"


class TestECValidatorPerformance:
    """Tests de performance para validador EC."""

    def test_validation_performance(self):
        """Validación de un item debe ser <10ms."""
        import time

        validator = ECValidator()

        start = time.perf_counter()
        for _ in range(100):
            validator.validate_tax_id("1713175071001")
            validator.validate_tax_rates([0.0, 12.0])
            validator.validate_invoice_number("001-001-000000123")
        end = time.perf_counter()

        avg_time_ms = (end - start) / 100 * 1000
        assert avg_time_ms < 10, f"Validación tomó {avg_time_ms:.2f}ms (límite: 10ms)"
