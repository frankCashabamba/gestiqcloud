from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional,Any, Mapping, Sequence
from uuid import uuid4
import hashlib
from fastapi import HTTPException
from contextlib import contextmanager
from sqlalchemy import text
import jwt
from jwt  import  (
    ExpiredSignatureError,
    ImmatureSignatureError,
    MissingRequiredClaimError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
)

import time
from pydantic import SecretStr

from app.config.settings import settings
from app.config.database import SessionLocal


# ---------------------------
# Helpers
# ---------------------------

def _hash(value: str) -> str:
    """Devuelve un hash SHA256 de un string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    """Fecha/hora UTC aware."""
    return datetime.now(timezone.utc)


@contextmanager
def _with_session():
    """Context manager para abrir/cerrar SessionLocal con commit/rollback."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------
# Public API (persistencia)
# ---------------------------

def family_create(user_id: str, tenant_id: Optional[str]) -> str:
    """
    Crea una familia de refresh tokens y devuelve su ID (UUID).
    """
    family_id = str(uuid4())
    with _with_session() as db:
        db.execute(
            text("""
                INSERT INTO auth_refresh_family (id, user_id, tenant_id, created_at, revoked_at)
                VALUES (:id, :user_id, :tenant_id, :created_at, NULL)
            """),
            {
                "id": family_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "created_at": _utcnow(),
            },
        )
    return family_id


def token_issue(
    family_id: str,
    prev_jti: Optional[str],
    user_agent: str,
    ip: str,
) -> str:
    """
    Crea un nuevo refresh token y devuelve su JTI.
    """
    jti = str(uuid4())
    with _with_session() as db:
        db.execute(
            text("""
                INSERT INTO auth_refresh_token
                  (id, family_id, jti, prev_jti, used_at, revoked_at, ua_hash, ip_hash, created_at)
                VALUES
                  (:id, :family_id, :jti, :prev_jti, NULL, NULL, :ua_hash, :ip_hash, :created_at)
            """),
            {
                "id": str(uuid4()),
                "family_id": family_id,
                "jti": jti,
                "prev_jti": prev_jti,
                "ua_hash": _hash(user_agent or ""),
                "ip_hash": _hash(ip or ""),
                "created_at": _utcnow(),
            },
        )
    return jti


def token_mark_used(jti: str) -> None:
    """Marca un refresh token como usado (rotado)."""
    with _with_session() as db:
        db.execute(
            text("""
                UPDATE auth_refresh_token
                   SET used_at = :ts
                 WHERE jti = :jti
            """),
            {"jti": jti, "ts": _utcnow()},
        )


def token_is_reused_or_revoked(jti: str) -> bool:
    """
    Devuelve True si:
      - el jti no existe,
      - está revocado,
      - o ya fue usado.
    """
    with _with_session() as db:
        row = db.execute(
            text("""
                SELECT used_at, revoked_at
                  FROM auth_refresh_token
                 WHERE jti = :jti
                 LIMIT 1
            """),
            {"jti": jti},
        ).mappings().first()

    if row is None:
        return True
    return (row["used_at"] is not None) or (row["revoked_at"] is not None)


def family_revoke(family_id: str) -> None:
    """Revoca toda la familia y todos sus tokens."""
    now = _utcnow()
    with _with_session() as db:
        db.execute(
            text("""
                UPDATE auth_refresh_family
                   SET revoked_at = :ts
                 WHERE id = :fid
            """),
            {"fid": family_id, "ts": now},
        )
        db.execute(
            text("""
                UPDATE auth_refresh_token
                   SET revoked_at = :ts
                 WHERE family_id = :fid
            """),
            {"fid": family_id, "ts": now},
        )


def token_get_family(jti: str) -> Optional[str]:
    """Devuelve el family_id al que pertenece un jti, o None si no existe."""
    with _with_session() as db:
        row = db.execute(
            text("""
                SELECT family_id
                  FROM auth_refresh_token
                 WHERE jti = :jti
                 LIMIT 1
            """),
            {"jti": jti},
        ).mappings().first()
    return str(row["family_id"]) if row else None


# ---------------------------
# JWT helpers 
# ---------------------------


def _now_ts() -> int:
    return int(time.time())

def _unwrap_secret(value: SecretStr | str | bytes | None) -> str | bytes | None:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value

def _signing_key() -> str | bytes:
    alg = settings.JWT_ALGORITHM.upper()
    if alg.startswith("HS"):
        key = _unwrap_secret(getattr(settings, "JWT_SECRET_KEY", None))
        if not isinstance(key, (str, bytes)) or not key:
            raise RuntimeError("JWT_SECRET_KEY no está configurada")
        return key
    # Algoritmos asimétricos (RS*/ES*)
    priv = _unwrap_secret(getattr(settings, "JWT_PRIVATE_KEY", None))
    if not isinstance(priv, (str, bytes)) or not priv:
        raise RuntimeError("JWT_PRIVATE_KEY no está configurada para algoritmo asimétrico")
    return priv

def _verification_keys() -> Sequence[str | bytes]:
    alg = settings.JWT_ALGORITHM.upper()
    if alg.startswith("HS"):
        # misma clave para verificar
        return [_signing_key()]
    # RS*/ES*: pública(s) para verificar (rotación opcional)
    keys: list[str | bytes] = []
    pub = _unwrap_secret(getattr(settings, "JWT_PUBLIC_KEY", None))
    if isinstance(pub, (str, bytes)) and pub:
        keys.append(pub)
    extras = getattr(settings, "JWT_ADDITIONAL_PUBLIC_KEYS", None) or []
    for k in extras:
        k = _unwrap_secret(k)
        if isinstance(k, (str, bytes)) and k:
            keys.append(k)
    if not keys:
        raise RuntimeError("No hay claves públicas para verificar JWT")
    return keys

def _base_claims(payload: Mapping[str, Any], token_type: str, exp_seconds: int) -> dict[str, Any]:
    now = _now_ts()
    claims = {
        **payload,
        "type": token_type,
        "iat": now,
        "nbf": now,
        "exp": now + exp_seconds,
        "iss": getattr(settings, "JWT_ISSUER", None) or "gestiqcloud",
    }
    aud = getattr(settings, "JWT_AUDIENCE", None)
    if aud:
        claims["aud"] = aud
    return claims

def create_access(payload: dict) -> str:
    """Crea un JWT de acceso corto."""
    exp_seconds = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)) * 60
    claims = _base_claims(payload, "access", exp_seconds)
    return jwt.encode(claims, _signing_key(), algorithm=settings.JWT_ALGORITHM)

def create_refresh(payload: dict, jti: str, prev_jti: Optional[str]) -> str:
    """Crea un JWT de refresh token."""
    exp_seconds = int(getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30)) * 24 * 60 * 60
    claims = _base_claims({**payload, "jti": jti, "prev_jti": prev_jti}, "refresh", exp_seconds)
    return jwt.encode(claims, _signing_key(), algorithm=settings.JWT_ALGORITHM)

def decode_and_validate(token: str, expected_type: str) -> dict:
    """Decodifica y valida un JWT asegurando que sea del tipo esperado."""
    options = {
        "require": ["exp", "iat", "nbf"],
        "verify_aud": bool(getattr(settings, "JWT_AUDIENCE", None)),
    }
    iss = getattr(settings, "JWT_ISSUER", None) or "gestiqcloud"
    aud = getattr(settings, "JWT_AUDIENCE", None)
    leeway = int(getattr(settings, "JWT_LEEWAY_SECONDS", 30))
    alg = settings.JWT_ALGORITHM

    last_err: Exception | None = None

    for key in _verification_keys():
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg],
                issuer=iss,
                audience=aud,
                leeway=leeway,
                options=options,
            )
            # Acepta "type" o "typ" según qué pusiste al emitir
            token_type = payload.get("type") or payload.get("typ")
            if token_type != expected_type:
                raise HTTPException(status_code=401, detail="wrong_token_type")

            return payload

        except ExpiredSignatureError as e:
            # 401 explícito: el cliente ya sabe que debe refrescar/cerrar sesión
            raise HTTPException(
                status_code=401,
                detail="token_expired",
                headers={
                    'WWW-Authenticate': 'Bearer error="invalid_token", error_description="token expired"'
                },
            ) from e

        # Errores de validación "de cliente" -> también 401
        except (InvalidAudienceError, InvalidIssuerError,
                ImmatureSignatureError, MissingRequiredClaimError) as e:
            raise HTTPException(status_code=401, detail=e.__class__.__name__) from e

        # Firma inválida / clave equivocada / etc.: probamos la siguiente clave (rotación)
        except InvalidTokenError as e:
            last_err = e
            continue

    # Ninguna clave validó
    raise HTTPException(status_code=401, detail="invalid_token") from last_err
