# app/core/security_headers.py
from backend.app.config.settings import settings
from starlette.requests import Request
from starlette.responses import Response


def _csp_for_request(request: Request) -> str:
    # Orígenes externos opcionales (deja "" si no aplican)
    API = getattr(settings, "PUBLIC_API_ORIGIN", "")  # p.ej. "https://api.miapp.com"
    CDN = getattr(settings, "PUBLIC_ASSETS_CDN", "")  # p.ej. "https://cdn.miapp.com"
    FONTS_CSS = getattr(settings, "FONTS_STYLES_ORIGIN", "")  # p.ej. "https://fonts.googleapis.com"
    FONTS_BIN = getattr(settings, "FONTS_BINARY_ORIGIN", "")  # p.ej. "https://fonts.gstatic.com"
    # Si no usas estos orígenes, déjalos en blanco; el join los ignora.

    def join_src(*vals: str) -> str:
        return " ".join(v for v in vals if v)

    if settings.ENV == "production":
        parts = [
            "default-src 'self' blob:",  # permite blob URLs si usas workers o downloads
            "base-uri 'none'",  # más estricto que 'self'
            f"frame-ancestors {'self' if settings.ALLOW_EMBED else 'none'}",
            "object-src 'none'",
            "form-action 'self'",
            "upgrade-insecure-requests",
            # Recursos
            join_src("img-src", "'self'", "data:", "blob:", CDN),
            join_src("font-src", "'self'", "data:", FONTS_BIN),
            join_src("style-src", "'self'", FONTS_CSS),  # sin 'unsafe-inline' en prod (ideal)
            join_src("script-src", "'self'", CDN),  # no inline, no eval
            join_src("connect-src", "'self'", API),  # API separada si aplica
            "media-src 'self'",
            "manifest-src 'self'",
            "worker-src 'self' blob:",
            # Añade aquí, si procede:
            # join_src("frame-src", "https://*.pasarela.com"),       # pagos/embeds externos
        ]
        if settings.CSP_REPORT_URI:
            parts.append(f"report-uri {settings.CSP_REPORT_URI}")
        return "; ".join(parts)
    else:
        # DEV: Vite/HMR
        # Get dev hosts from settings or use defaults
        dev_hosts_list = getattr(settings, "CSP_DEV_HOSTS", "http://localhost:5173 http://localhost:5174")
        dev_hosts = dev_hosts_list if isinstance(dev_hosts_list, str) else " ".join(dev_hosts_list)
        
        # Convert HTTP hosts to WS equivalents
        dev_ws_list = []
        for host in dev_hosts.split():
            if host.startswith("http://"):
                dev_ws_list.append("ws://" + host[7:])  # Replace http:// with ws://
            elif host.startswith("https://"):
                dev_ws_list.append("wss://" + host[8:])  # Replace https:// with wss://
            else:
                dev_ws_list.append(host)
        dev_ws = " ".join(dev_ws_list)
        
        return "; ".join(
            [
                "default-src 'self' blob: data:",
                "object-src 'none'",
                "frame-ancestors 'none'",
                "form-action 'self'",
                # Permisos para Vite: inline + eval + hosts/WS
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {dev_hosts}",
                f"style-src 'self' 'unsafe-inline' {dev_hosts}",
                f"font-src 'self' data: {dev_hosts}",
                f"img-src 'self' data: blob: {dev_hosts}",
                f"connect-src 'self' {dev_hosts} {dev_ws}",
                "media-src 'self'",
                "manifest-src 'self'",
                "worker-src 'self' blob:",
            ]
        )


async def security_headers_middleware(request: Request, call_next):
    resp: Response = await call_next(request)

    # X-Frame-Options: mantenlo por compat (CSP frame-ancestors manda)
    resp.headers["X-Frame-Options"] = "SAMEORIGIN" if settings.ALLOW_EMBED else "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = settings.REFERRER_POLICY
    resp.headers["Content-Security-Policy"] = _csp_for_request(request)

    # HSTS solo prod + https
    if settings.ENV == "production" and settings.HSTS_ENABLED and request.url.scheme == "https":
        resp.headers["Strict-Transport-Security"] = "max-age=15552000; includeSubDomains; preload"

    # Opcionales según settings
    if settings.COOP_ENABLED:
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if settings.COEP_ENABLED:
        resp.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    if settings.CORP_POLICY:
        resp.headers["Cross-Origin-Resource-Policy"] = settings.CORP_POLICY

    # Evita cache agresiva en HTML dinámico
    if resp.media_type in ("text/html", "application/xhtml+xml"):
        resp.headers.setdefault("Cache-Control", "no-store")

    resp.headers["Permissions-Policy"] = settings.PERMISSIONS_POLICY
    return resp
