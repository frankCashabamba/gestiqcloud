"""Debug test para verificar autenticación"""
import pytest
from uuid import uuid4


@pytest.mark.skip(reason="Debug test - not needed for CI")
def test_debug_auth_headers(client, db, auth_headers):
    """Test simple para debugear autenticación"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    
    # Verificar que tenant se creó
    from sqlalchemy import text
    row = db.execute(
        text("SELECT id, empresa_id, slug FROM tenants WHERE id = :tid"),
        {"tid": tenant_id}
    ).first()
    
    print(f"\n=== DEBUG AUTH ===")
    print(f"tenant_id: {tenant_id}")
    print(f"Tenant in DB: {row}")
    print(f"Headers: {headers}")
    
    assert row is not None, "Tenant should exist in DB"
    assert row[0] == tenant_id
    
    # Test simple: GET /api/v1/pos/registers
    response = client.get("/api/v1/pos/registers", headers=headers)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
