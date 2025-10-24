"""
Conftest para tests SPEC-1 y nuevos endpoints
Mock de autenticación para tests sin DB compleja
"""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock de autenticación para tests"""
    with patch('app.middleware.tenant.ensure_tenant') as mock_ensure:
        mock_ensure.return_value = "123e4567-e89b-12d3-a456-426614174000"
        yield mock_ensure


@pytest.fixture(autouse=True)
def mock_get_current_user():
    """Mock de usuario actual"""
    with patch('app.middleware.tenant.get_current_user') as mock_user:
        mock_user.return_value = {
            "id": 1,
            "username": "testuser",
            "tenant_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        yield mock_user


@pytest.fixture
def auth_headers():
    """Headers con autenticación mock"""
    return {
        "X-Tenant-ID": "123e4567-e89b-12d3-a456-426614174000",
        "Authorization": "Bearer mock-token"
    }
