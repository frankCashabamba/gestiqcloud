"""
Tests para autenticación con cookies HttpOnly.
Coverage: auth_cookies.py + security_cookies.py
"""

from fastapi.responses import Response

from app.core.auth_cookies import (
    clear_auth_cookies,
    get_token_from_cookie,
    get_token_from_cookie_or_header,
    set_access_token_cookie,
    set_refresh_token_cookie,
)


class TestSetCookies:
    """Tests para seteo de cookies"""

    def test_set_access_token_cookie(self):
        """Access token debe setearse en cookie HttpOnly"""
        response = Response()
        token = "test_access_token_123"

        set_access_token_cookie(response, token)

        # Verificar que cookie existe
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_header
        assert token in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "SameSite=lax" in set_cookie_header or "samesite=lax" in set_cookie_header.lower()

    def test_set_refresh_token_cookie(self):
        """Refresh token debe setearse en cookie HttpOnly"""
        response = Response()
        token = "test_refresh_token_456"

        set_refresh_token_cookie(response, token)

        set_cookie_header = response.headers.get("set-cookie", "")
        assert "refresh_token" in set_cookie_header
        assert token in set_cookie_header
        assert "HttpOnly" in set_cookie_header

    def test_clear_auth_cookies(self):
        """Debe eliminar todas las cookies de autenticación"""
        response = Response()

        clear_auth_cookies(response)

        # Verificar que ambas cookies se eliminan
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_header or "refresh_token" in set_cookie_header


class TestGetCookies:
    """Tests para extracción de cookies"""

    def test_get_token_from_cookie(self):
        """Debe extraer token desde cookie"""
        # Mock request con cookie

        class MockRequest:
            def __init__(self):
                self.cookies = {"access_token": "token_from_cookie"}

        request = MockRequest()
        token = get_token_from_cookie(request)  # type: ignore

        assert token == "token_from_cookie"

    def test_get_token_from_cookie_missing(self):
        """Debe retornar None si no hay cookie"""

        class MockRequest:
            def __init__(self):
                self.cookies = {}

        request = MockRequest()
        token = get_token_from_cookie(request)  # type: ignore

        assert token is None


class TestMigrationCompat:
    """Tests para compatibilidad durante migración"""

    def test_get_token_from_cookie_or_header_prefers_cookie(self):
        """Debe preferir cookie sobre header"""

        class MockRequest:
            def __init__(self):
                self.cookies = {"access_token": "token_from_cookie"}
                self.headers = {"Authorization": "Bearer token_from_header"}

        request = MockRequest()
        token = get_token_from_cookie_or_header(request)  # type: ignore

        # Debe retornar cookie (preferencia)
        assert token == "token_from_cookie"

    def test_get_token_from_header_fallback(self):
        """Debe usar header si no hay cookie (fallback)"""

        class MockRequest:
            def __init__(self):
                self.cookies = {}
                self.headers = {"Authorization": "Bearer token_from_header"}

        request = MockRequest()
        token = get_token_from_cookie_or_header(request)  # type: ignore

        assert token == "token_from_header"

    def test_get_token_returns_none_if_both_missing(self):
        """Debe retornar None si no hay token en cookie ni header"""

        class MockRequest:
            def __init__(self):
                self.cookies = {}
                self.headers = {}

        request = MockRequest()
        token = get_token_from_cookie_or_header(request)  # type: ignore

        assert token is None
