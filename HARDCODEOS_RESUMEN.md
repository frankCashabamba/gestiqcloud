# Resumen Ejecutivo: Hardcodeos en Gestiqcloud

## Estado actual (final)

- Estado: COMPLETADO (sin pendientes abiertos)
- Referencia principal: `HARDCODEOS_FIXES.md`
- Nota: Las acciones y checklist de este archivo son historicas y ya fueron ejecutadas.

## Nuevos campos y tablas (incluidos en fixes)

- Campo `CSP_DEV_HOSTS` agregado en `apps/backend/app/config/settings.py`; `security_headers.py` lo usa.
- Tabla `Currency` ya existe en DB; se eliminaron `constants/currencies.py` y `constants/statuses.py` redundantes.

## 📊 Estadísticas Rápidas

```
Total de hardcodeos: 35+
├─ 🔴 CRÍTICOS (8)
├─ 🟡 MODERADOS (12)
└─ 🟢 BAJO RIESGO (15+)

Afectados:
├─ Backend: 8 hardcodeos (críticos)
├─ Tenant Frontend: 8 hardcodeos
├─ Admin Frontend: 4 hardcodeos
└─ Workers: 4 hardcodeos
```

---

## 🔴 Los 8 Problemas Críticos Que DEBEN Arreglarse

| # | Problema | Ubicación | Por Qué Es Crítico | Arreglo |
|---|----------|-----------|-------------------|---------|
| 1 | `DEFAULT_FROM_EMAIL = "no-reply@localhost"` | `settings.py:289` | Emails inentregables en producción | Usar env var |
| 2 | `REDIS_URL \|\| "redis://localhost:6379/0"` | `celery_app.py:12` | Fallback silencioso a localhost | Fallar si no está configurado |
| 3 | `CERT_PASSWORD = "CERT_PASSWORD"` | `einvoicing_tasks.py` | Feature incompleto, no funciona | Integrado via secrets (env/AWS) |
| 4 | `VITE_ELECTRIC_URL \|\| 'ws://localhost:5133'` | `electric.ts:10` | Falla silenciosa en producción | Hacer obligatorio |
| 5 | `CORS_ORIGINS default = [localhost]` | `settings.py:231` | Seguridad comprometida | Default vacío en prod |
| 6 | `TARGET = "gestiqcloud-api.onrender.com"` | `wrangler.toml:16` | Hardcodeado, inflexible | Usar solo env vars |
| 7 | `ALLOWED_ORIGINS = "admin.gestiqcloud.com"` | `wrangler.toml:17` | Hardcodeado, inflexible | Usar solo env vars |
| 8 | `API_BASE = 'https://api.gestiqcloud.com'` | `test-login.html:12` | Test file expone credenciales | Eliminar del repo |

---

## 🎯 Acciones Inmediatas (Esta Semana)

### 1️⃣ Email Default
```python
# ❌ ACTUAL
DEFAULT_FROM_EMAIL: str = "no-reply@localhost"

# ✅ CORREGIDO
DEFAULT_FROM_EMAIL: str = Field(
    description="Requerido en producción (ej: no-reply@gestiqcloud.com)"
)
```
**Impacto:** 🔴 CRÍTICO - Todos los emails fallarán

---

### 2️⃣ Redis URL
```python
# ❌ ACTUAL
url = os.getenv("REDIS_URL") or "redis://localhost:6379/0"

# ✅ CORREGIDO
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise ValueError("REDIS_URL debe estar configurado")
```
**Impacto:** 🔴 CRÍTICO - Posible corrupción de datos en staging

---

### 3️⃣ CORS Origins
```python
# ❌ ACTUAL (permite localhost en prod!)
CORS_ORIGINS: list[str] = Field(
    default=["http://localhost:5173", "http://localhost:8081", ...]
)

# ✅ CORREGIDO
CORS_ORIGINS: list[str] = Field(
    default=[],  # Vacío - debe venir de env
    description="Dominios permitidos (CSRF protection)"
)
```
**Impacto:** 🔴 CRÍTICO - Brechas de seguridad

---

### 4️⃣ ElectricSQL URL
```typescript
// ❌ ACTUAL (fallback silencioso)
const ELECTRIC_URL = import.meta.env.VITE_ELECTRIC_URL || 'ws://localhost:5133'

// ✅ CORREGIDO (falla explícitamente)
const ELECTRIC_URL = import.meta.env.VITE_ELECTRIC_URL
if (!ELECTRIC_URL) {
    throw new Error(
        'VITE_ELECTRIC_URL no configurado. ' +
        'Define en .env: VITE_ELECTRIC_URL=ws://electric.internal:3000'
    )
}
```
**Impacto:** 🔴 CRÍTICO - La app falla sin error claro

---

### 5️⃣ Certificado E-Invoicing
```python
# ❌ ACTUAL (placeholder)
"password": "CERT_PASSWORD",  # Antes: placeholder hardcodeado (resuelto)

# ✅ CORREGIDO
cert_password = get_secret_from_vault("cert_password")
if not cert_password:
    raise ConfigError("CERT_PASSWORD no disponible en Secrets Manager")
```
**Impacto:** 🔴 CRÍTICO - Feature no funciona

---

## 📋 Checklist Inmediato

```bash
# 1. Hacer variables OBLIGATORIAS
☐ DEFAULT_FROM_EMAIL - quitar default
☐ REDIS_URL - quitar fallback
☐ CERT_PASSWORD - implementado via secrets (env/AWS)
☐ VITE_ELECTRIC_URL - quitar fallback

# 2. Cambiar DEFAULTS seguros
☐ CORS_ORIGINS = [] (no localhost)
☐ Eliminar test-login.html

# 3. Validación al startup
☐ Agregar health checks
☐ Validar vars en app initialization
☐ Fallar explícitamente, no silenciosos

# 4. Documentación
☐ Crear .env.example con ALL required vars
☐ Actualizar README con vars críticas
☐ Documentar en render.yaml
```

---

## 📊 Impacto por Entorno

### 🏠 Development (Local)
- ✅ Fallbacks a localhost están OK
- ✅ Emails pueden ir a localhost
- ✅ CORS con localhost es OK
- 📝 PERO: Documentar claramente

### 🟡 Staging
- ⚠️ CRÍTICO: No debe haber fallbacks
- ⚠️ Emails deben ser reales (o mock)
- ⚠️ CORS debe excluir localhost
- ⚠️ Redis debe ser staging, no local

### 🔴 Production
- 🚫 NADA de localhost permitido
- 🚫 NADA de fallbacks silenciosos
- 🚫 NADA de credenciales hardcodeadas
- 🚫 Validación ESTRICTA al startup

---

## 💡 Patrón de Solución (Implementar en Todas las Variables)

```python
from pydantic import Field
import os

class Settings(BaseSettings):
    # ❌ NO HACER ESTO
    # api_url: str = "http://localhost:8000"

    # ✅ HACER ESTO
    api_url: str = Field(
        description="API endpoint (ej: https://api.gestiqcloud.com)",
        # Sin default = OBLIGATORIO en producción
    )

    @field_validator('api_url')
    @classmethod
    def validate_api_url(cls, v):
        if 'localhost' in v and os.getenv('ENVIRONMENT') == 'production':
            raise ValueError('API URL no puede ser localhost en producción')
        return v
```

---

## 🔍 Archivos Críticos a Revisar

**Prioridad 1 (Hoy):**
- `apps/backend/app/config/settings.py` - DEFAULT_FROM_EMAIL, CORS_ORIGINS
- `apps/backend/celery_app.py` - REDIS_URL fallback
- `apps/tenant/src/lib/electric.ts` - ELECTRIC_URL fallback
- `apps/admin/test-login.html` - Eliminar archivo

**Prioridad 2 (Esta Semana):**
- `apps/backend/app/workers/einvoicing_tasks.py` - CERT_PASSWORD
- `workers/wrangler.toml` - Dominios hardcodeados
- `render.yaml` - Dominios hardcodeados
- `apps/tenant/vite.config.ts` - API URL fallback

---

## 🚨 Qué Pasa Si No Se Arregla

| Escenario | Impacto | Severidad |
|-----------|---------|-----------|
| Prod sin DEFAULT_FROM_EMAIL | Todos los emails rebotarán | 🔴 |
| Prod sin REDIS_URL env | Usará localhost, perderá datos | 🔴 |
| Prod con CORS defaults | CSRF/XSS attacks posibles | 🔴 |
| Prod sin VITE_ELECTRIC_URL | App falla en algún punto | 🔴 |
| E-invoicing con placeholder | Feature completamente roto | 🔴 |

---

## 📈 Próximos Pasos

1. **Esta semana:** Implementar los 8 fixes críticos
2. **Próxima semana:** Validación y tests
3. **Luego:** Implementar validador de startup
4. **Después:** Revisar otros hardcodeos moderados

---

## 📚 Documentación Generada

- `ANALISIS_HARDCODEOS_COMPLETO.md` - Análisis detallado (35+ hardcodeos)
- `scripts/validate_env_vars.py` - Script de validación automática
- `HARDCODEOS_RESUMEN.md` - Este archivo

**Usar:** `python scripts/validate_env_vars.py --env production --strict`

---

**Último análisis:** 15 de Enero de 2026
**Estado:** COMPLETADO (sin pendientes)
