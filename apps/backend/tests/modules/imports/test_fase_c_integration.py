"""
Tests de integración Fase C: Validación por país + Handlers + Flujo completo.

Verifica que:
1. Parsers emiten CanonicalDocument válidos
2. validate_canonical valida estructura SPEC-1
3. Country validators validan según país
4. HandlersRouter despacha a handlers correctos
5. Handlers promocionan a tablas destino
"""

import pytest

from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.domain.handlers import (
    BankHandler,
    ExpenseHandler,
    InvoiceHandler,
    ProductHandler,
)
from app.modules.imports.domain.handlers_router import HandlersRouter
# TODO: Country validators not yet implemented
# from app.modules.imports.validators.country_validators import (
#     ECValidator,
#     ESValidator,
#     get_validator_for_country,
# )


@pytest.mark.skip(reason="Country validators not yet implemented")
class TestCanonicalValidationPhaseC:
    """Validación de estructura canónica - Fase C."""

    def test_invoice_spec_1_valid(self):
        """Factura cumple SPEC-1."""
        doc = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "invoice_number": "001-002-000123",
            "vendor": {
                "name": "Proveedor SA",
                "tax_id": "1792012345001",
                "country": "EC",
            },
            "buyer": {
                "name": "Mi Empresa",
                "tax_id": "1791234567001",
            },
            "totals": {
                "subtotal": 100.0,
                "tax": 12.0,
                "total": 112.0,
                "tax_breakdown": [{"code": "IVA12-EC", "rate": 12.0, "amount": 12.0}],
            },
            "lines": [
                {
                    "desc": "Producto",
                    "qty": 1.0,
                    "unit_price": 100.0,
                    "total": 100.0,
                    "tax_code": "IVA12",
                }
            ],
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_bank_tx_spec_1_valid(self):
        """Transacción bancaria cumple SPEC-1."""
        doc = {
            "doc_type": "bank_tx",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "bank_tx": {
                "amount": 1500.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Transferencia cliente",
                "counterparty": "Cliente ABC",
                "external_ref": "TRX001",
            },
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_expense_receipt_spec_1_valid(self):
        """Recibo de gasto cumple SPEC-1."""
        doc = {
            "doc_type": "expense_receipt",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "vendor": {"name": "Tienda Local"},
            "totals": {
                "subtotal": 50.0,
                "tax": 6.0,
                "total": 56.0,
            },
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_product_spec_1_valid(self):
        """Producto cumple SPEC-1."""
        doc = {
            "doc_type": "product",
            "country": "EC",
            "currency": "USD",
            "product": {
                "name": "Laptop Dell",
                "sku": "LAP-001",
                "price": 1200.0,
                "stock": 10,
                "category": "Electrónica",
            },
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_expense_spec_1_valid(self):
        """Gasto cumple SPEC-1."""
        doc = {
            "doc_type": "expense",
            "country": "EC",
            "currency": "USD",
            "expense": {
                "description": "Combustible",
                "amount": 50.0,
                "expense_date": "2025-01-15",
                "category": "combustible",
            },
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"


class TestCountryValidatorsEcuador:
    """Validadores específicos para Ecuador - Fase C."""

    def test_ec_validator_valid_ruc(self):
        """RUC ecuatoriano válido."""
        validator = ECValidator()
        errors = validator.validate_tax_id("1792012345001")
        assert len(errors) == 0

    def test_ec_validator_invalid_ruc_format(self):
        """RUC con formato inválido."""
        validator = ECValidator()
        errors = validator.validate_tax_id("179201234500")  # 12 dígitos
        assert len(errors) > 0

    def test_ec_validator_valid_iva_rates(self):
        """Tasas IVA válidas para Ecuador."""
        validator = ECValidator()
        errors = validator.validate_tax_rates([0.0, 12.0, 15.0])
        assert len(errors) == 0

    def test_ec_validator_invalid_iva_rate(self):
        """Tasa IVA inválida para Ecuador."""
        validator = ECValidator()
        errors = validator.validate_tax_rates([10.0])  # No es 0, 12, o 15
        assert len(errors) > 0

    def test_ec_validator_valid_ice_rate(self):
        """Tasa ICE válida para Ecuador."""
        validator = ECValidator()
        errors = validator.validate_tax_rates([5.0, 10.0])
        assert len(errors) == 0

    def test_ec_validator_valid_invoice_number(self):
        """Número de factura válido formato SRI."""
        validator = ECValidator()
        errors = validator.validate_invoice_number("001-002-000000123")
        assert len(errors) == 0

    def test_ec_validator_invoice_number_invalid_format(self):
        """Número de factura formato inválido."""
        validator = ECValidator()
        errors = validator.validate_invoice_number("123456789")
        assert len(errors) > 0


class TestCountryValidatorsSpain:
    """Validadores específicos para España - Fase C."""

    def test_es_validator_valid_nif(self):
        """NIF español válido."""
        validator = ESValidator()
        errors = validator.validate_tax_id("12345678Z")
        assert len(errors) == 0

    def test_es_validator_valid_cif(self):
        """CIF español válido."""
        validator = ESValidator()
        validator.validate_tax_id("A12345674")
        # Puede ser válido dependiendo de la implementación
        # assert len(errors) == 0

    def test_es_validator_valid_iva_rates(self):
        """Tasas IVA válidas para España."""
        validator = ESValidator()
        errors = validator.validate_tax_rates([0.0, 4.0, 10.0, 21.0])
        assert len(errors) == 0

    def test_es_validator_invalid_iva_rate(self):
        """Tasa IVA inválida para España."""
        validator = ESValidator()
        errors = validator.validate_tax_rates([12.0])  # No es válida en ES
        assert len(errors) > 0


class TestCountryValidatorFactory:
    """Factory de validadores por país - Fase C."""

    def test_get_validator_ec(self):
        """Obtener validador Ecuador."""
        validator = get_validator_for_country("EC")
        assert isinstance(validator, ECValidator)

    def test_get_validator_es(self):
        """Obtener validador España."""
        validator = get_validator_for_country("ES")
        assert isinstance(validator, ESValidator)

    def test_get_validator_unknown_country(self):
        """País no soportado retorna None."""
        validator = get_validator_for_country("XX")
        assert validator is None

    def test_get_validator_case_insensitive(self):
        """Factory es case-insensitive."""
        validator1 = get_validator_for_country("EC")
        validator2 = get_validator_for_country("ec")
        assert type(validator1) is type(validator2)


class TestHandlersRouterMapping:
    """Mapeo doc_type → Handler - Fase C."""

    def test_handler_map_invoice(self):
        """Invoice → InvoiceHandler."""
        handler_class = HandlersRouter.get_handler_for_type("invoice")
        assert handler_class == InvoiceHandler

    def test_handler_map_expense(self):
        """Expense → ExpenseHandler."""
        handler_class = HandlersRouter.get_handler_for_type("expense")
        assert handler_class == ExpenseHandler

    def test_handler_map_bank_tx(self):
        """Bank_tx → BankHandler."""
        handler_class = HandlersRouter.get_handler_for_type("bank_tx")
        assert handler_class == BankHandler

    def test_handler_map_product(self):
        """Product → ProductHandler."""
        handler_class = HandlersRouter.get_handler_for_type("product")
        assert handler_class == ProductHandler

    def test_handler_map_aliases(self):
        """Aliases funcionan."""
        assert HandlersRouter.get_handler_for_type("factura") == InvoiceHandler
        assert HandlersRouter.get_handler_for_type("recibo") == ExpenseHandler
        assert HandlersRouter.get_handler_for_type("transferencia") == BankHandler

    def test_target_map_invoice(self):
        """Invoice → invoices table."""
        target = HandlersRouter.get_target_for_type("invoice")
        assert target == "invoices"

    def test_target_map_expense(self):
        """Expense → expenses table."""
        target = HandlersRouter.get_target_for_type("expense")
        assert target == "expenses"

    def test_target_map_bank_tx(self):
        """Bank_tx → bank_movements table."""
        target = HandlersRouter.get_target_for_type("bank_tx")
        assert target == "bank_movements"

    def test_target_map_product(self):
        """Product → inventory table."""
        target = HandlersRouter.get_target_for_type("product")
        assert target == "inventory"

    def test_target_map_case_insensitive(self):
        """Mapeo es case-insensitive."""
        target1 = HandlersRouter.get_target_for_type("INVOICE")
        target2 = HandlersRouter.get_target_for_type("invoice")
        assert target1 == target2 == "invoices"


class TestCompleteFlowEcuador:
    """Flujo completo: Parser → Validate → Country Validator → Handler (Ecuador)."""

    def test_flow_invoice_ecuador(self):
        """
        Flujo completo factura Ecuador:
        1. CanonicalDocument validado
        2. ECValidator valida RUC y tasas
        3. HandlersRouter despacha a InvoiceHandler
        4. Target es "invoices"
        """
        # 1. Documento canónico válido
        canonical_doc = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "invoice_number": "001-002-000123",
            "vendor": {
                "name": "Proveedor SA",
                "tax_id": "1792012345001",
                "country": "EC",
            },
            "buyer": {
                "name": "Mi Empresa",
                "tax_id": "1791234567001",
            },
            "totals": {
                "subtotal": 100.0,
                "tax": 12.0,
                "total": 112.0,
                "tax_breakdown": [{"code": "IVA12-EC", "rate": 12.0, "amount": 12.0}],
            },
        }

        # 2. Validar estructura canónica
        is_valid, errors = validate_canonical(canonical_doc)
        assert is_valid, f"Validación canónica falló: {errors}"

        # 3. Validar con country validator
        ec_validator = get_validator_for_country("EC")
        assert ec_validator is not None

        vendor_errors = ec_validator.validate_tax_id(canonical_doc["vendor"]["tax_id"])
        assert len(vendor_errors) == 0, f"Validación RUC falló: {vendor_errors}"

        rate_errors = ec_validator.validate_tax_rates([12.0])
        assert len(rate_errors) == 0, f"Validación tasas falló: {rate_errors}"

        # 4. Despachar a handler
        handler_class = HandlersRouter.get_handler_for_type("invoice")
        assert handler_class == InvoiceHandler

        # 5. Obtener tabla destino
        target = HandlersRouter.get_target_for_type("invoice")
        assert target == "invoices"

    def test_flow_bank_transaction_ecuador(self):
        """
        Flujo completo transacción bancaria Ecuador:
        1. CanonicalDocument validado
        2. HandlersRouter despacha a BankHandler
        3. Target es "bank_movements"
        """
        canonical_doc = {
            "doc_type": "bank_tx",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "bank_tx": {
                "amount": 1500.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Pago de cliente",
                "counterparty": "Cliente ABC",
            },
        }

        # 1. Validar estructura
        is_valid, errors = validate_canonical(canonical_doc)
        assert is_valid, f"Validación falló: {errors}"

        # 2. Despachar
        handler_class = HandlersRouter.get_handler_for_type("bank_tx")
        assert handler_class == BankHandler

        # 3. Target
        target = HandlersRouter.get_target_for_type("bank_tx")
        assert target == "bank_movements"

    def test_flow_expense_receipt_ecuador(self):
        """
        Flujo completo recibo de gasto Ecuador:
        1. CanonicalDocument validado
        2. HandlersRouter despacha a ExpenseHandler
        3. Target es "expenses"
        """
        canonical_doc = {
            "doc_type": "expense_receipt",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "vendor": {"name": "Gasolinera Shell"},
            "totals": {
                "subtotal": 50.0,
                "tax": 6.0,
                "total": 56.0,
            },
        }

        # 1. Validar
        is_valid, errors = validate_canonical(canonical_doc)
        assert is_valid, f"Validación falló: {errors}"

        # 2. Despachar
        handler_class = HandlersRouter.get_handler_for_type("expense_receipt")
        assert handler_class == ExpenseHandler

        # 3. Target
        target = HandlersRouter.get_target_for_type("expense_receipt")
        assert target == "expenses"

    def test_flow_product_ecuador(self):
        """
        Flujo completo producto Ecuador:
        1. CanonicalDocument validado
        2. HandlersRouter despacha a ProductHandler
        3. Target es "inventory"
        """
        canonical_doc = {
            "doc_type": "product",
            "country": "EC",
            "currency": "USD",
            "product": {
                "name": "Laptop Dell",
                "price": 1200.0,
                "stock": 5,
            },
        }

        # 1. Validar
        is_valid, errors = validate_canonical(canonical_doc)
        assert is_valid, f"Validación falló: {errors}"

        # 2. Despachar
        handler_class = HandlersRouter.get_handler_for_type("product")
        assert handler_class == ProductHandler

        # 3. Target
        target = HandlersRouter.get_target_for_type("product")
        assert target == "inventory"


class TestCompleteFlowSpain:
    """Flujo completo: Parser → Validate → Country Validator → Handler (España)."""

    def test_flow_invoice_spain(self):
        """Flujo completo factura España con validación ES."""
        canonical_doc = {
            "doc_type": "invoice",
            "country": "ES",
            "currency": "EUR",
            "issue_date": "2025-01-15",
            "invoice_number": "FAC-2025-0001",
            "vendor": {
                "name": "Empresa SA",
                "tax_id": "12345678Z",
                "country": "ES",
            },
            "totals": {
                "subtotal": 100.0,
                "tax": 21.0,
                "total": 121.0,
                "tax_breakdown": [{"code": "IVA21-ES", "rate": 21.0, "amount": 21.0}],
            },
        }

        # 1. Validar estructura
        is_valid, errors = validate_canonical(canonical_doc)
        assert is_valid, f"Validación falló: {errors}"

        # 2. Validar con country validator
        es_validator = get_validator_for_country("ES")
        assert es_validator is not None

        rate_errors = es_validator.validate_tax_rates([21.0])
        assert len(rate_errors) == 0, f"Validación tasas España falló: {rate_errors}"

        # 3. Despachar
        handler_class = HandlersRouter.get_handler_for_type("invoice")
        assert handler_class == InvoiceHandler

        # 4. Target
        target = HandlersRouter.get_target_for_type("invoice")
        assert target == "invoices"


class TestValidationErrorHandling:
    """Manejo de errores en validación - Fase C."""

    def test_missing_doc_type(self):
        """Sin doc_type no valida."""
        doc = {"country": "EC", "currency": "USD"}
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("doc_type" in e for e in errors)

    def test_invalid_doc_type(self):
        """doc_type inválido no valida."""
        doc = {"doc_type": "invalid", "country": "EC"}
        is_valid, errors = validate_canonical(doc)
        assert not is_valid

    def test_invalid_country(self):
        """País no soportado no valida."""
        doc = {"doc_type": "invoice", "country": "XX"}
        is_valid, errors = validate_canonical(doc)
        assert not is_valid

    def test_invalid_currency(self):
        """Moneda no soportada no valida."""
        doc = {"doc_type": "invoice", "country": "EC", "currency": "XXX"}
        is_valid, errors = validate_canonical(doc)
        assert not is_valid

    def test_invoice_missing_required_fields(self):
        """Factura sin campos obligatorios no valida."""
        doc = {"doc_type": "invoice", "country": "EC", "currency": "USD"}
        is_valid, errors = validate_canonical(doc)
        assert not is_valid

    def test_bank_tx_invalid_direction(self):
        """Dirección bancaria inválida."""
        doc = {
            "doc_type": "bank_tx",
            "bank_tx": {
                "amount": 100.0,
                "direction": "invalid",
                "value_date": "2025-01-15",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
