# Edge Gateway (Cloudflare Worker)

This Worker fronts the backend API with restrictive CORS, cookie hardening and request ID propagation. In the current setup it is routed at `admin.gestiqcloud.com/api/*` (Admin) and `www.gestiqcloud.com/api/*` (Tenant). The upstream API runs on Render.

## Prerequisites
- Cloudflare account + zone `gestiqcloud.com`
- `wrangler` CLI installed and authenticated

## Configure
Edit `workers/wrangler.toml` and set:
- `vars.TARGET` (o `vars.UPSTREAM_BASE`): Public URL of the backend (Render), sin barra final. Ej.: `https://gestiqcloud-api.onrender.com`
- `vars.ALLOWED_ORIGINS`: Comma-separated allowed origins. Ej.: `https://admin.gestiqcloud.com,https://www.gestiqcloud.com`
- `vars.COOKIE_DOMAIN`: `.gestiqcloud.com`
- `vars.HSTS_ENABLED`: `"1"`

Alternatively set them with `wrangler secret put` / `wrangler kv` if preferred.

## Publish
```
cd workers
wrangler publish
```
Add routes in Cloudflare (Dashboard or wrangler):
- `admin.gestiqcloud.com/api/*`
- `www.gestiqcloud.com/api/*`

## What it does
- CORS (credentials=true), only echoes allowed Origin
- Security headers: HSTS (if HTTPS), X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Request ID: generates/propagates `X-Request-Id`
- Cookie rewriting for upstream `Set-Cookie`:
  - `Domain=.gestiqcloud.com`
  - `Secure; HttpOnly` for all
  - `SameSite=None` for `refresh_token`
  - `SameSite=Lax` for `access_token`

## Quick tests (curl)
- Admin/Tenant health
```
curl -i -H "Origin: https://admin.gestiqcloud.com" https://admin.gestiqcloud.com/api/v1/health
```

- Tenant login
```
curl -i -s -X POST https://api.gestiqcloud.com/v1/tenant/auth/login \
  -H "Origin: https://gestiqcloud.com" \
  -H "Content-Type: application/json" \
  --data '{"identificador":"USER","password":"secret"}' -c cookies.txt
```
Should return 200, CORS headers, and Set-Cookie for `refresh_token` (SameSite=None) and `access_token` (SameSite=Lax).

- Refresh
```
curl -i -s -X POST https://api.gestiqcloud.com/v1/tenant/auth/refresh \
  -H "Origin: https://gestiqcloud.com" -b cookies.txt -c cookies.txt
```
Should rotate `refresh_token` and return a new `access_token`.

- Preflight
```
curl -i -s -X OPTIONS https://api.gestiqcloud.com/v1/tenant/auth/login \
  -H "Origin: https://gestiqcloud.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization"
```
Should respond 204 with CORS headers and Allow-Credentials: true.

## Troubleshooting
- 403 origin_not_allowed: Add the Origin to `ALLOWED_ORIGINS`.
- Missing cookies: Ensure backend sets Set-Cookie in login/refresh; gateway rewrites attributes.
- Cross-site cookie blocked: confirm `SameSite=None; Secure` on `refresh_token` and HTTPS in browser.
- HSTS not present: ensure the request is HTTPS and `HSTS_ENABLED=1`.
