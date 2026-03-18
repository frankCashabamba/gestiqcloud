"""MFA — TOTP setup, verification, recovery, and disable endpoints."""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.modules.identity.application.mfa import (
    generate_recovery_codes,
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth/mfa",
    tags=["MFA"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_user_id(request: Request) -> UUID:
    claims = getattr(request.state, "access_claims", {}) or {}
    # Support both "user_id" (tenant tokens) and "sub" (standard JWT)
    uid = claims.get("user_id") or claims.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="not_authenticated")
    try:
        return UUID(str(uid))
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid_user_id")


def _get_user_email(request: Request) -> str:
    claims = getattr(request.state, "access_claims", {}) or {}
    return claims.get("email", "") or claims.get("username", "")


# --- Schemas ---


class TOTPVerifyIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class RecoveryIn(BaseModel):
    code: str = Field(min_length=8, max_length=8)


# --- Endpoints ---


@router.get("/status", response_model=dict[str, Any])
def mfa_status(request: Request, db: Session = Depends(get_db)):
    """Retorna el estado MFA del usuario autenticado."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = _get_user_id(request)

    row = db.execute(
        text("SELECT is_enabled, last_used_at FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    ).first()

    return {
        "mfa_enabled": bool(row and row[0]),
        "last_used_at": row[1].isoformat() if row and row[1] else None,
    }


@router.post("/setup", response_model=dict[str, Any], status_code=201)
def setup_mfa(request: Request, db: Session = Depends(get_db)):
    """Genera secreto TOTP y códigos de recuperación. Retorna URI para QR."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = _get_user_id(request)
    email = _get_user_email(request)

    existing = db.execute(
        text("SELECT id, is_enabled FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    ).first()

    if existing and existing[1]:
        raise HTTPException(status_code=409, detail="mfa_already_enabled")

    secret = generate_totp_secret()
    plain_codes, hashed_codes = generate_recovery_codes()
    uri = get_totp_uri(secret, email)

    if existing:
        db.execute(
            text(
                "UPDATE user_mfa SET totp_secret = :secret, recovery_codes = :codes, "
                "is_enabled = false WHERE user_id = :uid"
            ).bindparams(bindparam("uid", type_=PGUUID(as_uuid=True))),
            {"uid": user_id, "secret": secret, "codes": hashed_codes},
        )
    else:
        db.execute(
            text(
                "INSERT INTO user_mfa(user_id, totp_secret, recovery_codes, is_enabled) "
                "VALUES (:uid, :secret, :codes, false)"
            ).bindparams(bindparam("uid", type_=PGUUID(as_uuid=True))),
            {"uid": user_id, "secret": secret, "codes": hashed_codes},
        )

    db.commit()

    return {
        "totp_uri": uri,
        "recovery_codes": plain_codes,
        "message": "Escanea el código QR y verifica con /verify para activar MFA.",
    }


@router.post("/verify", response_model=dict[str, Any])
def verify_and_enable_mfa(payload: TOTPVerifyIn, request: Request, db: Session = Depends(get_db)):
    """Verifica código TOTP y activa MFA."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = _get_user_id(request)

    mfa = db.execute(
        text("SELECT id, totp_secret, is_enabled FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    ).first()

    if not mfa:
        raise HTTPException(status_code=404, detail="mfa_not_setup")
    if mfa[2]:
        raise HTTPException(status_code=409, detail="mfa_already_enabled")

    if not verify_totp(mfa[1], payload.code):
        raise HTTPException(status_code=400, detail="invalid_totp_code")

    db.execute(
        text("UPDATE user_mfa SET is_enabled = true, last_used_at = NOW() WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    )
    db.commit()

    return {"status": "mfa_enabled", "message": "MFA activado correctamente."}


@router.post("/validate", response_model=dict[str, Any])
def validate_totp(payload: TOTPVerifyIn, request: Request, db: Session = Depends(get_db)):
    """Valida código TOTP durante el login."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = _get_user_id(request)

    mfa = db.execute(
        text("SELECT totp_secret, is_enabled FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    ).first()

    if not mfa or not mfa[1]:
        raise HTTPException(status_code=404, detail="mfa_not_enabled")

    if not verify_totp(mfa[0], payload.code):
        raise HTTPException(status_code=400, detail="invalid_totp_code")

    db.execute(
        text("UPDATE user_mfa SET last_used_at = NOW() WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    )
    db.commit()

    return {"status": "valid", "message": "Código TOTP válido."}


@router.post("/recovery", response_model=dict[str, Any])
def use_recovery_code(payload: RecoveryIn, request: Request, db: Session = Depends(get_db)):
    """Usa un código de recuperación."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = _get_user_id(request)

    mfa = db.execute(
        text("SELECT id, recovery_codes, is_enabled FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    ).first()

    if not mfa or not mfa[2]:
        raise HTTPException(status_code=404, detail="mfa_not_enabled")

    hashed_input = hashlib.sha256(payload.code.encode()).hexdigest()
    stored_codes = list(mfa[1]) if mfa[1] else []

    if hashed_input not in stored_codes:
        raise HTTPException(status_code=400, detail="invalid_recovery_code")

    stored_codes.remove(hashed_input)

    db.execute(
        text("UPDATE user_mfa SET recovery_codes = :codes, last_used_at = NOW() WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id, "codes": stored_codes},
    )
    db.commit()

    return {
        "status": "valid",
        "remaining_codes": len(stored_codes),
        "message": "Código de recuperación usado correctamente.",
    }


@router.delete("/disable", response_model=dict[str, Any])
def disable_mfa(request: Request, db: Session = Depends(get_db)):
    """Desactiva MFA para el usuario."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = _get_user_id(request)

    mfa = db.execute(
        text("SELECT id, is_enabled FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    ).first()

    if not mfa:
        raise HTTPException(status_code=404, detail="mfa_not_setup")

    db.execute(
        text("DELETE FROM user_mfa WHERE user_id = :uid").bindparams(
            bindparam("uid", type_=PGUUID(as_uuid=True))
        ),
        {"uid": user_id},
    )
    db.commit()

    return {"status": "mfa_disabled", "message": "MFA desactivado correctamente."}
