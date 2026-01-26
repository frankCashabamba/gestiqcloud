# ✅ Checklist de Validación - Hardcodeos Arreglados

**Documento:** Checklist para validar que todos los hardcodeos han sido arreglados correctamente
**Última actualización:** 15 Enero 2026
**Estado:** 🟢 Listo para Validación

---

## 🔴 CRÍTICOS (8/8 - DEBE validar todos)

### 1. DEFAULT_FROM_EMAIL
- [ ] En desarrollo: Funciona sin variable (fallback a logger)
- [ ] En producción: Error si no está configurado
- [ ] En `app/config/settings.py`: default=""
- [ ] En `startup_validation.py`: Se valida en environment=production

**Test:**
```bash
ENVIRONMENT=production python -c "from app.config.settings import settings"
# Resultado esperado: ValidationError
```

---

### 2. REDIS_URL Fallback
- [ ] En `celery_app.py`: No hay fallback a localhost
- [ ] En producción: Error si contiene "localhost"
- [ ] En startup: Se valida en `startup_validation.py`

**Test:**
```bash
ENVIRONMENT=production REDIS_URL=redis://localhost:6379/0 python -c "from celery_app import _redis_url"
# Resultado esperado: RuntimeError
```

---

### 3. test-login.html
- [ ] No contiene credenciales hardcodeadas
- [ ] API_BASE es campo de entrada (no hardcodeado)
- [ ] Password es input secreto (no se almacena)
- [ ] Avisos de seguridad visibles

**Test:**
```bash
grep -n "Admin.2025\|https://api.gestiqcloud.com" apps/admin/test-login.html
# Resultado esperado: vacío (no encontrado)
```

---

### 4. CORS_ORIGINS
- [ ] En `settings.py`: default=[] (vacío)
- [ ] En producción: Error si vacío o contiene localhost
- [ ] En `startup_validation.py`: Validación estricta
- [ ] En desarrollo: Permite sin validación

**Test:**
```bash
ENVIRONMENT=production python -c "from app.config.settings import settings"
# Resultado esperado: ValidationError si CORS_ORIGINS no está
```

---

### 5. ElectricSQL URL
- [ ] En `electric.ts`: No fallback a localhost
- [ ] Si vacío: Error claro en console
- [ ] Requiere `VITE_ELECTRIC_URL`

**Test:**
```bash
grep -n "localhost:5133" apps/tenant/src/lib/electric.ts
# Resultado esperado: vacío
```

---

### 6. Cloudflare Workers
- [ ] En `wrangler.toml`: Sin hardcodeos de dominios
- [ ] En `edge-gateway.js`: ALLOWED_ORIGINS desde env
- [ ] Variables desde environment

**Test:**
```bash
grep -n "gestiqcloud-api.onrender.com\|admin.gestiqcloud.com" workers/wrangler.toml
# Resultado esperado: vacío o comentado
```

---

### 7. E-invoicing CERT_PASSWORD
- [ ] En `einvoicing_tasks.py`: Usa `get_certificate_password()`
- [ ] En `secrets.py`: Implementado con AWS Secrets Manager + env vars
- [ ] Error explícito si no encontrado

**Test:**
```bash
python -c "from app.services.secrets import get_certificate_password; get_certificate_password('nonexistent', 'ECU')"
# Resultado esperado: ValueError
```

---

### 8. render.yaml dominios
- [ ] `DEFAULT_FROM_EMAIL`: sync: false (no value)
- [ ] Dominios de tenant: NO en yaml (comentado)
- [ ] Dominios de admin: NO en yaml (comentado)
- [ ] Configuración vía Render Dashboard

**Test:**
```bash
grep -n "domains:\|DEFAULT_FROM_EMAIL.*value:" render.yaml
# Resultado esperado: solo comentarios
```

---

## 🟡 MODERADOS (12 - Validar la mayoria)

### 9. API URL Fallback Vite
- [ ] En `vite.config.ts`: fallback a `/v1` es aceptable
- [ ] `VITE_API_URL` está documentado en .env.example

**Test:**
```bash
grep VITE_API_URL .env.example apps/tenant/.env.example
# Resultado esperado: encontrado
```

---

### 10. Storage Keys Centralizados
- [ ] `apps/tenant/src/constants/storage.ts` existe
- [ ] Importado en componentes que lo necesitan

**Test:**
```bash
grep -l "STORAGE_KEYS\|constants/storage" apps/tenant/src/**/*.tsx
# Resultado esperado: múltiples archivos
```

---

### 11. API Routes Versionadas
- [ ] `constants/api.ts` tiene rutas centralizadas
- [ ] Versión de API en una sola ubicación

**Test:**
```bash
grep -n "api/v1" apps/admin/src/constants/api.ts
# Resultado esperado: 1 ubicación
```

---

### 12. Slug Empresa Fallback
- [ ] En `EmpresaLoader.tsx`: Fallback a 'default'
- [ ] No hay fallback a 'kusi-panaderia'

**Test:**
```bash
grep -n "kusi-panaderia" apps/tenant/src/pages/EmpresaLoader.tsx
# Resultado esperado: vacío
```

---

### 13. Plantillas Dashboard
- [ ] Dinámicas según DB (sector)
- [ ] Fallback a `default.tsx` es válido
- [ ] NO son hardcodeos

**Test:**
```bash
grep -n "import.*panaderia_pro\|import.*taller_pro" apps/tenant/src/pages/
# Resultado esperado: vacío (son dinámicas)
```

---

### 14. Credenciales Test Backend
- [ ] Usa random passwords con `secrets` module
- [ ] O usa pytest fixtures

**Test:**
```bash
grep -n "password.*=.*secret\|password.*=.*Admin" apps/backend/app/tests/test_*.py
# Resultado esperado: vacío o con generación random
```

---

### 15. Render Dashboard Variables
- [ ] EMAIL_HOST, EMAIL_PORT, etc.: sync: false
- [ ] Documentado en render.yaml

**Test:**
```bash
grep "sync: false" render.yaml | wc -l
# Resultado esperado: >10 (variables críticas)
```

---

### 16. Systemd Services
- [ ] `gestiq-worker-imports.service`: EnvironmentFile=/etc/gestiq/worker-imports.env
- [ ] README_ENV_CONFIG.md existe y está documentado
- [ ] Permisos: 600 para archivos .env

**Test:**
```bash
grep "EnvironmentFile" ops/systemd/gestiq-worker-imports.service
# Resultado esperado: encontrado

test -f ops/systemd/README_ENV_CONFIG.md
# Resultado esperado: exitoso
```

---

### 17. Database Fallback
- [ ] En `session.py`: Función `_get_database_url()` implementada
- [ ] Error explícito en producción si DB no está configurada
- [ ] Fallback a localhost SOLO en desarrollo

**Test:**
```bash
ENVIRONMENT=production python -c "from app.db.session import _get_database_url"
# Resultado esperado: RuntimeError si DATABASE_URL no existe
```

---

### 18. Render.yaml Configuración (Item #29)
- [ ] DEFAULT_FROM_EMAIL: sync: false
- [ ] Dominios removidos de yaml
- [ ] Comentarios claros sobre cómo configurar

**Test:**
```bash
grep -A 1 "DEFAULT_FROM_EMAIL" render.yaml | grep "sync: false"
# Resultado esperado: encontrado
```

---

### 19. CSP_DEV_HOSTS (nuevo campo)
- [ ] En `settings.py`: existe `CSP_DEV_HOSTS` con default controlado
- [ ] En `security_headers.py`: usa settings en lugar de hardcodeos
- [ ] En produccion: se puede configurar via env

**Test:**
```bash
rg -n "CSP_DEV_HOSTS" apps/backend/app/config/settings.py apps/backend/app/middleware/security_headers.py
# Resultado esperado: encontrado en ambos
```

---

### 20. Currency table (sin constants redundantes)
- [ ] Currency se maneja via tabla DB (modelo `Currency`)
- [ ] No existen `constants/currencies.py` ni `constants/statuses.py`

**Test:**
```bash
rg -n "Currency" apps/backend/app/models/company/company.py
rg -n "constants/(currencies|statuses)" apps/backend/app
# Resultado esperado: Currency existe en modelos; sin imports a constants eliminadas
```

---

## 🟢 BAJO RIESGO (15+ - Referencia)

- [ ] Datos de demostración documentados
- [ ] Puertos por defecto en README
- [ ] URLs en documentación claramente marcadas como ejemplos
- [ ] SVG namespaces aceptables
- [ ] APIs externas estándar

---

## 🔧 Tests de Integración

### Backend Startup
```bash
cd apps/backend
ENVIRONMENT=production python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Esperado: Sin errores de configuración, solo de env vars faltantes
```

### Systemd Service
```bash
# En servidor:
systemctl start gestiq-worker-imports
journalctl -u gestiq-worker-imports -n 50
# Esperado: Sin errores sobre variables hardcodeadas
```

### Frontend Build
```bash
cd apps/tenant
VITE_API_URL=https://api.example.com npm run build
# Esperado: Build exitoso
```

---

## 📋 Checklist Pre-Deploy

### En Desarrollo (Local)
- [ ] `python -m pytest` pasa todos los tests
- [ ] Backend arranca sin warnings de hardcodeos
- [ ] Frontend se compila sin warnings

### En Staging
- [ ] Configurar `/etc/gestiq/worker-imports.env` si usa systemd
- [ ] Configurar variables en Render Dashboard
- [ ] Validar que ningún error de hardcodeo aparece en logs

### En Producción
- [ ] Todos los valores críticos están en variables de entorno
- [ ] Ningún "localhost" en DATABASE_URL, REDIS_URL, CORS_ORIGINS
- [ ] Dominios configurados vía Render Dashboard
- [ ] Email configurado en Render Dashboard
- [ ] Permisos correctos en `/etc/gestiq/*.env` (600)

---

## 🚨 Problemas Comunes

### Error: "DATABASE_URL not configured"
- **Causa:** DATABASE_URL o DB_DSN no están seteados
- **Fix:** Agregar a .env o variables de entorno
- **Validar:** `echo $DATABASE_URL`

### Error: "REDIS_URL points to localhost in production"
- **Causa:** REDIS_URL=redis://localhost:6379/0
- **Fix:** Usar URL de Redis remoto
- **Validar:** `echo $REDIS_URL | grep -v localhost`

### Error: "CORS_ORIGINS not configured"
- **Causa:** Falta variable CORS_ORIGINS
- **Fix:** Agregar en Render Dashboard
- **Validar:** `echo $CORS_ORIGINS`

### Dominio incorrecto en frontend
- **Causa:** VITE_TENANT_ORIGIN no seteado
- **Fix:** Configurar en Render Dashboard
- **Validar:** Revisar variable en Settings

---

## ✅ Sign-off

- [ ] Todos los críticos validados
- [ ] Todos los moderados validados
- [ ] Tests de integración pasados
- [ ] Documentación actualizada
- [ ] Listo para merge a main

---

**Creado por:** Amp (Sesión Fase 5)
**Fecha:** 15 Enero 2026
**Versión:** 1.0 - Final
