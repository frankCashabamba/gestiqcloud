from __future__ import annotations

import smtplib

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.email.email_utils import send_email_mailtrap
from app.config.settings import settings

router = APIRouter(prefix="/email", tags=["email"])


@router.get("/health")
def smtp_health():
    host = getattr(settings, "EMAIL_HOST", None)
    if not host:
        return {
            "ok": False,
            "reason": "EMAIL_HOST not configured",
            "env": settings.ENV,
        }

    port = int(getattr(settings, "EMAIL_PORT", 0) or 0)
    use_ssl = bool(getattr(settings, "EMAIL_USE_SSL", False) or port == 465)
    use_tls = bool(getattr(settings, "EMAIL_USE_TLS", True))
    username = getattr(settings, "EMAIL_HOST_USER", None)
    result: dict = {
        "host": host,
        "port": port,
        "use_ssl": use_ssl,
        "use_tls": use_tls,
        "has_user": bool(username),
        "from": getattr(settings, "DEFAULT_FROM_EMAIL", None),
        "env": settings.ENV,
    }

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host=host, port=port or 465, timeout=10)
        else:
            server = smtplib.SMTP(host=host, port=port or 587, timeout=10)
            if use_tls:
                server.starttls()
        if username and getattr(settings, "EMAIL_HOST_PASSWORD", None):
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.noop()
        server.quit()
        result.update({"ok": True})
        return result
    except Exception as e:
        # Best-effort: devuelve estado y error sin romper el esquema
        result.update({"ok": False, "error": str(e)})
        return result


class EmailTestIn(BaseModel):
    to: EmailStr
    subject: str | None = None
    html: str | None = None


@router.post("/test")
def smtp_test(payload: EmailTestIn, background: BackgroundTasks):
    # Seguridad básica: deshabilitar por defecto en producción salvo flag explícita
    enabled = bool(getattr(settings, "EMAIL_TEST_ENDPOINT_ENABLED", False))
    if settings.ENV == "production" and not enabled:
        raise HTTPException(status_code=403, detail="email_test_disabled_in_production")

    subject = payload.subject or "GestiqCloud: correo de prueba"
    html = payload.html or ("""
    <html><body>
      <h3>Correo de prueba</h3>
      <p>Este es un correo de prueba enviado por el endpoint /email/test.</p>
      <p>Fecha servidor: {}</p>
    </body></html>
    """.format(__import__("datetime").datetime.utcnow().isoformat() + "Z"))

    try:
        background.add_task(send_email_mailtrap, str(payload.to), subject, html)
        return {"queued": True, "to": str(payload.to)}
    except Exception as e:
        # Propagar error para verlo en logs/clientes
        raise HTTPException(status_code=500, detail=f"smtp_test_failed: {e}")
