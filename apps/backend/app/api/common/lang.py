# app/api/v1/common/lang.py
from fastapi import APIRouter, Response
router = APIRouter(prefix="/i18n", tags=["i18n"])

@router.post("/lang/{lang}")
def set_lang(lang: str, response: Response):
    if lang not in ("es", "en"):
        lang = "es"
    # cookie no-httponly para que la SPA pueda leerla si quiere
    response.set_cookie("lang", lang, max_age=60*60*24*365, samesite="lax")
    return {"ok": True, "lang": lang}
