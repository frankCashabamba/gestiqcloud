from __future__ import annotations

from typing import Optional, Tuple

from app.modules.identity.application.ports import PasswordHasher
from app.core.security import hash_password as _hash_password, verify_password as _verify_password


class PasslibPasswordHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return _hash_password(plain)

    def verify(self, plain: str, hashed: str) -> Tuple[bool, Optional[str]]:
        return _verify_password(plain, hashed)

