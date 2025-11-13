"""Email utilities: token generation, rendering and SMTP send with dev fallback."""

import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid, parseaddr, formataddr
import logging

from fastapi import BackgroundTasks
from itsdangerous import URLSafeTimedSerializer

from app.config.settings import settings
from app.utils.email_renderer import render_template

logger = logging.getLogger("app.email")


def _html_to_text(html: str) -> str:
    try:
        # Very small HTML→text fallback for better deliverability
        text = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.I)
        text = re.sub(r"<\s*/p\s*>", "\n\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception:
        return html


def send_email_mailtrap(to_email: str, subject: str, html_content: str) -> None:
    """Send email via SMTP, or log to console in development.

    - If ENV=development and either EMAIL_DEV_LOG_ONLY is true or EMAIL_HOST is missing,
      print the email details and HTML to stdout and return.
    - Otherwise, attempt SMTP send using settings.*
    - On SMTP error in development, also log to stdout instead of raising.
    """
    dev_log = getattr(settings, "EMAIL_DEV_LOG_ONLY", False) or not getattr(
        settings, "EMAIL_HOST", None
    )
    if getattr(settings, "ENV", "development") == "development" and dev_log:
        logger.info("[DEV EMAIL] From: %s", settings.DEFAULT_FROM_EMAIL)
        logger.info("[DEV EMAIL] To: %s", to_email)
        logger.info("[DEV EMAIL] Subject: %s", subject)
        logger.info("[DEV EMAIL] HTML:\n%s", html_content)
        return

    # Build multipart/alternative (plain + HTML) for better spam compliance
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject

    # Parse and normalize From/To to avoid SMTP 501 sender syntax errors
    from_name, from_addr = parseaddr(getattr(settings, "DEFAULT_FROM_EMAIL", "") or "")
    # Robust fallback: extract first email-looking token if parseaddr failed
    if not from_addr or ("@" not in from_addr):
        try:
            m = re.search(
                r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                getattr(settings, "DEFAULT_FROM_EMAIL", "") or "",
            )
            if m:
                from_addr = m.group(1)
        except Exception:
            pass
    if not from_addr or ("@" not in from_addr):
        # Fallback: use SMTP user or a safe default
        from_addr = (
            getattr(settings, "EMAIL_HOST_USER", None) or "no-reply@localhost"
        ).strip()
    if not from_name:
        from_name = getattr(settings, "app_name", "GestiqCloud")
    msg["From"] = formataddr((from_name, from_addr))

    to_name, to_addr = parseaddr(to_email or "")
    if not to_addr or ("@" not in to_addr):
        m_to = None
        try:
            m_to = re.search(
                r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", to_email or ""
            )
        except Exception:
            m_to = None
        to_addr = m_to.group(1) if m_to else (to_email or "").strip()
    msg["To"] = formataddr((to_name, to_addr))
    msg["Date"] = formatdate(localtime=True)
    msg["Message-Id"] = make_msgid(domain=None)
    # Optional: Reply-To same as From (or adjust if you add a REPLY_TO setting)
    try:
        if getattr(settings, "DEFAULT_FROM_EMAIL", None):
            msg["Reply-To"] = formataddr((from_name, from_addr))
    except Exception:
        pass

    plain = _html_to_text(html_content)
    msg.attach(MIMEText(plain, "plain", _charset="utf-8"))
    msg.attach(MIMEText(html_content, "html", _charset="utf-8"))

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
        # Envelope addresses: be explicit to satisfy providers expecting RFC-compliant MAIL FROM
        result = server.send_message(msg, from_addr=from_addr, to_addrs=[to_addr])
        try:
            # send_message returns a dict of {recipient: error} on failure
            if result:
                logger.warning("SMTP send_message reported failures: %s", result)
            else:
                logger.info("SMTP send_message accepted for delivery to %s", to_addr)
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
    secret = (
        settings.SECRET_KEY.get_secret_value()
        if hasattr(settings.SECRET_KEY, "get_secret_value")
        else str(settings.SECRET_KEY)
    )
    return URLSafeTimedSerializer(secret)


def generar_token_email(email: str) -> str:
    serializer = _get_serializer()
    return serializer.dumps(email, salt="recuperar-password")


def verificar_token_email(token: str, max_age: int = 3600) -> str:
    serializer = _get_serializer()
    return serializer.loads(token, salt="recuperar-password", max_age=max_age)


def enviar_correo_bienvenida(
    user_email: str,
    username: str,
    empresa_nombre: str,
    background_tasks: BackgroundTasks,
) -> None:
    token = generar_token_email(user_email)
    base = (
        getattr(settings, "PASSWORD_RESET_URL_BASE", None) or settings.FRONTEND_URL
    ).rstrip("/")
    enlace = f"{base}/set-password?token={token}"
    contexto = {
        "nombre_empresa": empresa_nombre,
        "username": username,
        "enlace": enlace,
        "anio": datetime.now().year,
    }
    html_content = render_template("bienvenida.html", contexto)
    if getattr(settings, "ENV", "development") == "development" and (
        getattr(settings, "EMAIL_DEV_LOG_ONLY", False)
        or not getattr(settings, "EMAIL_HOST", None)
    ):
        logger.info("[DEV EMAIL] Bienvenida link: %s", enlace)
    background_tasks.add_task(
        send_email_mailtrap, user_email, "Bienvenido a GestiqCloud", html_content
    )
    try:
        logger.info("Queued welcome email to %s", user_email)
    except Exception:
        pass


def reenviar_correo_reset(user_email: str, background_tasks: BackgroundTasks) -> None:
    token = generar_token_email(user_email)
    base = (
        getattr(settings, "PASSWORD_RESET_URL_BASE", None) or settings.FRONTEND_URL
    ).rstrip("/")
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
    if getattr(settings, "ENV", "development") == "development" and (
        getattr(settings, "EMAIL_DEV_LOG_ONLY", False)
        or not getattr(settings, "EMAIL_HOST", None)
    ):
        logger.info("[DEV EMAIL] Reset link: %s", enlace)
    background_tasks.add_task(
        send_email_mailtrap, user_email, "Restablecer tu contraseña", html_content
    )
