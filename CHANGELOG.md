# Changelog

## feat(auth): Unify JWT on PyJWT via JwtService

- Add `JwtService` + `JwtSettings` (HS256 by default with safe dev/test defaults).
- `JwtSettings` reads from env (via app settings) with legacy compatibility:
  - `JWT_SECRET` or `JWT_SECRET_KEY`
  - `JWT_ALGORITHM`
  - `ACCESS_TTL_MINUTES` or `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `REFRESH_TTL_DAYS` or `REFRESH_TOKEN_EXPIRE_DAYS`
- Replace legacy jose usages with `JwtService` in middleware and protected route;
  handle `jwt.ExpiredSignatureError` and `jwt.InvalidTokenError` explicitly.
- Remove `python-jose` from backend dependencies; keep `PyJWT`.
- Keep `/api/v1/auth/login` alias (tenant-first, admin fallback) to ease FE migration.
- Test harness stabilized:
  - Inject required envs early, ensure identity + refresh tables in SQLite; `StaticPool` engine.
  - Admin factories are idempotent to avoid UNIQUE constraint errors.
- Full suite passes locally in this environment (two expected xfails: CSRF CRUD in minimal env; modulos admin mount variability).

