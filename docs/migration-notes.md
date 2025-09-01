# Migration Notes: JWT Unification on PyJWT

## Environment Variables
Set these in non-dev environments (dev/test have safe defaults):

- `JWT_SECRET` (or legacy `JWT_SECRET_KEY`)
- `JWT_ALGORITHM` (default `HS256`)
- `ACCESS_TTL_MINUTES` (or legacy `ACCESS_TOKEN_EXPIRE_MINUTES`)
- `REFRESH_TTL_DAYS` (or legacy `REFRESH_TOKEN_EXPIRE_DAYS`)

## API Compatibility
- Preferred:
  - Admin login: `POST /api/v1/admin/auth/login`
  - Tenant login: `POST /api/v1/tenant/auth/login`
- Legacy alias retained: `POST /api/v1/auth/login` (tenant-first, then admin)

## CSRF (Admin JSON APIs)
- If CSRF is enforced, the FE must include `X-CSRF-Token`.
- Use `GET /api/v1/admin/auth/csrf` to bootstrap and set `csrf_token` cookie in dev.

## Post-Deploy Smoke Checks
- Admin login, call `/api/v1/me/admin` with Bearer token.
- Tenant login, refresh rotation flow.
- Protected endpoints that depend on `Authorization: Bearer`.

## Notes
- `python-jose` removed; `PyJWT` retained.
- All JWT decode paths route through `JwtService`.
- Error handling standardized on `jwt.ExpiredSignatureError` and `jwt.InvalidTokenError`.

