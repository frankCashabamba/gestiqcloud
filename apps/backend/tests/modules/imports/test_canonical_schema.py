"""
Tests para schema canónico SPEC-1.

Cubre validación, conversión legacy y construcción de documentos.
"""
import pytest
from app.modules.imports.domain.canonical_schema import (
    CanonicalDocument,
    validate_canonical,
    convert_legacy_to_canonical,
    detect_and_convert,
    build_routing_proposal,
    validate_totals,
    validate_tax_breakdown,
)


class TestCanonicalValidation:
    """Tests de validación de schema canónico."""
    
    def test_valid_invoice_minimal(self):
        """Factura mínima válida."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "invoice_number": "001-002-000123",
            "vendor": {"name": "Proveedor SA", "tax_id": "1792012345001"},
            "totals": {"subtotal": 100.0, "tax": 12.0, "total": 112.0},
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid
        assert len(errors) == 0
    
    def test_invalid_doc_type_missing(self):
        """doc_type es obligatorio."""
        doc = {
            "country": "EC",
            "currency": "USD",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("doc_type" in err for err in errors)
    
    def test_invalid_country(self):
        """País no soportado."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "XX",  # No existe
            "currency": "USD",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("country" in err for err in errors)
    
    def test_invalid_currency(self):
        """Moneda no soportada."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "XXX",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("currency" in err for err in errors)
    
    def test_invalid_date_format(self):
        """Fecha en formato incorrecto."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "issue_date": "15/01/2025",  # Debe ser YYYY-MM-DD
            "invoice_number": "001",
            "vendor": {"name": "Test"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("issue_date" in err for err in errors)
    
    def test_invoice_requires_invoice_number(self):
        """Facturas requieren número."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "issue_date": "2025-01-15",
            "vendor": {"name": "Test"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("invoice_number" in err for err in errors)
    
    def test_expense_receipt_requires_date_and_total(self):
        """Recibos requieren fecha y total."""
        doc: CanonicalDocument = {
            "doc_type": "expense_receipt",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("issue_date" in err for err in errors)
        assert any("totals.total" in err for err in errors)
    
    def test_bank_tx_requires_bank_tx_block(self):
        """Transacciones bancarias requieren bloque bank_tx."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("bank_tx" in err for err in errors)
    
    def test_bank_tx_validates_direction(self):
        """Dirección debe ser debit o credit."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "bank_tx": {
                "amount": 100.0,
                "direction": "invalid",
                "value_date": "2025-01-15",
                "narrative": "Test",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("direction" in err for err in errors)


class TestTotalsValidation:
    """Tests de validación de totales."""
    
    def test_totals_valid(self):
        """Totales correctos."""
        totals = {"subtotal": 100.0, "tax": 12.0, "total": 112.0}
        errors = validate_totals(totals)
        assert len(errors) == 0
    
    def test_totals_mismatch(self):
        """Totales no cuadran."""
        totals = {"subtotal": 100.0, "tax": 12.0, "total": 120.0}
        errors = validate_totals(totals)
        assert len(errors) > 0
        assert "no cuadra" in errors[0]
    
    def test_totals_with_rounding_tolerance(self):
        """Tolera diferencias de redondeo."""
        totals = {"subtotal": 100.0, "tax": 12.0, "total": 112.005}
        errors = validate_totals(totals)
        assert len(errors) == 0


class TestTaxBreakdownValidation:
    """Tests de validación de desglose fiscal."""
    
    def test_tax_breakdown_valid(self):
        """Desglose válido."""
        breakdown = [
            {"code": "IVA12-EC", "rate": 12.0, "amount": 12.0},
        ]
        errors = validate_tax_breakdown(breakdown)
        assert len(errors) == 0
    
    def test_tax_breakdown_missing_code(self):
        """Falta código."""
        breakdown = [
            {"rate": 12.0, "amount": 12.0},
        ]
        errors = validate_tax_breakdown(breakdown)
        assert len(errors) > 0
        assert "code" in errors[0]["field"]
    
    def test_tax_breakdown_missing_amount(self):
        """Falta monto."""
        breakdown = [
            {"code": "IVA12", "rate": 12.0},
        ]
        errors = validate_tax_breakdown(breakdown)
        assert len(errors) > 0
        assert "amount" in errors[0]["field"]


class TestLegacyConversion:
    """Tests de conversión de formato legacy."""
    
    def test_convert_legacy_factura(self):
        """Convierte factura legacy."""
        legacy = {
            "fecha": "2025-01-15",
            "concepto": "Compra suministros",
            "importe": 112.0,
            "documentoTipo": "factura",
            "invoice": "001-002-000123",
            "cliente": "Cliente ABC",
            "origen": "ocr",
        }
        canonical = convert_legacy_to_canonical(legacy)
        
        assert canonical["doc_type"] == "invoice"
        assert canonical["issue_date"] == "2025-01-15"
        assert canonical["invoice_number"] == "001-002-000123"
        assert canonical["totals"]["total"] == 112.0
        assert canonical["vendor"]["name"] == "Cliente ABC"
        assert len(canonical["lines"]) == 1
    
    def test_convert_legacy_recibo(self):
        """Convierte recibo legacy."""
        legacy = {
            "fecha": "2025-01-15",
            "concepto": "Gasolina",
            "importe": 50.0,
            "documentoTipo": "recibo",
            "origen": "ocr",
        }
        canonical = convert_legacy_to_canonical(legacy)
        
        assert canonical["doc_type"] == "expense_receipt"
        assert canonical["issue_date"] == "2025-01-15"
        assert canonical["totals"]["total"] == 50.0
    
    def test_detect_and_convert_legacy(self):
        """Detecta y convierte automáticamente legacy."""
        legacy = {
            "fecha": "2025-01-15",
            "concepto": "Test",
            "importe": 100.0,
            "documentoTipo": "factura",
        }
        canonical = detect_and_convert(legacy)
        assert canonical["doc_type"] == "invoice"
    
    def test_detect_and_convert_already_canonical(self):
        """No convierte si ya es canónico."""
        canonical_doc = {
            "doc_type": "invoice",
            "issue_date": "2025-01-15",
            "invoice_number": "001",
        }
        result = detect_and_convert(canonical_doc)
        assert result["doc_type"] == "invoice"
        assert "documentoTipo" not in result


class TestRoutingProposal:
    """Tests de propuestas de enrutamiento."""
    
    def test_build_routing_proposal_invoice(self):
        """Propuesta para factura."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "totals": {"total": 100.0},
        }
        proposal = build_routing_proposal(doc, "FUEL", "6230", 0.85)
        
        assert proposal["target"] == "expenses"
        assert proposal["category_code"] == "FUEL"
        assert proposal["account"] == "6230"
        assert proposal["confidence"] == 0.85
    
    def test_build_routing_proposal_bank_tx(self):
        """Propuesta para transacción bancaria."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "bank_tx": {"amount": 1000.0, "direction": "credit"},
        }
        proposal = build_routing_proposal(doc, confidence=0.7)
        
        assert proposal["target"] == "bank_movements"
        assert proposal["confidence"] == 0.7


class TestCompleteExamples:
    """Tests con ejemplos completos."""
    
    def test_complete_invoice_ecuador(self):
        """Factura completa de Ecuador."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "due_date": "2025-02-15",
            "invoice_number": "001-002-000123",
            "vendor": {
                "name": "Proveedor SA",
                "tax_id": "1792012345001",
                "country": "EC",
                "address": "Quito, Ecuador",
            },
            "buyer": {
                "name": "Mi Empresa SRL",
                "tax_id": "1791234567001",
            },
            "totals": {
                "subtotal": 100.0,
                "tax": 12.0,
                "total": 112.0,
                "tax_breakdown": [
                    {"code": "IVA12-EC", "rate": 12.0, "amount": 12.0, "base": 100.0}
                ],
            },
            "lines": [
                {
                    "desc": "Suministros de oficina",
                    "qty": 10.0,
                    "unit": "pcs",
                    "unit_price": 10.0,
                    "total": 100.0,
                    "tax_code": "IVA12",
                    "tax_amount": 12.0,
                }
            ],
            "payment": {"method": "transfer", "iban": "EC12345678901234567890"},
            "routing_proposal": {
                "target": "expenses",
                "category_code": "SUPPLIES",
                "account": "6290",
                "confidence": 0.85,
            },
            "source": "xml",
            "confidence": 0.95,
        }
        
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"
    
    def test_complete_bank_transaction(self):
        """Transacción bancaria completa."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "bank_tx": {
                "amount": 1500.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Transferencia cliente ABC",
                "counterparty": "Cliente ABC SA",
                "external_ref": "TRX20250115001",
            },
            "routing_proposal": {
                "target": "bank_movements",
                "confidence": 0.90,
            },
            "source": "camt053",
            "confidence": 0.95,
        }
        
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
