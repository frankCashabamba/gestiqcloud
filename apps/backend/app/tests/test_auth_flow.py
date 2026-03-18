"""
C-T3: Tests del flujo de autenticación.

Cubre:
- LoginUseCase: validación de credenciales, rate limiting, emisión de tokens
- RefreshTokenUseCase: rotación segura, detección de replay attacks
- LogoutUseCase: revocación de familia de tokens
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.identity.application.use_cases import (
    LoginUseCase,
    LogoutUseCase,
    RefreshTokenUseCase,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_user(email: str = "test@empresa.com", is_active: bool = True):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.password_hash = "hashed_password"
    user.name = "Test User"
    user.is_active = is_active
    return user


def _make_rate_limiter(is_locked: bool = False):
    rl = MagicMock()
    status = MagicMock()
    status.is_locked = is_locked
    status.retry_after = 60
    rl.check.return_value = status
    return rl


def _make_token_service(access_token: str = "access.jwt", refresh_token: str = "refresh.jwt"):
    ts = MagicMock()
    ts.issue_access.return_value = access_token
    ts.issue_refresh.return_value = refresh_token
    return ts


def _make_refresh_repo(family_id: str | None = None, is_reused: bool = False):
    repo = MagicMock()
    repo.create_family.return_value = family_id or str(uuid.uuid4())
    repo.is_reused_or_revoked.return_value = is_reused
    repo.get_family.return_value = family_id
    return repo


def _fake_request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


# ============================================================================
# LoginUseCase
# ============================================================================


class TestLoginUseCase:

    def test_raises_when_rate_limited(self):
        rl = _make_rate_limiter(is_locked=True)
        uc = LoginUseCase(
            token_service=MagicMock(),
            password_hasher=MagicMock(),
            rate_limiter=rl,
            refresh_repo=MagicMock(),
        )
        with pytest.raises(ValueError, match="bloqueada"):
            uc.execute(
                user=_make_user(),
                password="wrongpass",
                request=_fake_request(),
                user_agent="test",
                ip_address="127.0.0.1",
            )

    def test_raises_on_wrong_password(self):
        pw_hasher = MagicMock()
        pw_hasher.verify.return_value = (False, "invalid_password")

        uc = LoginUseCase(
            token_service=MagicMock(),
            password_hasher=pw_hasher,
            rate_limiter=_make_rate_limiter(),
            refresh_repo=MagicMock(),
        )
        with pytest.raises(ValueError, match="incorrecta"):
            uc.execute(
                user=_make_user(),
                password="wrongpassword",
                request=_fake_request(),
                user_agent="test",
                ip_address="127.0.0.1",
            )

    def test_increments_fail_counter_on_wrong_password(self):
        pw_hasher = MagicMock()
        pw_hasher.verify.return_value = (False, "invalid_password")
        rl = _make_rate_limiter()

        uc = LoginUseCase(
            token_service=MagicMock(),
            password_hasher=pw_hasher,
            rate_limiter=rl,
            refresh_repo=MagicMock(),
        )
        try:
            uc.execute(
                user=_make_user(),
                password="wrong",
                request=_fake_request(),
                user_agent="test",
                ip_address="127.0.0.1",
            )
        except ValueError:
            pass

        rl.incr_fail.assert_called_once()

    def test_successful_login_returns_tokens(self):
        pw_hasher = MagicMock()
        pw_hasher.verify.return_value = (True, None)
        token_service = _make_token_service("acc.tok", "ref.tok")
        refresh_repo = _make_refresh_repo("fam-123")
        tenant_id = str(uuid.uuid4())

        uc = LoginUseCase(
            token_service=token_service,
            password_hasher=pw_hasher,
            rate_limiter=_make_rate_limiter(),
            refresh_repo=refresh_repo,
        )
        result = uc.execute(
            user=_make_user("user@co.com"),
            password="validpassword",
            request=_fake_request(),
            user_agent="Mozilla",
            ip_address="10.0.0.1",
            tenant_id=tenant_id,
        )

        assert result["access_token"] == "acc.tok"
        assert result["refresh_token"] == "ref.tok"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 900
        assert result["user"]["email"] == "user@co.com"

    def test_successful_login_resets_rate_limiter(self):
        pw_hasher = MagicMock()
        pw_hasher.verify.return_value = (True, None)
        rl = _make_rate_limiter()

        uc = LoginUseCase(
            token_service=_make_token_service(),
            password_hasher=pw_hasher,
            rate_limiter=rl,
            refresh_repo=_make_refresh_repo(),
        )
        uc.execute(
            user=_make_user(),
            password="validpass",
            request=_fake_request(),
            user_agent="test",
            ip_address="127.0.0.1",
        )

        rl.reset.assert_called_once()

    def test_tenant_scope_in_access_token(self):
        pw_hasher = MagicMock()
        pw_hasher.verify.return_value = (True, None)
        token_service = MagicMock()
        token_service.issue_access.return_value = "tok"
        token_service.issue_refresh.return_value = "ref"

        uc = LoginUseCase(
            token_service=token_service,
            password_hasher=pw_hasher,
            rate_limiter=_make_rate_limiter(),
            refresh_repo=_make_refresh_repo(),
        )
        uc.execute(
            user=_make_user(),
            password="pass",
            request=_fake_request(),
            user_agent="test",
            ip_address="127.0.0.1",
            tenant_id="tid-123",
        )

        call_payload = token_service.issue_access.call_args[0][0]
        assert "tenant" in call_payload.get("scopes", [])


# ============================================================================
# RefreshTokenUseCase
# ============================================================================


class TestRefreshTokenUseCase:

    def test_raises_when_token_invalid(self):
        ts = MagicMock()
        ts.decode_and_validate.side_effect = Exception("invalid")

        uc = RefreshTokenUseCase(token_service=ts, refresh_repo=MagicMock())
        with pytest.raises(ValueError, match="inválido"):
            uc.execute(
                refresh_token="bad.token",
                user_agent="test",
                ip_address="127.0.0.1",
            )

    def test_raises_and_revokes_family_on_replay(self):
        jti = str(uuid.uuid4())
        family_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        ts = MagicMock()
        ts.decode_and_validate.return_value = {
            "jti": jti, "family": family_id, "sub": user_id
        }
        repo = _make_refresh_repo(is_reused=True)

        uc = RefreshTokenUseCase(token_service=ts, refresh_repo=repo)
        with pytest.raises(ValueError, match="comprometida"):
            uc.execute(
                refresh_token="valid.but.reused",
                user_agent="test",
                ip_address="127.0.0.1",
            )

        repo.revoke_family.assert_called_once_with(family_id=family_id)

    def test_successful_refresh_rotates_tokens(self):
        jti = str(uuid.uuid4())
        family_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        ts = MagicMock()
        ts.decode_and_validate.return_value = {
            "jti": jti,
            "family": family_id,
            "sub": user_id,
            "tenant_id": "tenant-abc",
            "scopes": ["tenant"],
        }
        ts.issue_access.return_value = "new.access.tok"
        ts.issue_refresh.return_value = "new.refresh.tok"
        repo = _make_refresh_repo(is_reused=False)

        uc = RefreshTokenUseCase(token_service=ts, refresh_repo=repo)
        result = uc.execute(
            refresh_token="valid.refresh.tok",
            user_agent="Mozilla",
            ip_address="10.0.0.1",
        )

        assert result["access_token"] == "new.access.tok"
        assert result["refresh_token"] == "new.refresh.tok"
        assert result["token_type"] == "bearer"
        # Old JTI must be marked as used
        repo.mark_used.assert_called_once_with(jti=jti)

    def test_raises_when_payload_missing_fields(self):
        ts = MagicMock()
        # Missing 'family' field
        ts.decode_and_validate.return_value = {"jti": "abc", "sub": "uid"}

        uc = RefreshTokenUseCase(token_service=ts, refresh_repo=MagicMock())
        with pytest.raises(ValueError, match="estructura"):
            uc.execute(
                refresh_token="incomplete.token",
                user_agent="test",
                ip_address="127.0.0.1",
            )


# ============================================================================
# LogoutUseCase
# ============================================================================


class TestLogoutUseCase:

    def test_revokes_family_on_logout(self):
        family_id = str(uuid.uuid4())
        repo = MagicMock()
        repo.get_family.return_value = family_id

        uc = LogoutUseCase(refresh_repo=repo)
        uc.execute(refresh_token="valid.tok", user_id=uuid.uuid4())

        repo.revoke_family.assert_called_once_with(family_id=family_id)

    def test_no_error_when_token_not_found(self):
        repo = MagicMock()
        repo.get_family.return_value = None

        uc = LogoutUseCase(refresh_repo=repo)
        # Should not raise
        uc.execute(refresh_token="unknown.tok", user_id=uuid.uuid4())

        repo.revoke_family.assert_not_called()

    def test_raises_value_error_on_repo_exception(self):
        repo = MagicMock()
        repo.get_family.side_effect = RuntimeError("DB error")

        uc = LogoutUseCase(refresh_repo=repo)
        with pytest.raises(ValueError, match="cerrar sesión"):
            uc.execute(refresh_token="valid.tok", user_id=uuid.uuid4())
