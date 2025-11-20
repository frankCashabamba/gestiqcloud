from __future__ import annotations

from app.core.security import hash_password as _hash_password
from app.core.security import verify_password as _verify_password
from app.modules.identity.application.ports import PasswordHasher


class PasslibPasswordHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return _hash_password(plain)

    def verify(self, plain: str, hashed: str) -> tuple[bool, str | None]:
        return _verify_password(plain, hashed)
