# ADR-0001: Edge Worker (Cloudflare) para CORS y cookies

## Contexto
- Admin y Tenant viven en dominios distintos (`admin.gestiqcloud.com`, `www.gestiqcloud.com`).
- Backend expone API; requiere CORS estricto y cookies con atributos seguros (SameSite, Secure, dominio).
- Se necesita request-id consistente y headers de seguridad.

## Decisión
- Colocar un Cloudflare Worker como gateway en `admin.gestiqcloud.com/api/*` y `www.gestiqcloud.com/api/*` que:
  - Limite orígenes permitidos (`ALLOWED_ORIGINS`).
  - Reescriba `Set-Cookie` (Domain=.gestiqcloud.com, SameSite adecuado, Secure/HttpOnly).
  - Propague/generar `X-Request-Id` y añada headers de seguridad (HSTS, X-Frame-Options, etc.).
  - Haga proxy al backend en Render (`TARGET`/`UPSTREAM_BASE`).

## Consecuencias
- Frontends no necesitan lógica especial de CORS/cookies; backend puede asumir dominio consistente.
- Riesgo: mal configurar orígenes/cookies bloquea login; monitorear con curl y métricas de auth.
- Operación: despliegue vía `wrangler publish`, rutas CF actualizadas, secretos en CF (no en repo).

## Referencias
- Código: `workers/edge-gateway.js`, config `workers/wrangler.toml`.
- Doc: `workers/README.md`, `docs/payments-einvoicing.md` (cookies en auth), `docs/observabilidad.md` (request-id/logs).
