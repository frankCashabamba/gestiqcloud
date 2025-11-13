from starlette.responses import Response


def test_cookie_helpers_set_secure_attributes(monkeypatch):
    # Arrange production-like cookie settings
    from app.config.settings import settings

    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "COOKIE_SAMESITE", "none")
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", ".example.com")

    from app.core.auth_http import set_refresh_cookie, set_access_cookie

    resp = Response()

    # Act
    set_refresh_cookie(resp, "rttoken", path="/api/v1/tenant/auth")
    set_access_cookie(resp, "attoken", path="/")

    # Assert
    cookies = resp.headers.getlist("set-cookie")
    # Two cookies expected
    assert any(c.startswith("refresh_token=") for c in cookies)
    assert any(c.startswith("access_token=") for c in cookies)

    # Verify attributes per cookie name
    for c in cookies:
        assert "; Domain=.example.com" in c
        assert "; Secure" in c
        assert "; HttpOnly" in c
        if c.startswith("refresh_token="):
            # Cross-site allowed for refresh
            assert "; SameSite=None" in c
        if c.startswith("access_token="):
            # Lax for access token
            assert "; SameSite=Lax" in c
