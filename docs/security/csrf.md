# CSRF — protección contra Cross-Site Request Forgery

Estado: ✅ montado y con tests de integración (punto 5 de la base técnica).

## Modelo

Double-submit cookie + token de sesión. El backend acepta una petición mutable si el
header coincide con la cookie `csrf_token` **o** con el token guardado en la sesión.

- **Emisión**: `GET /api/v1/tenant/auth/csrf` y `GET /api/v1/admin/auth/csrf`
  (`app/api/v1/{tenant,admin}/auth.py`) llaman a `issue_csrf_token` (`app/core/csrf.py`),
  guardan el token en `session["csrf"]` y setean la cookie `csrf_token`
  (`httponly=False` para que el JS la lea, `samesite=lax`, `secure` en prod).
- **Validación**: `RequireCSRFMiddleware` (`app/middleware/require_csrf.py`), montado en
  `app/main.py` bajo flag `CSRF_ENABLED` (default on), ANTES de `SessionMiddleware`
  (queda más interno y ve `request.state.session`).
- **Header aceptado**: `X-CSRF-Token` o `X-CSRF`.

## Qué exige y qué exime

| Caso | CSRF |
|---|---|
| `GET` / `HEAD` / `OPTIONS` (métodos seguros) | No |
| Sufijos `/auth/login`, `/auth/refresh`, `/auth/logout` | Exento |
| Segmento `/webhook/` (singular) y sufijo `/webhook` — webhooks ENTRANTES externos (Telegram, Stripe, pasarelas), autenticados por firma/secret propio | Exento |
| `/webhooks/` (plural) — gestión del tenant desde el navegador | **Exige** CSRF |
| Resto de `POST/PUT/PATCH/DELETE` | **Exige** CSRF |

Fallo → `403 {"detail": "CSRF token missing/invalid"}`.

## Frontend

Los clientes HTTP de `apps/tenant` y `apps/admin` (`@shared/http` `createClient`) leen la
cookie `csrf_token` y la reenvían en `X-CSRFToken`/`X-CSRF` en métodos no seguros. El token
se obtiene vía `GET .../auth/csrf` (se precalienta en el flujo de refresh).

## Bypass bajo pytest

El middleware se salta si `PYTEST_CURRENT_TEST` está en el entorno (coherente con
`with_access_claims`), salvo que `PYTEST_DISABLE_CSRF_BYPASS=1`. Los tests de integración
(`app/tests/security/test_csrf_middleware.py`) activan ese flag para validar la protección
real: GET pasa, POST sin token → 403, double-submit válido → 200, exenciones login/webhook.

## Pendiente

- Validar en producción tras el Cloudflare Worker que el header `X-CSRF-Token` no se
  elimina en el proxy (el Worker reenvía cabeceras; confirmar en un POST real).
