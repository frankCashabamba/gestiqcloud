"""Tests SRI Ecuador — firma XAdES-BES, validación RUC, parsers SOAP, task Celery."""

from __future__ import annotations

import base64
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.core.einvoicing import SRISubmission
from app.models.einvoicing.country_settings import EInvoicingCountrySettings
from app.modules.einvoicing.application.sri_service import (
    SRIService,
    _build_authorization_envelope,
    _build_reception_envelope,
    _parse_authorization_response,
    _parse_reception_response,
    validate_ruc_ec,
)
from app.workers.einvoicing_tasks import (
    calcular_digito_verificador_modulo11,
    generate_clave_acceso,
    generate_sri_xml,
    sign_xml_xades_bes,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_INVOICE_DATA = {
    "numero": "001-001-000000001",
    "fecha": date(2026, 3, 24),
    "subtotal": 100.0,
    "impuesto": 15.0,
    "total": 115.0,
    "empresa": {
        "nombre": "Empresa Test S.A.",
        "ruc": "1790000125001",
        "direccion": "Av. Principal 123, Quito",
    },
    "cliente": {
        "nombre": "Cliente Test",
        "ruc": "1713175071001",
        "email": "cliente@test.ec",
    },
    "lines": [
        {
            "cantidad": 1.0,
            "precio_unitario": 100.0,
            "total": 100.0,
            "descripcion": "Servicio de prueba",
            "sku": "SRV-001",
        }
    ],
}


def _make_p12() -> bytes:
    """
    Genera un certificado P12 auto-firmado en memoria para pruebas.
    No hace falta escribir en disco.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Test Cert"),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EC"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GestiqCloud Test"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime(2025, 1, 1))
        .not_valid_after(datetime(2030, 1, 1))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"test", key, cert, None, serialization.NoEncryption()
    )


@pytest.fixture(scope="module")
def p12_cert_data():
    """P12 de prueba reutilizable (generado una sola vez por módulo)."""
    p12_bytes = _make_p12()
    return {
        "p12_base64": base64.b64encode(p12_bytes).decode(),
        "password": "",
    }


@pytest.fixture
def tenant_id(db: Session):
    tid = uuid4()
    db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, active, created_at) "
            "VALUES (:id, :name, :slug, :active, :created_at)"
        ),
        {
            "id": str(tid),
            "name": "Test SRI Ecuador",
            "slug": f"sri-test-{tid.hex[:8]}",
            "active": True,
            "created_at": datetime.utcnow(),
        },
    )
    db.flush()
    return tid


@pytest.fixture
def sri_settings(db: Session, tenant_id):
    """Configuración SRI Ecuador en BD."""
    settings = EInvoicingCountrySettings(
        tenant_id=tenant_id,
        country="EC",
        is_enabled=True,
        environment="STAGING",
        api_endpoint="https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
        validation_rules={
            "autorizacion_endpoint": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
            "verify_ssl": True,
        },
    )
    db.add(settings)
    db.flush()
    return settings


# ===========================================================================
# 1. Validación de RUC Ecuador
# ===========================================================================


class TestValidateRucEc:
    def test_valid_natural_person(self):
        # Cédula 1713175071 es válida (mod-10), RUC = cédula + 001
        assert validate_ruc_ec("1713175071001") is True

    def test_valid_juridical(self):
        # Construido manualmente: 1790000125 verifier=5, sufijo 001
        assert validate_ruc_ec("1790000125001") is True

    def test_too_short(self):
        assert validate_ruc_ec("12345") is False

    def test_non_numeric(self):
        assert validate_ruc_ec("ABCDEFGHIJKLM") is False

    def test_province_zero(self):
        assert validate_ruc_ec("0013175071001") is False

    def test_province_out_of_range(self):
        assert validate_ruc_ec("2613175071001") is False

    def test_suffix_000(self):
        # Sufijo 000 siempre inválido
        assert validate_ruc_ec("1713175071000") is False

    def test_wrong_length_12(self):
        assert validate_ruc_ec("171317507100") is False

    def test_wrong_length_14(self):
        assert validate_ruc_ec("17131750710011") is False


# ===========================================================================
# 2. Generación de clave de acceso
# ===========================================================================


class TestGenerateClaveAcceso:
    def test_length_49(self):
        clave = generate_clave_acceso(_SAMPLE_INVOICE_DATA)
        assert len(clave) == 49, f"Longitud esperada 49, obtenida {len(clave)}: {clave}"

    def test_only_digits(self):
        clave = generate_clave_acceso(_SAMPLE_INVOICE_DATA)
        assert clave.isdigit(), f"La clave debe ser numérica: {clave}"

    def test_check_digit_valid(self):
        clave = generate_clave_acceso(_SAMPLE_INVOICE_DATA)
        base = clave[:-1]
        expected_digit = calcular_digito_verificador_modulo11(base)
        assert int(clave[-1]) == expected_digit

    def test_date_embedded(self):
        clave = generate_clave_acceso(_SAMPLE_INVOICE_DATA)
        # Fecha 24/03/2026 → empieza con 24032026
        assert clave.startswith("24032026")

    def test_ruc_embedded(self):
        clave = generate_clave_acceso(_SAMPLE_INVOICE_DATA)
        assert "1790000125001" in clave


# ===========================================================================
# 3. Generación de XML RIDE
# ===========================================================================


class TestGenerateSriXml:
    def test_generates_valid_xml(self):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        assert xml.startswith("<?xml")
        assert "<invoice" in xml

    def test_contains_empresa_ruc(self):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        assert "1790000125001" in xml

    def test_contains_cliente_nombre(self):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        assert "Cliente Test" in xml

    def test_contains_totales(self):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        assert "100.00" in xml
        assert "15.00" in xml
        assert "115.00" in xml

    def test_contains_detalle_linea(self):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        assert "Servicio de prueba" in xml
        assert "SRV-001" in xml

    def test_iva_codigo_porcentaje_15(self):
        """IVA 15% → codigoPorcentaje = 4."""
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        assert "<codigoPorcentaje>4</codigoPorcentaje>" in xml


# ===========================================================================
# 4. Firma XAdES-BES (SHA-256)
# ===========================================================================


class TestSignXmlXadesBes:
    def test_signed_xml_contains_signature(self, p12_cert_data):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        assert "ds:Signature" in signed or "Signature" in signed

    def test_signed_uses_rsa_sha256(self, p12_cert_data):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        assert "rsa-sha256" in signed

    def test_signed_contains_xades_qualifying_props(self, p12_cert_data):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        assert "QualifyingProperties" in signed

    def test_signed_contains_signing_time(self, p12_cert_data):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        assert "SigningTime" in signed

    def test_signed_contains_x509_certificate(self, p12_cert_data):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        assert "X509Certificate" in signed

    def test_signed_is_valid_xml(self, p12_cert_data):
        from lxml import etree

        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        # No debe lanzar excepción
        root = etree.fromstring(signed.encode("utf-8"))
        assert root is not None

    def test_signed_preserves_invoice_content(self, p12_cert_data):
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, p12_cert_data)
        # Los datos de la factura deben seguir presentes
        assert "1790000125001" in signed
        assert "Cliente Test" in signed

    def test_password_as_bytes(self, p12_cert_data):
        """Acepta password como bytes sin error."""
        data = dict(p12_cert_data)
        data["password"] = b""
        xml = generate_sri_xml(_SAMPLE_INVOICE_DATA)
        signed = sign_xml_xades_bes(xml, data)
        assert "Signature" in signed


# ===========================================================================
# 5. SOAP Envelope builders
# ===========================================================================


class TestSoapEnvelopes:
    def test_reception_envelope_structure(self):
        env = _build_reception_envelope("<invoice/>")
        assert "validarComprobante" in env
        assert "soapenv:Body" in env
        assert "soapenv:Envelope" in env
        # XML base64 del documento firmado
        expected_b64 = base64.b64encode(b"<invoice/>").decode()
        assert expected_b64 in env

    def test_authorization_envelope_structure(self):
        clave = "1234567890123456789012345678901234567890123456789"
        env = _build_authorization_envelope(clave)
        assert "autorizacionComprobante" in env
        assert "claveAccesoComprobante" in env
        assert clave in env


# ===========================================================================
# 6. Parsers SOAP
# ===========================================================================


class TestParseSoapResponses:
    # --- Recepción ---

    def test_parse_reception_recibida(self):
        r = _parse_reception_response(
            "<RespuestaRecepcionComprobante>"
            "<estado>RECIBIDA</estado>"
            "<comprobantes><comprobante>"
            "<claveAcceso>abc123</claveAcceso>"
            "<mensajes/>"
            "</comprobante></comprobantes>"
            "</RespuestaRecepcionComprobante>"
        )
        assert r["status"] == "RECEIVED"
        assert r["clave_acceso"] == "abc123"
        assert r["messages"] == []

    def test_parse_reception_devuelta_with_errors(self):
        r = _parse_reception_response(
            "<RespuestaRecepcionComprobante><estado>DEVUELTA</estado>"
            "<comprobantes><comprobante><claveAcceso>x</claveAcceso>"
            "<mensajes><mensaje><tipo>ERROR</tipo>"
            "<mensaje>RUC emisor invalido</mensaje>"
            "</mensaje></mensajes></comprobante></comprobantes>"
            "</RespuestaRecepcionComprobante>"
        )
        assert r["status"] == "REJECTED"
        assert len(r["messages"]) == 1
        assert r["messages"][0]["tipo"] == "ERROR"
        assert "RUC" in r["messages"][0]["mensaje"]

    def test_parse_reception_invalid_xml(self):
        r = _parse_reception_response("not xml at all!!")
        assert r["status"] == "ERROR"

    def test_parse_reception_http_500_placeholder(self):
        r = _parse_reception_response("")
        assert r["status"] == "ERROR"

    # --- Autorización ---

    def test_parse_authorization_autorizado(self):
        a = _parse_authorization_response(
            "<RespuestaAutorizacionComprobante>"
            "<autorizaciones><autorizacion>"
            "<estado>AUTORIZADO</estado>"
            "<numeroAutorizacion>2403202601171790000125001001001000000001123</numeroAutorizacion>"
            "<fechaAutorizacion>24/03/2026 10:30:00</fechaAutorizacion>"
            "<ambiente>PRUEBAS</ambiente>"
            "<comprobante></comprobante>"
            "<mensajes/></autorizacion></autorizaciones>"
            "</RespuestaAutorizacionComprobante>"
        )
        assert a["status"] == "AUTHORIZED"
        assert a["authorization_number"] is not None
        assert a["authorization_date"] == "24/03/2026 10:30:00"
        assert a["environment"] == "PRUEBAS"

    def test_parse_authorization_no_autorizado(self):
        a = _parse_authorization_response(
            "<RespuestaAutorizacionComprobante>"
            "<autorizaciones><autorizacion>"
            "<estado>NO AUTORIZADO</estado>"
            "<mensajes><mensaje><tipo>ERROR</tipo>"
            "<mensaje>CLAVE ACCESO NO EXISTE</mensaje></mensaje></mensajes>"
            "</autorizacion></autorizaciones>"
            "</RespuestaAutorizacionComprobante>"
        )
        assert a["status"] == "REJECTED"
        assert "CLAVE ACCESO" in (a["message"] or "")

    def test_parse_authorization_invalid_xml(self):
        a = _parse_authorization_response("garbage!!!")
        assert a["status"] == "ERROR"


# ===========================================================================
# 7. SRIService.get_settings
# ===========================================================================


class TestSRIServiceGetSettings:
    def test_get_settings_ok(self, db: Session, tenant_id, sri_settings):
        settings = SRIService.get_settings(db, tenant_id, "EC")
        assert settings.is_enabled is True
        assert settings.country == "EC"

    def test_get_settings_not_configured(self, db: Session):
        with pytest.raises(ValueError, match="not configured"):
            SRIService.get_settings(db, uuid4(), "EC")

    def test_get_settings_disabled(self, db: Session, tenant_id):
        db.add(
            EInvoicingCountrySettings(
                tenant_id=tenant_id,
                country="EC",
                is_enabled=False,
                environment="STAGING",
            )
        )
        db.flush()
        with pytest.raises(ValueError, match="not enabled"):
            SRIService.get_settings(db, tenant_id, "EC")

    def test_endpoints_from_settings(self, db: Session, tenant_id, sri_settings):
        settings = SRIService.get_settings(db, tenant_id, "EC")
        endpoints = SRIService._get_endpoints(settings)
        assert "celcer.sri.gob.ec" in endpoints["recepcion"]
        assert "celcer.sri.gob.ec" in endpoints["autorizacion"]

    def test_endpoints_default_sandbox(self, db: Session, tenant_id):
        # Sin api_endpoint configureado → defaults sandbox
        settings = EInvoicingCountrySettings(
            tenant_id=tenant_id,
            country="EC",
            is_enabled=True,
            environment="STAGING",
        )
        db.add(settings)
        db.flush()
        endpoints = SRIService._get_endpoints(settings)
        assert "celcer.sri.gob.ec" in endpoints["recepcion"]

    def test_endpoints_production(self, db: Session, tenant_id):
        settings = EInvoicingCountrySettings(
            tenant_id=tenant_id,
            country="EC",
            is_enabled=True,
            environment="PRODUCTION",
        )
        db.add(settings)
        db.flush()
        endpoints = SRIService._get_endpoints(settings)
        assert "cel.sri.gob.ec" in endpoints["recepcion"]
        assert "celcer" not in endpoints["recepcion"]


# ===========================================================================
# 8. SRIService.validate_invoice_data
# ===========================================================================


class TestSRIServiceValidation:
    def test_valid_invoice(self):
        errors = SRIService.validate_invoice_data(_SAMPLE_INVOICE_DATA)
        assert errors == []

    def test_invalid_empresa_ruc(self):
        data = {**_SAMPLE_INVOICE_DATA, "empresa": {"nombre": "X", "ruc": "INVALID", "direccion": ""}}
        errors = SRIService.validate_invoice_data(data)
        assert any("ruc_empresa" in e for e in errors)

    def test_missing_numero(self):
        data = {**_SAMPLE_INVOICE_DATA, "numero": ""}
        errors = SRIService.validate_invoice_data(data)
        assert "numero_factura_requerido" in errors

    def test_missing_lines(self):
        data = {**_SAMPLE_INVOICE_DATA, "lines": []}
        errors = SRIService.validate_invoice_data(data)
        assert "lineas_factura_requeridas" in errors


# ===========================================================================
# 9. SRIService.send_reception — con httpx mockeado
# ===========================================================================


class TestSRIServiceSendReception:
    def _make_settings(self):
        s = MagicMock(spec=EInvoicingCountrySettings)
        s.environment = "STAGING"
        s.api_endpoint = None
        s.validation_rules = {"verify_ssl": False}
        return s

    def test_send_reception_received(self):
        settings = self._make_settings()
        soap_response = (
            "<RespuestaRecepcionComprobante><estado>RECIBIDA</estado>"
            "<comprobantes><comprobante><claveAcceso>abc</claveAcceso>"
            "<mensajes/></comprobante></comprobantes></RespuestaRecepcionComprobante>"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = soap_response

        with patch("app.modules.einvoicing.application.sri_service.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
            result = SRIService.send_reception(settings, "<invoice/>")

        assert result["status"] == "RECEIVED"
        assert result["clave_acceso"] == "abc"

    def test_send_reception_http_error(self):
        settings = self._make_settings()
        with patch("app.modules.einvoicing.application.sri_service.httpx.Client") as mock_client:
            import httpx

            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
                "Connection refused"
            )
            result = SRIService.send_reception(settings, "<invoice/>")

        assert result["status"] == "ERROR"
        assert "Connection" in result.get("message", "")

    def test_send_reception_non_200(self):
        settings = self._make_settings()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"

        with patch("app.modules.einvoicing.application.sri_service.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
            result = SRIService.send_reception(settings, "<invoice/>")

        assert result["status"] == "ERROR"
        assert "503" in result["message"]


# ===========================================================================
# 10. SRIService.poll_authorization — con httpx mockeado
# ===========================================================================


class TestSRIServicePollAuthorization:
    def _make_settings(self):
        s = MagicMock(spec=EInvoicingCountrySettings)
        s.environment = "STAGING"
        s.api_endpoint = None
        s.validation_rules = {"verify_ssl": False}
        return s

    def test_poll_authorized(self):
        settings = self._make_settings()
        soap_resp = (
            "<RespuestaAutorizacionComprobante><autorizaciones><autorizacion>"
            "<estado>AUTORIZADO</estado>"
            "<numeroAutorizacion>AUTHNUM001</numeroAutorizacion>"
            "<fechaAutorizacion>24/03/2026 10:00:00</fechaAutorizacion>"
            "<ambiente>PRUEBAS</ambiente>"
            "<comprobante></comprobante><mensajes/>"
            "</autorizacion></autorizaciones></RespuestaAutorizacionComprobante>"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = soap_resp

        with patch("app.modules.einvoicing.application.sri_service.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
            result = SRIService.poll_authorization(settings, "abc123")

        assert result["status"] == "AUTHORIZED"
        assert result["authorization_number"] == "AUTHNUM001"

    def test_poll_not_authorized(self):
        settings = self._make_settings()
        soap_resp = (
            "<RespuestaAutorizacionComprobante><autorizaciones><autorizacion>"
            "<estado>NO AUTORIZADO</estado>"
            "<mensajes><mensaje><tipo>ERROR</tipo>"
            "<mensaje>EN PROCESO</mensaje></mensaje></mensajes>"
            "</autorizacion></autorizaciones></RespuestaAutorizacionComprobante>"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = soap_resp

        with patch("app.modules.einvoicing.application.sri_service.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
            result = SRIService.poll_authorization(settings, "abc123")

        assert result["status"] == "REJECTED"


# ===========================================================================
# 11. Task sign_and_send_sri_task — con todos los deps mockeados
# ===========================================================================


class TestSignAndSendSriTask:
    def _make_invoice_mock(self, tenant_id):
        from datetime import date

        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.tenant_id = tenant_id
        invoice.numero = "001-001-000000001"
        invoice.fecha = date(2026, 3, 24)
        invoice.issue_date = date(2026, 3, 24)
        invoice.subtotal = 100.0
        invoice.iva = 15.0
        invoice.total = 115.0
        invoice.lines = [
            MagicMock(
                cantidad=1,
                precio_unitario=100.0,
                total=100.0,
                descripcion="Servicio",
                description="Servicio",
                sku="SRV-001",
            )
        ]
        tenant = MagicMock()
        tenant.name = "Empresa Test S.A."
        tenant.tax_id = "1790000125001"
        tenant.address = "Quito"
        invoice.tenant = tenant

        customer = MagicMock()
        customer.name = "Cliente Test"
        customer.tax_id = "1713175071001"
        customer.identificacion = "1713175071001"
        customer.email = "cliente@test.ec"
        invoice.customer = customer
        return invoice

    def _patch_task(self, tid, invoice, settings_mock, cert_data, reception_result):
        """Contexto común para parchear las deps del task."""
        db_mock = MagicMock()
        db_mock.execute.return_value.scalar_one_or_none.return_value = invoice

        # SessionLocal se importa localmente dentro del task; hay que parchear
        # el módulo origen donde vive la clase.
        return (
            patch("app.config.database.SessionLocal", return_value=db_mock),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.get_settings",
                return_value=settings_mock,
            ),
            patch("app.workers.einvoicing_tasks._load_cert_sync", return_value=cert_data),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.send_reception",
                return_value=reception_result,
            ),
            db_mock,
        )

    def test_task_success_queues_poll(self, p12_cert_data):
        tid = uuid4()
        invoice = self._make_invoice_mock(tid)
        settings_mock = MagicMock(spec=EInvoicingCountrySettings)
        settings_mock.environment = "STAGING"
        settings_mock.api_endpoint = None
        settings_mock.validation_rules = {"verify_ssl": False}
        settings_mock.is_enabled = True

        db_mock = MagicMock()
        db_mock.execute.return_value.scalar_one_or_none.return_value = invoice

        with (
            patch("app.config.database.SessionLocal", return_value=db_mock),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.get_settings",
                return_value=settings_mock,
            ),
            patch("app.workers.einvoicing_tasks._load_cert_sync", return_value=p12_cert_data),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.send_reception",
                return_value={"status": "RECEIVED", "clave_acceso": "abc", "messages": []},
            ),
            patch("app.workers.einvoicing_tasks.poll_sri_authorization_task") as mock_poll,
        ):
            from app.workers.einvoicing_tasks import sign_and_send_sri_task

            result = sign_and_send_sri_task(str(invoice.id), str(tid))

        assert result["status"] == "SENT"
        assert result["clave_acceso"] is not None
        assert len(result["clave_acceso"]) == 49
        mock_poll.apply_async.assert_called_once()

    def test_task_rejected_does_not_queue_poll(self, p12_cert_data):
        tid = uuid4()
        invoice = self._make_invoice_mock(tid)
        settings_mock = MagicMock(spec=EInvoicingCountrySettings)
        settings_mock.environment = "STAGING"
        settings_mock.api_endpoint = None
        settings_mock.validation_rules = {"verify_ssl": False}
        settings_mock.is_enabled = True

        db_mock = MagicMock()
        db_mock.execute.return_value.scalar_one_or_none.return_value = invoice

        with (
            patch("app.config.database.SessionLocal", return_value=db_mock),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.get_settings",
                return_value=settings_mock,
            ),
            patch("app.workers.einvoicing_tasks._load_cert_sync", return_value=p12_cert_data),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.send_reception",
                return_value={
                    "status": "REJECTED",
                    "clave_acceso": "abc",
                    "messages": [{"tipo": "ERROR", "mensaje": "RUC invalido", "info": ""}],
                },
            ),
            patch("app.workers.einvoicing_tasks.poll_sri_authorization_task") as mock_poll,
        ):
            from app.workers.einvoicing_tasks import sign_and_send_sri_task

            result = sign_and_send_sri_task(str(invoice.id), str(tid))

        assert result["status"] == "REJECTED"
        mock_poll.apply_async.assert_not_called()

    def test_task_invalid_ruc_raises(self, p12_cert_data):
        tid = uuid4()
        invoice = self._make_invoice_mock(tid)
        invoice.tenant = MagicMock(name="X", tax_id="1234567890123", address="")
        settings_mock = MagicMock(spec=EInvoicingCountrySettings)
        settings_mock.environment = "STAGING"
        settings_mock.api_endpoint = None
        settings_mock.validation_rules = {}
        settings_mock.is_enabled = True

        db_mock = MagicMock()
        db_mock.execute.return_value.scalar_one_or_none.return_value = invoice

        with (
            patch("app.config.database.SessionLocal", return_value=db_mock),
            patch(
                "app.modules.einvoicing.application.sri_service.SRIService.get_settings",
                return_value=settings_mock,
            ),
            patch("app.workers.einvoicing_tasks._load_cert_sync", return_value=p12_cert_data),
        ):
            from app.workers.einvoicing_tasks import sign_and_send_sri_task

            with pytest.raises(ValueError, match="RUC"):
                sign_and_send_sri_task(str(invoice.id), str(tid))


# ===========================================================================
# 12. SRISubmission model (DB)
# ===========================================================================


class TestSRISubmissionModel:
    def _now(self):
        from datetime import UTC, datetime

        return datetime.now(UTC)

    def test_create_submission(self, db: Session, tenant_id):
        now = self._now()
        sub = SRISubmission(
            tenant_id=tenant_id,
            invoice_id=uuid4(),
            status="SENT",
            receipt_number="1234567890123456789012345678901234567890123456789",
            payload="<signed_xml/>",
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
        db.flush()
        assert sub.id is not None
        assert sub.status == "SENT"
        assert sub.authorization_number is None

    def test_update_to_authorized(self, db: Session, tenant_id):
        now = self._now()
        sub = SRISubmission(
            tenant_id=tenant_id,
            invoice_id=uuid4(),
            status="SENT",
            receipt_number="1234567890123456789012345678901234567890123456789",
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
        db.flush()

        sub.status = "AUTHORIZED"
        sub.authorization_number = "AUTHNUM-001"
        sub.response = "<authorized_xml/>"
        db.flush()

        assert sub.status == "AUTHORIZED"
        assert sub.authorization_number == "AUTHNUM-001"
