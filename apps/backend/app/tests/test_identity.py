"""Tests for Identity module use cases."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

pytestmark = pytest.mark.no_db

from app.modules.identity.application.use_cases import (
    LoginUseCase,
    RefreshTokenUseCase,
    LogoutUseCase,
    ChangePasswordUseCase,
)
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher


class TestPasslibPasswordHasher:
    def test_hash_and_verify(self):
        hasher = PasslibPasswordHasher()
        hashed = hasher.hash("mypassword123")
        assert hashed != "mypassword123"
        ok, err = hasher.verify("mypassword123", hashed)
        assert ok is True
        assert err is None

    def test_verify_wrong_password(self):
        hasher = PasslibPasswordHasher()
        hashed = hasher.hash("correct_password")
        ok, err = hasher.verify("wrong_password", hashed)
        assert ok is False


class TestLoginUseCase:
    def _make_user(self, email="test@example.com", password_hash="hashed"):
        user = MagicMock()
        user.id = uuid4()
        user.email = email
        user.name = "Test User"
        user.is_active = True
        user.password_hash = password_hash
        return user

    def test_login_success(self):
        token_service = MagicMock()
        token_service.issue_access.return_value = "access_token_123"
        token_service.issue_refresh.return_value = "refresh_token_123"

        hasher = MagicMock()
        hasher.verify.return_value = (True, None)

        rate_limiter = MagicMock()
        rate_limiter.check.return_value = MagicMock(is_locked=False)

        refresh_repo = MagicMock()
        refresh_repo.create_family.return_value = "family_id_123"

        uc = LoginUseCase(
            token_service=token_service,
            password_hasher=hasher,
            rate_limiter=rate_limiter,
            refresh_repo=refresh_repo,
        )

        user = self._make_user()
        request = MagicMock()
        result = uc.execute(
            user=user,
            password="password123",
            request=request,
            user_agent="Mozilla/5.0",
            ip_address="127.0.0.1",
        )

        assert result["access_token"] == "access_token_123"
        assert result["refresh_token"] == "refresh_token_123"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 900
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["name"] == "Test User"
        rate_limiter.reset.assert_called_once()
        refresh_repo.create_family.assert_called_once()
        refresh_repo.mark_used.assert_called_once_with(jti="family_id_123")

    def test_login_rate_limited(self):
        rate_limiter = MagicMock()
        rate_limiter.check.return_value = MagicMock(is_locked=True, retry_after=300)

        uc = LoginUseCase(
            token_service=MagicMock(),
            password_hasher=MagicMock(),
            rate_limiter=rate_limiter,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="bloqueada"):
            uc.execute(
                user=self._make_user(),
                password="any",
                request=MagicMock(),
                user_agent="",
                ip_address="",
            )

    def test_login_wrong_password(self):
        hasher = MagicMock()
        hasher.verify.return_value = (False, "wrong password")

        rate_limiter = MagicMock()
        rate_limiter.check.return_value = MagicMock(is_locked=False)

        uc = LoginUseCase(
            token_service=MagicMock(),
            password_hasher=hasher,
            rate_limiter=rate_limiter,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="incorrecta"):
            uc.execute(
                user=self._make_user(),
                password="wrong",
                request=MagicMock(),
                user_agent="",
                ip_address="",
            )
        rate_limiter.incr_fail.assert_called_once()

    def test_login_with_tenant_id(self):
        token_service = MagicMock()
        token_service.issue_access.return_value = "at"
        token_service.issue_refresh.return_value = "rt"

        hasher = MagicMock()
        hasher.verify.return_value = (True, None)

        rate_limiter = MagicMock()
        rate_limiter.check.return_value = MagicMock(is_locked=False)

        refresh_repo = MagicMock()
        refresh_repo.create_family.return_value = "fam"

        uc = LoginUseCase(
            token_service=token_service,
            password_hasher=hasher,
            rate_limiter=rate_limiter,
            refresh_repo=refresh_repo,
        )

        result = uc.execute(
            user=self._make_user(),
            password="p",
            request=MagicMock(),
            user_agent="",
            ip_address="",
            tenant_id="tenant-abc",
        )

        # access payload should include tenant_id
        call_args = token_service.issue_access.call_args[0][0]
        assert call_args["tenant_id"] == "tenant-abc"
        assert call_args["scopes"] == ["tenant"]
        refresh_repo.create_family.assert_called_once_with(
            user_id=str(result["user"]["id"]),
            tenant_id="tenant-abc",
        )


class TestRefreshTokenUseCase:
    def test_refresh_success(self):
        token_service = MagicMock()
        token_service.decode_and_validate.return_value = {
            "jti": "old-jti",
            "family": "fam-1",
            "sub": "user-1",
            "tenant_id": "t1",
            "scopes": ["tenant"],
        }
        token_service.issue_access.return_value = "new_access"
        token_service.issue_refresh.return_value = "new_refresh"

        refresh_repo = MagicMock()
        refresh_repo.is_reused_or_revoked.return_value = False

        uc = RefreshTokenUseCase(
            token_service=token_service,
            refresh_repo=refresh_repo,
        )

        result = uc.execute(
            refresh_token="old_rt",
            user_agent="Mozilla",
            ip_address="10.0.0.1",
        )

        assert result["access_token"] == "new_access"
        assert result["refresh_token"] == "new_refresh"
        assert result["token_type"] == "bearer"
        refresh_repo.mark_used.assert_called_once_with(jti="old-jti")

    def test_refresh_replay_attack(self):
        token_service = MagicMock()
        token_service.decode_and_validate.return_value = {
            "jti": "reused-jti",
            "family": "fam-1",
            "sub": "user-1",
        }

        refresh_repo = MagicMock()
        refresh_repo.is_reused_or_revoked.return_value = True

        uc = RefreshTokenUseCase(
            token_service=token_service,
            refresh_repo=refresh_repo,
        )

        with pytest.raises(ValueError, match="comprometida"):
            uc.execute(
                refresh_token="reused_rt",
                user_agent="",
                ip_address="",
            )
        refresh_repo.revoke_family.assert_called_once_with(family_id="fam-1")

    def test_refresh_invalid_token(self):
        token_service = MagicMock()
        token_service.decode_and_validate.side_effect = Exception("expired")

        uc = RefreshTokenUseCase(
            token_service=token_service,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="inválido"):
            uc.execute(
                refresh_token="bad_token",
                user_agent="",
                ip_address="",
            )

    def test_refresh_missing_fields(self):
        token_service = MagicMock()
        token_service.decode_and_validate.return_value = {
            "sub": "user-1",
            # missing jti and family
        }

        uc = RefreshTokenUseCase(
            token_service=token_service,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="inválida"):
            uc.execute(
                refresh_token="incomplete_rt",
                user_agent="",
                ip_address="",
            )


class TestChangePasswordUseCase:
    def test_change_password_success(self):
        hasher = MagicMock()
        hasher.verify.return_value = (True, None)
        hasher.hash.return_value = "new_hashed_password"

        uc = ChangePasswordUseCase(
            password_hasher=hasher,
            refresh_repo=MagicMock(),
        )

        user = MagicMock()
        user.password_hash = "old_hash"
        result = uc.execute(
            user=user,
            current_password="old_pass",
            new_password="new_password_123",
            user_id=uuid4(),
        )

        assert result["new_password_hash"] == "new_hashed_password"
        assert "exitosamente" in result["message"]

    def test_change_password_wrong_current(self):
        hasher = MagicMock()
        hasher.verify.return_value = (False, "wrong")

        uc = ChangePasswordUseCase(
            password_hasher=hasher,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="incorrecta"):
            uc.execute(
                user=MagicMock(),
                current_password="wrong",
                new_password="new_pass_123",
                user_id=uuid4(),
            )

    def test_change_password_same_as_current(self):
        hasher = MagicMock()
        hasher.verify.return_value = (True, None)

        uc = ChangePasswordUseCase(
            password_hasher=hasher,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="diferente"):
            uc.execute(
                user=MagicMock(),
                current_password="same_pass",
                new_password="same_pass",
                user_id=uuid4(),
            )

    def test_change_password_too_short(self):
        hasher = MagicMock()
        hasher.verify.return_value = (True, None)

        uc = ChangePasswordUseCase(
            password_hasher=hasher,
            refresh_repo=MagicMock(),
        )

        with pytest.raises(ValueError, match="8 caracteres"):
            uc.execute(
                user=MagicMock(),
                current_password="old_pass",
                new_password="short",
                user_id=uuid4(),
            )


class TestLogoutUseCase:
    def test_logout_revokes_family(self):
        refresh_repo = MagicMock()
        refresh_repo.get_family.return_value = "family_123"

        uc = LogoutUseCase(refresh_repo=refresh_repo)
        uc.execute(refresh_token="token_abc", user_id=uuid4())

        refresh_repo.get_family.assert_called_once_with(jti="token_abc")
        refresh_repo.revoke_family.assert_called_once_with(family_id="family_123")

    def test_logout_unknown_token(self):
        refresh_repo = MagicMock()
        refresh_repo.get_family.return_value = None

        uc = LogoutUseCase(refresh_repo=refresh_repo)
        uc.execute(refresh_token="unknown", user_id=uuid4())
        refresh_repo.revoke_family.assert_not_called()

    def test_logout_error_raises(self):
        refresh_repo = MagicMock()
        refresh_repo.get_family.side_effect = RuntimeError("db error")

        uc = LogoutUseCase(refresh_repo=refresh_repo)
        with pytest.raises(ValueError, match="cerrar sesión"):
            uc.execute(refresh_token="tok", user_id=uuid4())
