"""Email utilities: token generation, rendering and SMTP send with dev fallback."""

import logging
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid, parseaddr

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
        from_addr = (getattr(settings, "EMAIL_HOST_USER", None) or "no-reply@localhost").strip()
    if not from_name:
        from_name = getattr(settings, "app_name", "GestiqCloud")
    msg["From"] = formataddr((from_name, from_addr))

    to_name, to_addr = parseaddr(to_email or "")
    if not to_addr or ("@" not in to_addr):
        m_to = None
        try:
            m_to = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", to_email or "")
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


_SECTOR_STEPS: dict[str, list[dict]] = {
    "panaderia": [
        {"icon": "🌾", "titulo": "Cargá tus ingredientes", "detalle": "Registrá harina, azúcar, huevos, etc. con la unidad correcta (kg, L, uds)"},
        {"icon": "📋", "titulo": "Creá tus recetas", "detalle": "Definí ingredientes, cantidades y el sistema calculará el costo y precio sugerido automáticamente"},
        {"icon": "🛒", "titulo": "Registrá tu primera compra", "detalle": "Al recibir la compra, el stock y el costo promedio se actualizan solos"},
        {"icon": "🏭", "titulo": "Ejecutá una orden de producción", "detalle": "El sistema descuenta los ingredientes según la receta y agrega el producto terminado al stock"},
        {"icon": "🧾", "titulo": "Abrí tu caja y vendé", "detalle": "Usá el POS para registrar ventas. Al cerrar turno se genera el asiento contable automáticamente"},
    ],
    "restaurante": [
        {"icon": "🍽️", "titulo": "Cargá tu menú por categorías", "detalle": "Organizá tus platos en Entrantes, Principales, Postres, Bebidas, etc."},
        {"icon": "📋", "titulo": "Creá recetas con costos", "detalle": "Asociá ingredientes a cada plato para conocer tu margen real por plato"},
        {"icon": "🛒", "titulo": "Registrá compras de insumos", "detalle": "Cada compra recibida actualiza el stock y el costo promedio de tus ingredientes"},
        {"icon": "🧾", "titulo": "Abrí tu caja y registrá servicios", "detalle": "Registrá ventas por mesa o mostrador y aceptá múltiples métodos de pago"},
        {"icon": "📊", "titulo": "Revisá márgenes en reportes", "detalle": "Consultá qué platos generan más ganancia y ajustá precios si es necesario"},
    ],
    "retail": [
        {"icon": "📦", "titulo": "Cargá tu catálogo de productos", "detalle": "Ingresá cada producto con precio de costo, precio de venta y unidad de medida"},
        {"icon": "🏪", "titulo": "Registrá tu stock inicial", "detalle": "Hacé un ajuste de inventario inicial para que el sistema parta con las cantidades reales"},
        {"icon": "💳", "titulo": "Configurá métodos de pago", "detalle": "Habilitá efectivo, tarjeta, transferencia u otros según cómo opera tu tienda"},
        {"icon": "🧾", "titulo": "Hacé tu primera venta en el POS", "detalle": "Buscá el producto, cobrá y emití el recibo. Es así de simple"},
        {"icon": "📊", "titulo": "Revisá el reporte diario", "detalle": "Al cerrar caja verás ventas, COGS y ganancia bruta del día"},
    ],
    "taller": [
        {"icon": "🔧", "titulo": "Cargá tus servicios", "detalle": "Ingresá los servicios que ofrecés (cambio de aceite, frenos, diagnóstico) con su precio"},
        {"icon": "📦", "titulo": "Cargá tus repuestos", "detalle": "Registrá cada repuesto con stock, costo y precio de venta"},
        {"icon": "👤", "titulo": "Creá tu primer cliente", "detalle": "Registrá el cliente con sus datos y los vehículos asociados"},
        {"icon": "📋", "titulo": "Abrí una orden de trabajo", "detalle": "Asociá servicios y repuestos a la orden. El sistema calcula el total automáticamente"},
        {"icon": "🧾", "titulo": "Cerrá y cobrá la orden", "detalle": "Al completar la orden se descuenta el stock de repuestos y se registra el ingreso"},
    ],
}

_SECTOR_ICONS: dict[str, str] = {
    "panaderia": "🥐",
    "restaurante": "🍴",
    "retail": "🛍️",
    "taller": "🔧",
}

_DEFAULT_STEPS = [
    {"icon": "⚙️", "titulo": "Configurá tu empresa", "detalle": "Completá la información básica: RUC, dirección, moneda y zona horaria"},
    {"icon": "📦", "titulo": "Cargá tus productos", "detalle": "Ingresá tu catálogo con precios y unidades de medida correctas"},
    {"icon": "🛒", "titulo": "Registrá tus compras", "detalle": "Cada compra recibida actualiza el stock y el costo promedio automáticamente"},
    {"icon": "🧾", "titulo": "Empezá a vender", "detalle": "Usá el POS para registrar ventas y cerrá caja al final del día"},
    {"icon": "📊", "titulo": "Revisá tus reportes", "detalle": "Consultá ventas, gastos y ganancia neta en el módulo de reportes"},
]


def _get_sector_key(sector_nombre: str | None) -> str | None:
    if not sector_nombre:
        return None
    s = sector_nombre.lower()
    if "panaderia" in s or "panadería" in s or "bakery" in s:
        return "panaderia"
    if "restaurante" in s or "restaurant" in s:
        return "restaurante"
    if "retail" in s or "tienda" in s:
        return "retail"
    if "taller" in s or "mecanic" in s:
        return "taller"
    return None


def enviar_correo_bienvenida(
    user_email: str,
    username: str,
    empresa_nombre: str,
    background_tasks: BackgroundTasks,
    nombre_usuario: str = None,
    is_admin_company: bool = False,
    sector_nombre: str | None = None,
) -> None:
    token = generar_token_email(user_email)
    base = (getattr(settings, "PASSWORD_RESET_URL_BASE", None) or settings.FRONTEND_URL).rstrip("/")
    enlace = f"{base}/set-password?token={token}"
    sector_key = _get_sector_key(sector_nombre)
    pasos = _SECTOR_STEPS.get(sector_key, _DEFAULT_STEPS) if sector_key else _DEFAULT_STEPS
    contexto = {
        "nombre_empresa": empresa_nombre,
        "nombre_usuario": nombre_usuario or username,
        "username": username,
        "email": user_email,
        "enlace": enlace,
        "anio": datetime.now().year,
        "sector_nombre": sector_nombre or "",
        "sector_icono": _SECTOR_ICONS.get(sector_key, "🏢") if sector_key else "🏢",
        "pasos": pasos,
    }
    # Selecciona plantilla según si es admin de empresa
    template_name = "bienvenida_admin_empresa.html" if is_admin_company else "bienvenida.html"
    html_content = render_template(template_name, contexto)
    subject = "¡Bienvenido a GestiqCloud!" if is_admin_company else "Bienvenido a GestiqCloud"

    if getattr(settings, "ENV", "development") == "development" and (
        getattr(settings, "EMAIL_DEV_LOG_ONLY", False) or not getattr(settings, "EMAIL_HOST", None)
    ):
        logger.info("[DEV EMAIL] Bienvenida link: %s", enlace)
    background_tasks.add_task(send_email_mailtrap, user_email, subject, html_content)
    try:
        logger.info("Queued welcome email to %s (admin=%s)", user_email, is_admin_company)
    except Exception:
        pass


def reenviar_correo_reset(user_email: str, background_tasks: BackgroundTasks) -> None:
    token = generar_token_email(user_email)
    base = (getattr(settings, "PASSWORD_RESET_URL_BASE", None) or settings.FRONTEND_URL).rstrip("/")
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
        getattr(settings, "EMAIL_DEV_LOG_ONLY", False) or not getattr(settings, "EMAIL_HOST", None)
    ):
        logger.info("[DEV EMAIL] Reset link: %s", enlace)
    background_tasks.add_task(
        send_email_mailtrap, user_email, "Restablecer tu contraseña", html_content
    )
