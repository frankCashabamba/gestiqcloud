# Environment Configuration Unification

**Date:** January 2026
**Status:** ✅ COMPLETED
**Impact:** Eliminates confusion from multiple .env files

---

## Summary

### Before (❌ PROBLEMATIC)
```
.env                 ← Could be anything
.env.local           ← Git-ignored dev secrets
.env.production      ← Separate production file
```

**Problems:**
- 3 files = ambiguity which one is active
- `_load_env_all()` searches multiple directories
- Different files in different environments
- Developer confusion on startup
- Production deploys hard to track

### After (✅ UNIFIED)
```
.env                 ← Single source of truth for ALL environments
```

**How it works:**
- ONE `.env` file at repository root
- `ENVIRONMENT` variable selects behavior (development/staging/production)
- Backend startup validates required vars based on ENVIRONMENT
- Cloudflare Worker gets env via wrangler.toml
- Frontends get vars at build time via Vite

---

## Key Changes

### 1. New `env_loader.py`
```python
# File: app/config/env_loader.py
def get_env_file_path() -> Path:
    """Returns SINGLE .env file path"""
    repo_root / ".env"  # Always here, never .env.production or .env.local

def load_env_file(env_path) -> dict:
    """Reads .env once, returns variables"""

def inject_env_variables(variables) -> None:
    """Injects into os.environ only if not already set"""
```

**Benefit:** Deterministic loading, no directory search, single file.

### 2. Updated `settings.py`
```python
# OLD: Multiple _load_env() and _load_env_all() functions
# NEW: Single import
from app.config.env_loader import get_env_file_path, load_env_file, inject_env_variables

_ENV_FILE = get_env_file_path()           # Always: .env
_ENV_VARS = load_env_file(_ENV_FILE)      # Load once
inject_env_variables(_ENV_VARS)            # Inject to os.environ
```

**Benefit:** Cleaner, debuggable, clear log output.

### 3. Renamed ENV → ENVIRONMENT
```python
# OLD
ENV: Literal["development", "production"] = "development"

# NEW
ENVIRONMENT: Literal["development", "staging", "production"] = Field(
    default="development",
    description="Environment: development, staging, or production"
)
```

**Benefit:** Clearer naming (ENV is ambiguous), supports staging tier, documented.

---

## How to Use

### Development
```bash
# 1. Ensure .env exists in repository root
ls .env

# 2. Edit for local development
ENVIRONMENT=development
DATABASE_URL=postgresql://user:pass@localhost:5432/gestiqcloud
REDIS_URL=redis://localhost:6379/0
# etc.

# 3. Start backend (will read .env automatically)
cd apps/backend
uvicorn app.main:app --reload

# Logs will show:
# [env_loader] Looking for .env at: /path/to/gestiqcloud/.env (exists=True)
# [env_loader] Loaded 50 variables from /path/to/gestiqcloud/.env
# [settings] ENVIRONMENT=development ENV_FILE=/path/to/gestiqcloud/.env SECRET_KEY_PRESENT=True
```

### Staging
```bash
# 1. Copy .env to staging server
scp .env user@staging.example.com:/app/.env

# 2. Edit .env on server with staging values
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/gestiqcloud
CORS_ORIGINS=https://admin-staging.example.com,https://app-staging.example.com
# etc.

# 3. Start backend
cd /app/apps/backend
ENVIRONMENT=staging uvicorn app.main:app --host 0.0.0.0

# Logs will show:
# [settings] ENVIRONMENT=staging ENV_FILE=/app/.env SECRET_KEY_PRESENT=True
```

### Production
```bash
# 1. NEVER copy secrets in .env
# 2. Set environment variables via deployment platform:

# Render.com example:
# Dashboard → Environment → Add variables:
#   ENVIRONMENT=production
#   SECRET_KEY=****** (secret)
#   JWT_SECRET_KEY=****** (secret)
#   DATABASE_URL=postgresql://... (secret)
#   CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
#   etc.

# 3. Docker example:
docker run \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=****** \
  -e DATABASE_URL=postgresql://... \
  ... \
  gestiqcloud-api:latest

# 4. Logs will show:
# [env_loader] WARNING: ENV_FILE=/path/to/gestiqcloud/.env does not exist
# [settings] ENVIRONMENT=production ENV_FILE=<none> SECRET_KEY_PRESENT=True
# [settings] ✓ All production variables validated
```

---

## Validation at Startup

Backend validates ALL critical variables when `ENVIRONMENT=production`:

```python
# settings.py: assert_required_for_production()
if self.ENVIRONMENT == "production":
    required_vars = [
        "JWT_SECRET_KEY",       # Must be set
        "SECRET_KEY",           # Must be set
        "FRONTEND_URL",         # Must be set
        "DATABASE_URL",         # Must be set
        "CORS_ORIGINS",         # Must be set (not empty, no localhost)
        "EMAIL_HOST",           # Must be set
        "EMAIL_HOST_USER",      # Must be set
        "EMAIL_HOST_PASSWORD",  # Must be set
        "DEFAULT_FROM_EMAIL",   # Must be set
        "COOKIE_SECURE=True",   # Must be true
        "SESSION_COOKIE_NAME",  # Must be set
        "CSRF_COOKIE_NAME",     # Must be set
    ]

    # If any missing → raise RuntimeError and exit
    if missing:
        raise RuntimeError(
            f"❌ Variables de entorno obligatorias faltantes para producción: {missing}"
        )
```

**Benefit:** Production deploy fails fast if misconfigured, not after 1 hour of debugging.

---

## File Organization

### `.env` (SINGLE FILE)
- **Location:** Repository root (`gestiqcloud/.env`)
- **Content:** All variables for current environment
- **Git:** Listed in `.gitignore` (never commit secrets)
- **Backup:** Back up before editing production .env

### `.env.example` (DOCUMENTATION)
- **Location:** Repository root (`gestiqcloud/.env.example`)
- **Content:** Template with all variables and descriptions
- **Git:** COMMITTED to repo (safe reference)
- **Purpose:** Show developers what variables exist and what they mean

### `.env.local` (DEPRECATED)
- **Old:** Used for development secrets
- **Now:** Not needed (use `.env` instead)
- **Note:** Can delete if you had one

### `.env.production` (DEPRECATED)
- **Old:** Separate file for production config
- **Now:** Use ONE `.env` with `ENVIRONMENT=production`
- **Note:** If you had one, merge into `.env` and set ENVIRONMENT variable in deployment platform

---

## Environment Variables by Tier

### Development (ENVIRONMENT=development)
```env
ENVIRONMENT=development
DATABASE_URL=postgresql://user:pass@localhost:5432/gestiqcloud
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173,http://localhost:8081,http://localhost:8082
VITE_ELECTRIC_ENABLED=0
COOKIE_SECURE=false
```

### Staging (ENVIRONMENT=staging)
```env
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/gestiqcloud
REDIS_URL=rediss://staging-redis:6379/0
CORS_ORIGINS=https://admin-staging.example.com,https://app-staging.example.com
VITE_ELECTRIC_ENABLED=0
COOKIE_SECURE=true
COOKIE_DOMAIN=.example.com
```

### Production (ENVIRONMENT=production)
```env
ENVIRONMENT=production
# All other vars must be set via deployment platform secrets
# (not in .env file)
DATABASE_URL=*** (from Render/Heroku/K8s secret)
SECRET_KEY=*** (from secret manager)
JWT_SECRET_KEY=*** (from secret manager)
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
VITE_ELECTRIC_ENABLED=0  # or 1 if setup
COOKIE_SECURE=true
COOKIE_DOMAIN=.gestiqcloud.com
```

---

## Troubleshooting

### "ENV_FILE_USED=<none>"
**Problem:** Backend couldn't find .env file
**Solution:**
```bash
# Check if .env exists
ls -la .env

# If missing, copy from example
cp .env.example .env

# Edit with your values
nano .env
```

### "CORS_ORIGINS is empty in production"
**Problem:** Production startup failed
**Solution:**
```bash
# Check ENV_FILE contains CORS_ORIGINS
grep CORS_ORIGINS .env

# Ensure it's not commented out
# Should look like:
# CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
```

### "CORS_ORIGINS contains localhost in production"
**Problem:** Development value accidentally deployed
**Solution:**
```bash
# Check production .env
grep CORS_ORIGINS .env

# Remove localhost values
# Should ONLY have production domains
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com
```

### "ElectricSQL configuration error: VITE_ELECTRIC_URL is required"
**Problem:** ElectricSQL enabled but URL not set
**Solution:**
```bash
# Either disable ElectricSQL:
VITE_ELECTRIC_ENABLED=0

# Or set the URL:
VITE_ELECTRIC_ENABLED=1
VITE_ELECTRIC_URL=ws://electric.internal:3000
```

---

## Migration Path

If you have old `.env.local` or `.env.production`:

1. **Read current values:**
   ```bash
   cat .env.local
   cat .env.production
   ```

2. **Merge into single `.env`:**
   ```bash
   # Copy .env.example to .env
   cp .env.example .env

   # Edit .env with values from both old files
   nano .env
   ```

3. **Set ENVIRONMENT variable:**
   ```bash
   # In .env
   ENVIRONMENT=development  # or staging/production
   ```

4. **Delete old files:**
   ```bash
   rm .env.local .env.production  # (if they existed)
   ```

5. **Test startup:**
   ```bash
   cd apps/backend
   python -c "from app.config.settings import settings; print(f'✓ Settings loaded: ENVIRONMENT={settings.ENVIRONMENT}')"
   ```

---

## Validation Checklist

- [ ] `.env` file exists in repository root
- [ ] `.env` contains `ENVIRONMENT=development|staging|production`
- [ ] `.env` is in `.gitignore` (not committed)
- [ ] `.env.example` is in git (documentation)
- [ ] Backend startup logs show `[env_loader]` messages
- [ ] `CORS_ORIGINS` doesn't contain localhost in production
- [ ] `COOKIE_SECURE=true` in staging/production
- [ ] Email variables configured if emails are needed
- [ ] Database URL is valid (test connection works)
- [ ] Redis URL is valid if caching enabled
- [ ] ElectricSQL URL is set if VITE_ELECTRIC_ENABLED=1

---

## References

- **Settings file:** `apps/backend/app/config/settings.py`
- **Env loader:** `apps/backend/app/config/env_loader.py`
- **Example template:** `.env.example`
- **Validation:** `settings.assert_required_for_production()`

---

## Questions?

1. **Why single .env instead of per-environment files?**
   - One source of truth
   - Clearer deployment process
   - Easier to debug
   - Matches industry best practices (12-factor app)

2. **Can I use environment variables directly?**
   - Yes! System env vars override .env file
   - Useful for Docker/Kubernetes: `docker run -e DATABASE_URL=...`

3. **How do I rotate secrets?**
   - Update value in .env or deployment platform
   - Restart application
   - For certificates: use AWS Secrets Manager (future phase)

4. **Is .env.example safe to commit?**
   - Yes! It has placeholder values only
   - Never commit actual secrets

---

**Status:** ✅ Ready for Production
**Last Updated:** January 2026
