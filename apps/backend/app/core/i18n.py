# app/core/i18n.py
from typing import Literal

from fastapi import Request

Lang = Literal["es", "en"]

MESSAGES: dict[str, dict[str, str]] = {
    "es": {
        "invalid_credentials": "Credenciales inválidas",
        "company_not_found": "Empresa no encontrada",
        "signed_out": "Sesión cerrada correctamente",
        "forbidden": "No tienes permisos para esta acción",
    },
    "en": {
        "invalid_credentials": "Invalid credentials",
        "company_not_found": "Company not found",
        "signed_out": "Signed out successfully",
        "forbidden": "You do not have permission to perform this action",
    },
}


def detect_lang(request: Request) -> Lang:
    # 1) cookie explícita
    lang = request.cookies.get("lang")
    if lang in ("es", "en"):
        return lang  # type: ignore[return-value]
    # 2) Accept-Language
    hdr = request.headers.get("Accept-Language", "")
    if hdr:
        code = hdr.split(",")[0].strip().lower()[:2]
        if code in ("es", "en"):
            return code  # type: ignore[return-value]
    return "es"


def t(request: Request, key: str) -> str:
    lang = detect_lang(request)
    return MESSAGES.get(lang, MESSAGES["en"]).get(key, key)
