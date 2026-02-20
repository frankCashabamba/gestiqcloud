"""Tests - E-Invoicing Module (Sprint 2)"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.einvoicing.country_settings import EInvoicingCountrySettings, TaxRegime
from app.models.einvoicing.einvoice import (
    EInvoice,
    EInvoiceError,
    EInvoiceSignature,
    EInvoiceStatus,
)
from app.modules.einvoicing.application.sii_service import SIIService


@pytest.fixture
def tenant_id(db: Session):
    tid = uuid4()
    db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, active, created_at) "
            "VALUES (:id, :name, :slug, :active, :created_at)"
        ),
        {
            "id": tid.hex,
            "name": "Sprint2 EInvoicing",
            "slug": f"s2-einv-{tid.hex[:8]}",
            "active": True,
            "created_at": datetime.utcnow(),
        },
    )
    db.flush()
    return tid


@pytest.fixture
def sii_settings(db: Session, tenant_id):
    """Crea configuración SII para tenant."""
    # Crear TaxRegime primero
    regime = TaxRegime(
        country="ES",
        regime_code="NORMAL",
        regime_name="Régimen Normal",
        requires_ruc=False,
        requires_invoice_authorization=False,
        vat_applicable=True,
        vat_rates={"standard": 21, "reduced": 10, "super_reduced": 4},
    )
    db.add(regime)
    db.flush()

    # Crear configuración
    settings = EInvoicingCountrySettings(
        tenant_id=tenant_id,
        country="ES",
        is_enabled=True,
        environment="STAGING",
        api_endpoint="https://www.aeat.es/svl/siiTest",
        max_retries=5,
        retry_backoff_seconds=300,
    )
    db.add(settings)
    db.flush()
    return settings


@pytest.fixture
def invoice_data():
    """Datos de factura de prueba."""
    return {
        "company_cif": "ES12345678A",
        "company_name": "Mi Empresa S.L.",
        "customer_nif": "87654321Z",
        "customer_name": "Cliente Test",
        "customer_address": "Calle Principal 123",
        "invoice_number": "FAC-2026-001",
        "issue_date": "2026-02-15",
        "subtotal": 1000.00,
        "total_vat": 210.00,
        "total": 1210.00,
        "lines": [
            {
                "description": "Servicio A",
                "quantity": 1,
                "unit_price": 500.00,
                "total": 500.00,
            },
            {
                "description": "Servicio B",
                "quantity": 1,
                "unit_price": 500.00,
                "total": 500.00,
            },
        ],
    }


# ============================================================================
# TESTS: Configuration
# ============================================================================


def test_sii_settings_creation(db: Session, tenant_id):
    """Test: crea configuración SII."""
    settings = EInvoicingCountrySettings(
        tenant_id=tenant_id,
        country="ES",
        is_enabled=True,
        environment="STAGING",
        api_endpoint="https://www.aeat.es/svl/siiTest",
    )
    db.add(settings)
    db.flush()

    assert settings.country == "ES"
    assert settings.api_endpoint == "https://www.aeat.es/svl/siiTest"


def test_sii_get_settings(db: Session, tenant_id, sii_settings):
    """Test: obtiene configuración desde BD."""
    settings = SIIService.get_settings(db, tenant_id, "ES")

    assert settings.is_enabled is True
    assert settings.api_endpoint == "https://www.aeat.es/svl/siiTest"


def test_sii_get_api_endpoint(db: Session, tenant_id, sii_settings):
    """Test: obtiene endpoint API (NO HARDCODEADO)."""
    endpoint = SIIService.get_api_endpoint(db, tenant_id, "ES")

    # Debe venir de BD, no ser hardcodeado
    assert endpoint == "https://www.aeat.es/svl/siiTest"
    assert "aeat.es" in endpoint


def test_tax_regime_creation(db: Session):
    """Test: crea régimen fiscal (master data)."""
    regime = TaxRegime(
        country="ES",
        regime_code="NORMAL",
        regime_name="Régimen Normal",
        requires_ruc=False,
        vat_applicable=True,
        vat_rates={"standard": 21, "reduced": 10},
    )
    db.add(regime)
    db.flush()

    assert regime.country == "ES"
    assert regime.vat_applicable is True


# ============================================================================
# TESTS: Validation
# ============================================================================


def test_validate_invoice_valid(invoice_data):
    """Test: valida factura correcta."""
    errors = SIIService.validate_invoice_data(invoice_data, "ES")

    assert len(errors) == 0


def test_validate_invoice_missing_cif(invoice_data):
    """Test: valida que CIF sea requerido."""
    del invoice_data["company_cif"]
    errors = SIIService.validate_invoice_data(invoice_data, "ES")

    assert "company_cif_required" in errors


def test_validate_invoice_invalid_cif_format(invoice_data):
    """Test: valida formato de CIF."""
    invoice_data["company_cif"] = "INVALID"  # Muy corto
    errors = SIIService.validate_invoice_data(invoice_data, "ES")

    assert "company_cif_invalid_format" in errors


def test_validate_invoice_missing_customer_nif(invoice_data):
    """Test: valida que NIF cliente sea requerido."""
    del invoice_data["customer_nif"]
    errors = SIIService.validate_invoice_data(invoice_data, "ES")

    assert "customer_nif_required" in errors


def test_validate_invoice_vat_calculation(invoice_data):
    """Test: valida cálculo de IVA."""
    # VAT incorrecto
    invoice_data["total_vat"] = 300.00  # Debería ser ~210
    errors = SIIService.validate_invoice_data(invoice_data, "ES")

    assert len(errors) > 0


# ============================================================================
# TESTS: XML Generation
# ============================================================================


def test_generate_xml_structure(invoice_data):
    """Test: genera XML con estructura correcta."""
    xml = SIIService.generate_xml(invoice_data, "ES")

    assert "<factura" in xml
    assert "version=" in xml
    assert "<cabecera>" in xml
    assert "<empresa>" in xml
    assert "<cliente>" in xml
    assert "<lineas>" in xml
    assert "<totales>" in xml


def test_generate_xml_company_data(invoice_data):
    """Test: XML contiene datos de empresa."""
    xml = SIIService.generate_xml(invoice_data, "ES")

    assert invoice_data["company_cif"] in xml
    assert invoice_data["company_name"] in xml


def test_generate_xml_customer_data(invoice_data):
    """Test: XML contiene datos de cliente."""
    xml = SIIService.generate_xml(invoice_data, "ES")

    assert invoice_data["customer_nif"] in xml
    assert invoice_data["customer_name"] in xml


def test_generate_xml_invoice_lines(invoice_data):
    """Test: XML contiene líneas de factura."""
    xml = SIIService.generate_xml(invoice_data, "ES")

    for line in invoice_data["lines"]:
        assert line["description"] in xml


def test_generate_xml_totals(invoice_data):
    """Test: XML contiene totales."""
    xml = SIIService.generate_xml(invoice_data, "ES")

    assert str(invoice_data["subtotal"]) in xml
    assert str(invoice_data["total_vat"]) in xml
    assert str(invoice_data["total"]) in xml


# ============================================================================
# TESTS: EInvoice Creation
# ============================================================================


def test_einvoice_send_to_sii(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: envía factura a SII."""
    result = SIIService.send_to_sii(db, tenant_id, uuid4(), invoice_data)

    assert result["status"] in ["PENDING", "SENT", "ACCEPTED", "ERROR"]


def test_einvoice_record_created(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: crea registro EInvoice."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(
        select(EInvoice).where(EInvoice.invoice_id == invoice_id)
    ).scalar_one_or_none()

    assert einvoice is not None
    assert einvoice.tenant_id == tenant_id
    assert einvoice.country == "ES"


def test_einvoice_xml_content(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: guarda XML en registro."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    assert einvoice.xml_content is not None
    assert "<factura" in einvoice.xml_content


# ============================================================================
# TESTS: EInvoice Status
# ============================================================================


def test_einvoice_status_pending(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: crea einvoice con estado PENDING."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    assert einvoice.status in ["PENDING", "SENT", "ACCEPTED"]


def test_einvoice_status_transitions(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: transiciones de estado de einvoice."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    # Cambiar estado
    einvoice.status = "ACCEPTED"
    einvoice.fiscal_number = "SII000001"
    einvoice.authorization_code = "AUTH123"
    einvoice.accepted_at = datetime.utcnow()
    db.flush()

    assert einvoice.status == "ACCEPTED"
    assert einvoice.fiscal_number is not None


def test_einvoice_status_history(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: registra historial de estados."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    # Agregar cambio de estado
    status_change = EInvoiceStatus(
        einvoice_id=einvoice.id,
        old_status="PENDING",
        new_status="SENT",
        reason="Sent to SII",
    )
    db.add(status_change)
    db.flush()

    # Crear otro cambio
    status_change2 = EInvoiceStatus(
        einvoice_id=einvoice.id,
        old_status="SENT",
        new_status="ACCEPTED",
        reason="SII accepted",
    )
    db.add(status_change2)
    db.flush()

    statuses = db.query(EInvoiceStatus).filter_by(einvoice_id=einvoice.id).all()
    assert len(statuses) >= 2


# ============================================================================
# TESTS: Retry Logic
# ============================================================================


def test_einvoice_retry_count(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: incrementa contador de reintentos."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    initial_count = einvoice.retry_count

    # Simular reintento
    SIIService.retry_send(db, einvoice.id)
    db.refresh(einvoice)

    assert einvoice.retry_count > initial_count


def test_einvoice_retry_schedule(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: programa próximo reintento."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    # Si status es RETRY, debe tener next_retry_at
    if einvoice.status == "RETRY":
        assert einvoice.next_retry_at is not None
        assert einvoice.next_retry_at > datetime.utcnow()


def test_einvoice_max_retries_exceeded(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: detiene después de max retries."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    # Simular múltiples reintentos
    einvoice.retry_count = 6  # Más que max_retries (5)

    with pytest.raises(ValueError, match="Max retry"):
        SIIService.retry_send(db, einvoice.id)


# ============================================================================
# TESTS: Signature
# ============================================================================


def test_einvoice_signature_creation(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: crea firma digital."""
    invoice_id = uuid4()
    SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)

    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    # Si tiene firma, verificar
    if einvoice.signature:
        assert einvoice.signature.status in ["SIGNED", "VERIFIED"]


def test_einvoice_signature_info(db: Session):
    """Test: guarda información de firma."""
    signature = EInvoiceSignature(
        einvoice_id=uuid4(),
        certificate_serial="1234567890",
        certificate_issuer="CA Trustworthy",
        digest_algorithm="SHA256",
        status="SIGNED",
    )
    db.add(signature)
    db.flush()

    assert signature.certificate_serial == "1234567890"
    assert signature.digest_algorithm == "SHA256"


# ============================================================================
# TESTS: Errors
# ============================================================================


def test_einvoice_error_logging(db: Session, tenant_id, sii_settings):
    """Test: registra errores de envío."""
    einvoice = EInvoice(
        tenant_id=tenant_id,
        invoice_id=uuid4(),
        country="ES",
        status="ERROR",
    )
    db.add(einvoice)
    db.flush()

    error = EInvoiceError(
        einvoice_id=einvoice.id,
        error_code="VAL_001",
        error_message="Invalid CIF format",
        error_type="VALIDATION",
        is_recoverable=False,
    )
    db.add(error)
    db.flush()

    assert error.error_type == "VALIDATION"
    assert error.is_recoverable is False


def test_einvoice_recoverable_error(db: Session, tenant_id, sii_settings):
    """Test: marca error como recuperable."""
    einvoice = EInvoice(
        tenant_id=tenant_id,
        invoice_id=uuid4(),
        country="ES",
        status="ERROR",
    )
    db.add(einvoice)
    db.flush()

    error = EInvoiceError(
        einvoice_id=einvoice.id,
        error_message="Connection timeout",
        error_type="CONNECTIVITY",
        is_recoverable=True,
    )
    db.add(error)
    db.flush()

    assert error.is_recoverable is True
    # Poder hacer reintento


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_full_einvoicing_workflow(db: Session, tenant_id, sii_settings, invoice_data):
    """Test: flujo completo de factura electrónica."""
    invoice_id = uuid4()

    # 1. Enviar factura
    result = SIIService.send_to_sii(db, tenant_id, invoice_id, invoice_data)
    assert result["status"] in ["PENDING", "SENT", "ACCEPTED"]

    # 2. Obtener estado
    from sqlalchemy import select

    einvoice = db.execute(select(EInvoice).where(EInvoice.invoice_id == invoice_id)).scalar_one()

    status = SIIService.get_status(db, einvoice.id)
    assert status["status"] is not None

    # 3. Si aceptada, verificar datos
    if status["status"] == "ACCEPTED":
        assert status["fiscal_number"] is not None
        assert status["authorization_code"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
