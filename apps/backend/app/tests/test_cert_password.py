"""
Tests para validar que CERT_PASSWORD se recupera correctamente
"""

import os
import pytest
from app.services.secrets import get_certificate_password


class TestCertificatePasswordRetrieval:
    """Test certificate password retrieval from multiple sources"""
    
    def test_get_cert_password_from_env_var(self):
        """Test retrieving password from environment variable"""
        # Set env var
        os.environ["CERT_PASSWORD_tenant-123_ECU"] = "password123"
        
        try:
            password = get_certificate_password("tenant-123", "ECU")
            assert password == "password123"
        finally:
            del os.environ["CERT_PASSWORD_tenant-123_ECU"]
    
    def test_get_cert_password_missing_raises_error(self):
        """Test that missing password raises ValueError"""
        # Ensure env var doesn't exist
        env_key = "CERT_PASSWORD_nonexistent_ECU"
        if env_key in os.environ:
            del os.environ[env_key]
        
        with pytest.raises(ValueError) as exc_info:
            get_certificate_password("nonexistent", "ECU")
        
        assert "Certificate password not found" in str(exc_info.value)
        assert "CERT_PASSWORD_NONEXISTENT_ECU" in str(exc_info.value)
    
    def test_get_cert_password_different_countries(self):
        """Test that different countries use different passwords"""
        os.environ["CERT_PASSWORD_tenant-456_ECU"] = "ecuador_password"
        os.environ["CERT_PASSWORD_tenant-456_ESP"] = "spain_password"
        
        try:
            ecu_pwd = get_certificate_password("tenant-456", "ECU")
            esp_pwd = get_certificate_password("tenant-456", "ESP")
            
            assert ecu_pwd == "ecuador_password"
            assert esp_pwd == "spain_password"
        finally:
            del os.environ["CERT_PASSWORD_tenant-456_ECU"]
            del os.environ["CERT_PASSWORD_tenant-456_ESP"]
    
    def test_get_cert_password_format_consistency(self):
        """Test that password format follows convention"""
        password = "test_password_123"
        os.environ["CERT_PASSWORD_test-tenant_ECU"] = password
        
        try:
            retrieved = get_certificate_password("test-tenant", "ECU")
            assert retrieved == password
        finally:
            del os.environ["CERT_PASSWORD_test-tenant_ECU"]
