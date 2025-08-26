# app/core/security.py
from typing import Optional, Tuple
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt", "argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> Tuple[bool, Optional[str]]:
    """
    Devuelve (ok, new_hash):
      - ok: True si la contraseña coincide
      - new_hash: nuevo hash si el almacenado necesita actualización; None en caso contrario
    """
    try:
        ok = _pwd.verify(plain, hashed)
    except Exception:
        return False, None
    if ok and _pwd.needs_update(hashed):
        return True, _pwd.hash(plain)
    return ok, None
