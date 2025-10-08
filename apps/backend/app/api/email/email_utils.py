"""Email utilities: token generation, rendering and SMTP send with dev fallback."""

import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Tuple
import logging

from fastapi import BackgroundTasks
from itsdangerous import URLSafeTimedSerializer

from app.config.settings import settings
from app.utils.email_renderer import render_template

logger = logging.getLogger("app.email")


def send_email_mailtrap(to_email: str, subject: str, html_content: str) -> None:
    """Send email via SMTP, or log to console in development.

    - If ENV=development and either EMAIL_DEV_LOG_ONLY is true or EMAIL_HOST is missing,
      print the email details and HTML to stdout and return.
    - Otherwise, attempt SMTP send using settings.*
    - On SMTP error in development, also log to stdout instead of raising.
    """
    dev_log = (getattr(settings, "EMAIL_DEV_LOG_ONLY", False) or not getattr(settings, "EMAIL_HOST", None))
    if getattr(settings, "ENV", "development") == "development" and dev_log:
        logger.info("[DEV EMAIL] From: %s", settings.DEFAULT_FROM_EMAIL)
        logger.info("[DEV EMAIL] To: %s", to_email)
        logger.info("[DEV EMAIL] Subject: %s", subject)
        logger.info("[DEV EMAIL] HTML:\n%s", html_content)
        return

    msg = MIMEText(html_content, "html")
    msg["Subject"] = subject
    msg["From"] = settings.DEFAULT_FROM_EMAIL
    msg["To"] = to_email

    try:
        port = int(getattr(settings, "EMAIL_PORT", 0) or 0)
        use_ssl = bool(getattr(settings, "EMAIL_USE_SSL", False) or port == 465)
        if use_ssl:
            server = smtplib.SMTP_SSL(host=settings.EMAIL_HOST, port=port or 465)
        else:
            server = smtplib.SMTP(host=settings.EMAIL_HOST, port=port or 587)
            if getattr(settings, "EMAIL_USE_TLS", True):
                server.starttls()
        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        result = server.send_message(msg)
        try:
            # send_message returns a dict of {recipient: error} on failure
            if result:
                logger.warning("SMTP send_message reported failures: %s", result)
            else:
                logger.info("SMTP send_message accepted for delivery to %s", to_email)
        except Exception:
            pass
        server.quit()
    except Exception as e:
        if getattr(settings, "ENV", "development") == "development":
            logger.warning("[DEV EMAIL FALLBACK] Error SMTP: %s", e)
            logger.info("[DEV EMAIL FALLBACK] From: %s", settings.DEFAULT_FROM_EMAIL)
            logger.info("[DEV EMAIL FALLBACK] To: %s", to_email)
            logger.info("[DEV EMAIL FALLBACK] Subject: %s", subject)
            logger.info("[DEV EMAIL FALLBACK] HTML:\n%s", html_content)
            return
        raise


def _get_serializer() -> URLSafeTimedSerializer:
    # NOTE: for dev purposes; in production consider a dedicated secret and salt
    secret = settings.SECRET_KEY.get_secret_value() if hasattr(settings.SECRET_KEY, "get_secret_value") else str(settings.SECRET_KEY)
    return URLSafeTimedSerializer(secret)


def generar_token_email(email: str) -> str:
    serializer = _get_serializer()
    return serializer.dumps(email, salt="recuperar-password")


def verificar_token_email(token: str, max_age: int = 3600) -> str:
    serializer = _get_serializer()
    return serializer.loads(token, salt="recuperar-password", max_age=max_age)


def enviar_correo_bienvenida(user_email: str, username: str, empresa_nombre: str, background_tasks: BackgroundTasks) -> None:
    token = generar_token_email(user_email)
    base = (getattr(settings, "PASSWORD_RESET_URL_BASE", None) or settings.FRONTEND_URL).rstrip('/')
    enlace = f"{base}/set-password?token={token}"
    contexto = {"nombre_empresa": empresa_nombre, "username": username, "enlace": enlace, "anio": datetime.now().year}
    html_content = render_template("bienvenida.html", contexto)
    if getattr(settings, "ENV", "development") == "development" and (getattr(settings, "EMAIL_DEV_LOG_ONLY", False) or not getattr(settings, "EMAIL_HOST", None)):
        logger.info("[DEV EMAIL] Bienvenida link: %s", enlace)
    background_tasks.add_task(send_email_mailtrap, user_email, "Bienvenido a GestiqCloud", html_content)
    try:
        logger.info("Queued welcome email to %s", user_email)
    except Exception:
        pass


def reenviar_correo_reset(user_email: str, background_tasks: BackgroundTasks) -> None:
    token = generar_token_email(user_email)
    base = (getattr(settings, "PASSWORD_RESET_URL_BASE", None) or settings.FRONTEND_URL).rstrip('/')
    enlace = f"{base}/set-password?token={token}"
    contexto = {"enlace": enlace, "anio": datetime.now().year}
    try:
        html_content = render_template("reset_password.html", contexto)
    except Exception:
        try:
            html_content = render_template("set_password.html", contexto)
        except Exception:
            html_content = f"""
            <html><body>
              <p>Para restablecer tu contraseña, visita el siguiente enlace:</p>
              <p><a href="{enlace}">{enlace}</a></p>
            </body></html>
            """
    if getattr(settings, "ENV", "development") == "development" and (getattr(settings, "EMAIL_DEV_LOG_ONLY", False) or not getattr(settings, "EMAIL_HOST", None)):
        logger.info("[DEV EMAIL] Reset link: %s", enlace)
    background_tasks.add_task(send_email_mailtrap, user_email, "Restablecer tu contraseña", html_content)
