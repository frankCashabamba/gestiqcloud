# Quick Start: Environment Configuration

## TL;DR

```bash
# 1. Copy template
cp .env.example .env

# 2. Edit for your environment
nano .env

# 3. Set ENVIRONMENT variable
ENVIRONMENT=development  # development, staging, or production

# 4. Start backend (reads .env automatically)
cd apps/backend
python -m uvicorn app.main:app --reload

# Logs should show:
# [env_loader] Loaded 50 variables from /path/to/gestiqcloud/.env
# [settings] ENVIRONMENT=development ENV_FILE=... SECRET_KEY_PRESENT=True
```

---

## One .env File for All Environments

```
.env  ← Single file, select environment with ENVIRONMENT variable
```

**No more:**
- ❌ `.env.local` (dev secrets)
- ❌ `.env.production` (prod config)
- ❌ Searching 4 directories

---

## Environment Setup Examples

### Development
```env
ENVIRONMENT=development
DATABASE_URL=postgresql://user:pass@localhost:5432/gestiqcloud
CORS_ORIGINS=http://localhost:5173,http://localhost:8081,http://localhost:8082
VITE_ELECTRIC_ENABLED=0
COOKIE_SECURE=false
```

### Staging
```env
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/gestiqcloud
CORS_ORIGINS=https://admin-staging.example.com,https://app-staging.example.com
VITE_ELECTRIC_ENABLED=0
COOKIE_SECURE=true
COOKIE_DOMAIN=.example.com
```

### Production
```bash
# Set via deployment platform (Render, Heroku, K8s), NOT in .env file
ENVIRONMENT=production
SECRET_KEY=****** (from secret manager)
JWT_SECRET_KEY=****** (from secret manager)
DATABASE_URL=****** (from secret manager)
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
COOKIE_SECURE=true
COOKIE_DOMAIN=.gestiqcloud.com
```

---

## Critical Variables Validated at Startup

**In Production:**
- ✅ ENVIRONMENT=production (set)
- ✅ SECRET_KEY (set, not placeholder)
- ✅ JWT_SECRET_KEY (set)
- ✅ DATABASE_URL (valid connection)
- ✅ CORS_ORIGINS (set, no localhost)
- ✅ EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL (all set)
- ✅ COOKIE_SECURE=true

**If any missing → app fails to start with error message**

---

## Common Scenarios

### Scenario 1: New developer (local setup)
```bash
cd gestiqcloud
cp .env.example .env
# Edit .env: set DATABASE_URL to local PostgreSQL
# Edit .env: ensure ENVIRONMENT=development
python -m uvicorn apps/backend/app.main:app --reload
# ✅ Should start successfully
```

### Scenario 2: Deploy to staging
```bash
# On staging server:
scp .env user@staging:/app/.env
ssh user@staging
cd /app
# Edit .env: change DATABASE_URL, CORS_ORIGINS, etc.
# Set ENVIRONMENT=staging in .env
docker build -t app:latest .
docker run -e ENVIRONMENT=staging app:latest
# ✅ Should start successfully, validate all vars
```

### Scenario 3: Deploy to production
```bash
# Via Render.com dashboard:
# Dashboard → Environment → Add variables:
ENVIRONMENT=production
SECRET_KEY=<generated secret>
JWT_SECRET_KEY=<generated secret>
DATABASE_URL=<connection string>
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
# etc.

# App starts automatically with these env vars
# ✅ Should start successfully
# ✅ All production requirements validated
```

---

## Validation at Startup

### Backend Log Output
```
[env_loader] Looking for .env at: /path/to/gestiqcloud/.env (exists=True)
[env_loader] Loaded 50 variables from /path/to/gestiqcloud/.env
[settings] ENVIRONMENT=development ENV_FILE=/path/to/gestiqcloud/.env SECRET_KEY_PRESENT=True
```

### If Production Misconfigured
```
RuntimeError: ❌ Variables de entorno obligatorias faltantes para producción:
['JWT_SECRET_KEY', 'CORS_ORIGINS (not localhost)', 'DEFAULT_FROM_EMAIL']
```

**Fix immediately:**
```bash
# Check what's missing
grep -E "JWT_SECRET_KEY|CORS_ORIGINS|DEFAULT_FROM_EMAIL" .env

# Add/fix values in .env or deployment platform

# Restart
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ENV_FILE_USED=<none>` | `.env` not found. Run: `cp .env.example .env` |
| `CORS_ORIGINS is empty` | Check `.env` has `CORS_ORIGINS=...`. Uncomment if needed. |
| `CORS_ORIGINS contains localhost in production` | Remove `localhost` from CORS_ORIGINS when ENVIRONMENT=production |
| `SECRET_KEY too short` | Use at least 32 chars. Run: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ElectricSQL configuration error` | Either set `VITE_ELECTRIC_ENABLED=0` or set `VITE_ELECTRIC_URL=...` |

---

## Files Reference

```
gestiqcloud/
├── .env                          ← SINGLE config file (git-ignored)
├── .env.example                  ← Template (committed to git)
├── ENV_UNIFICATION.md            ← Full documentation
├── RESUMEN_HARDCODEOS_VERIFICADO.md ← Verification report
├── apps/
│   └── backend/
│       └── app/config/
│           ├── env_loader.py     ← Loading implementation
│           └── settings.py       ← Settings + validation
├── .gitignore                    ← Make sure .env is ignored
```

---

## One-Liner Tests

```bash
# Test env loading
python -c "from app.config.env_loader import get_env_file_path; print(get_env_file_path())"

# Test settings
python -c "from app.config.settings import settings; print(f'✓ ENVIRONMENT={settings.ENVIRONMENT}')"

# Test production validation (should fail if vars missing)
ENVIRONMENT=production python -c "from app.config.settings import settings"

# Test CORS validation (should fail if localhost in prod)
grep "localhost" .env  # If ENVIRONMENT=production and result is CORS, that's wrong
```

---

## That's It!

Single `.env` file for all environments. Just set `ENVIRONMENT=` and the system validates everything at startup.

See `ENV_UNIFICATION.md` for complete details.
