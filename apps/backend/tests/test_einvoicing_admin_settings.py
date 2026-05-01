"""Tests para endpoints admin de E-Invoicing.

Cubre:
- POST /api/v1/admin/companies/{tenant_id}/einvoicing/{type}/certificate
- GET  /api/v1/admin/companies/{tenant_id}/einvoicing/{type}/settings
- PUT  /api/v1/admin/companies/{tenant_id}/einvoicing/{type}/settings
- Scope admin (sin token → 401/403)
"""

from __future__ import annotations

import os
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("TEST_MINIMAL", "1")

import pytest

from app.models.einvoicing.country_settings import EInvoicingCountrySettings
from app.models.tenant import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _admin_headers(client, superuser_factory) -> dict[str, str]:
    password = "secret123"
    superuser_factory(
        email="einvoicing-admin@example.com",
        username="einvoicing_admin",
        password=password,
    )
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "einvoicing-admin@example.com", "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _tenant_id(db) -> str:
    """Devuelve un tenant existente (creando uno si hace falta)."""
    t = db.query(Tenant).first()
    if not t:
        t = Tenant(id=uuid4(), name="Test Co", slug=f"testco-{uuid4().hex[:6]}")
        db.add(t)
        db.commit()
        db.refresh(t)
    return str(t.id)


# ---------------------------------------------------------------------------
# Scope admin
# ---------------------------------------------------------------------------


def test_settings_endpoints_require_admin_scope(client, db):
    tid = _tenant_id(db)
    # Sin Authorization header → 401/403
    res = client.get(f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings")
    assert res.status_code in (401, 403), res.text

    res = client.put(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings",
        json={"is_enabled": True},
    )
    assert res.status_code in (401, 403), res.text

    res = client.post(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/certificate",
        files={"file": ("c.p12", b"x", "application/x-pkcs12")},
        data={"password": "x"},
    )
    assert res.status_code in (401, 403), res.text


# ---------------------------------------------------------------------------
# GET / PUT settings (SRI y SII)
# ---------------------------------------------------------------------------


def test_get_settings_404_when_not_configured(client, db, superuser_factory):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.get(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings", headers=headers
    )
    assert res.status_code == 404, res.text
    assert res.json()["detail"] == "einvoicing_settings_not_found"


def test_put_settings_creates_and_then_get_returns_them_sri(client, db, superuser_factory):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)

    res = client.put(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings",
        headers=headers,
        json={
            "is_enabled": True,
            "environment": "PRODUCTION",
            "api_endpoint": "https://cel.sri.gob.ec/x?wsdl",
            "username": "user-sri",
            "max_retries": 7,
            "retry_backoff_seconds": 120,
            "validation_rules": {"recepcion_endpoint": "https://x"},
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["country"] == "EC"
    assert body["type"] == "sri"
    assert body["is_enabled"] is True
    assert body["environment"] == "PRODUCTION"
    assert body["api_endpoint"] == "https://cel.sri.gob.ec/x?wsdl"
    assert body["username"] == "user-sri"
    assert body["max_retries"] == 7
    assert body["retry_backoff_seconds"] == 120
    assert body["validation_rules"] == {"recepcion_endpoint": "https://x"}

    # Persistencia en BD
    row = (
        db.query(EInvoicingCountrySettings)
        .filter_by(tenant_id=tid, country="EC")
        .one()
    )
    assert row.is_enabled is True
    assert row.environment == "PRODUCTION"

    # GET ahora retorna 200
    res = client.get(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings", headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["environment"] == "PRODUCTION"


def test_put_settings_creates_sii_independently(client, db, superuser_factory):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)

    res = client.put(
        f"/api/v1/admin/companies/{tid}/einvoicing/sii/settings",
        headers=headers,
        json={"is_enabled": True, "environment": "STAGING"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["country"] == "ES"
    assert body["type"] == "sii"
    assert body["environment"] == "STAGING"

    # GET sri todavía 404 (independiente)
    res = client.get(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings", headers=headers
    )
    assert res.status_code == 404


def test_put_settings_rejects_invalid_environment(client, db, superuser_factory):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.put(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings",
        headers=headers,
        json={"environment": "BANANA"},
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "invalid_environment"


def test_settings_response_does_not_leak_password(client, db, superuser_factory):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    # Crear settings con password en BD
    row = EInvoicingCountrySettings(
        tenant_id=tid,
        country="EC",
        is_enabled=True,
        environment="STAGING",
        password_encrypted="should-not-leak",
        certificate_password_encrypted="also-secret",
    )
    db.add(row)
    db.commit()

    res = client.get(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/settings", headers=headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    payload_str = res.text
    assert "should-not-leak" not in payload_str
    assert "also-secret" not in payload_str
    # Solo señal booleana
    assert body["has_password"] is True


def test_invalid_type_returns_422(client, db, superuser_factory):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.get(
        f"/api/v1/admin/companies/{tid}/einvoicing/banana/settings", headers=headers
    )
    # FastAPI valida pattern en Path → 422
    assert res.status_code == 422


def test_invalid_tenant_id_returns_400(client, superuser_factory):
    headers = _admin_headers(client, superuser_factory)
    res = client.get(
        "/api/v1/admin/companies/not-a-uuid/einvoicing/sri/settings", headers=headers
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "invalid_tenant_id"


# ---------------------------------------------------------------------------
# POST certificate upload
# ---------------------------------------------------------------------------


@pytest.fixture
def stubbed_certificate_manager():
    """Mockea certificate_manager.store_certificate (async) sin tocar disco/cripto."""
    from app.modules.einvoicing.interface.http import admin as admin_mod

    async def fake_store(*, tenant_id, country, cert_data, password, cert_type="p12"):
        # Ejercer parámetros para detectar regresiones de signatura
        assert cert_data, "cert_data must not be empty"
        assert password, "password required"
        return f"/tmp/{country.lower()}-{tenant_id}.p12"

    with patch.object(
        admin_mod.certificate_manager, "store_certificate", side_effect=fake_store
    ) as m:
        yield m


def test_upload_certificate_success_sri(
    client, db, superuser_factory, stubbed_certificate_manager
):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)

    res = client.post(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/certificate",
        headers=headers,
        files={"file": ("acme.p12", b"\x30\x82binary", "application/x-pkcs12")},
        data={"password": "p4ss", "alias": "ACME-Cert"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["country"] == "EC"
    assert body["type"] == "sri"
    assert body["alias"] == "ACME-Cert"
    assert body["cert_ref"].endswith(".p12")

    # store_certificate fue llamado con los kwargs esperados
    stubbed_certificate_manager.assert_called_once()
    kwargs = stubbed_certificate_manager.call_args.kwargs
    assert str(kwargs["tenant_id"]) == tid
    assert kwargs["country"] == "EC"
    assert kwargs["password"] == "p4ss"


def test_upload_certificate_success_sii(
    client, db, superuser_factory, stubbed_certificate_manager
):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.post(
        f"/api/v1/admin/companies/{tid}/einvoicing/sii/certificate",
        headers=headers,
        files={"file": ("c.pfx", b"binary", "application/x-pkcs12")},
        data={"password": "p"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["country"] == "ES"
    kwargs = stubbed_certificate_manager.call_args.kwargs
    assert kwargs["country"] == "ES"


def test_upload_certificate_rejects_bad_extension(
    client, db, superuser_factory, stubbed_certificate_manager
):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.post(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/certificate",
        headers=headers,
        files={"file": ("evil.txt", b"x", "text/plain")},
        data={"password": "p"},
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "invalid_file_extension"
    stubbed_certificate_manager.assert_not_called()


def test_upload_certificate_rejects_empty_file(
    client, db, superuser_factory, stubbed_certificate_manager
):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.post(
        f"/api/v1/admin/companies/{tid}/einvoicing/sri/certificate",
        headers=headers,
        files={"file": ("c.p12", b"", "application/x-pkcs12")},
        data={"password": "p"},
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "empty_certificate_file"
    stubbed_certificate_manager.assert_not_called()


def test_upload_certificate_invalid_propagates_400(client, db, superuser_factory):
    """Si store_certificate lanza ValueError (cert inválido) → 400."""
    from app.modules.einvoicing.interface.http import admin as admin_mod

    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)

    async def bad_store(**_kw):
        raise ValueError("Certificado inválido: bad password")

    with patch.object(admin_mod.certificate_manager, "store_certificate", side_effect=bad_store):
        res = client.post(
            f"/api/v1/admin/companies/{tid}/einvoicing/sri/certificate",
            headers=headers,
            files={"file": ("c.p12", b"binary", "application/x-pkcs12")},
            data={"password": "wrong"},
        )
    assert res.status_code == 400, res.text
    assert "Certificado inválido" in res.json()["detail"]


def test_upload_certificate_invalid_type_404_or_422(
    client, db, superuser_factory, stubbed_certificate_manager
):
    tid = _tenant_id(db)
    headers = _admin_headers(client, superuser_factory)
    res = client.post(
        f"/api/v1/admin/companies/{tid}/einvoicing/banana/certificate",
        headers=headers,
        files={"file": ("c.p12", b"x", "application/x-pkcs12")},
        data={"password": "p"},
    )
    # Pattern del path → 422
    assert res.status_code == 422
    stubbed_certificate_manager.assert_not_called()
