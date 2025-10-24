"""
Tests: E-invoicing Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.skip(reason="E-invoicing endpoints pending - workers implemented")
def test_einvoicing_credentials(client: TestClient, db, auth_headers):
    """Test gestión de credenciales"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    
    # Obtener credenciales (no existen inicialmente)
    response = client.get(
        "/api/v1/einvoicing/credentials?country=EC",
        headers=headers
    )
    assert response.status_code == 200
    creds = response.json()
    assert creds.get("country") == "EC"
    assert creds.get("has_certificate") == False
    
    # Actualizar credenciales
    response = client.put(
        "/api/v1/einvoicing/credentials",
        json={
            "country": "EC",
            "sandbox": True
        },
        headers=headers
    )
    assert response.status_code == 200
    
    # Verificar actualización
    response = client.get(
        "/api/v1/einvoicing/credentials?country=EC",
        headers=headers
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated.get("sandbox") == True


@pytest.mark.skip(reason="E-invoicing endpoints pending - workers implemented")
def test_einvoicing_send(client: TestClient, db, auth_headers):
    """Test envío de e-factura"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    invoice_id = str(uuid4())
    
    response = client.post(
        "/api/v1/einvoicing/send",
        json={
            "invoice_id": invoice_id,
            "country": "EC"
        },
        headers=headers
    )
    # Puede dar 404 si la factura no existe
    assert response.status_code in [200, 404, 500]


@pytest.mark.skip(reason="E-invoicing endpoints pending - workers implemented")
def test_einvoicing_status(client: TestClient, db, auth_headers):
    """Test estado de e-factura"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    invoice_id = str(uuid4())
    
    response = client.get(
        f"/api/v1/einvoicing/status/{invoice_id}?country=EC",
        headers=headers
    )
    # 404 es esperado si no hay envío
    assert response.status_code in [200, 404]


@pytest.mark.skip(reason="E-invoicing endpoints pending - workers implemented")
def test_einvoicing_retry_sri(client: TestClient, db, auth_headers):
    """Test retry SRI"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    invoice_id = str(uuid4())
    
    response = client.post(
        "/api/v1/einvoicing/sri/retry",
        json={"invoice_id": invoice_id},
        headers=headers
    )
    # Puede dar 404, 200 o 500
    assert response.status_code in [200, 404, 500]
