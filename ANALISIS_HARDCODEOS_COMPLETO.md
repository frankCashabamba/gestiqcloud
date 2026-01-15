# Análisis Completo de Hardcodeos - Gestiqcloud (100%)

**Fecha del análisis:** 15 de Enero de 2026  
**Cobertura:** Frontend (apps/tenant, apps/admin) + Backend (apps/backend) + Workers + Scripts

---

## 📊 Resumen Ejecutivo

| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| 🔴 **CRÍTICO** | 8 | Impacto directo en producción |
| 🟡 **MODERADO** | 12 | Requiere validación/config |
| 🟢 **BAJO** | 15+ | Documentación/ejemplos |

**Total de hardcodeos identificados:** 35+

---

## 🔴 CRÍTICOS (Corregir Inmediatamente)

### 1. **Dominios Production en Cloudflare Worker**
- **Archivos:** `workers/wrangler.toml` (línea 16-17), `workers/edge-gateway.js` (línea 177-181)
- **Problema:** Origins de producción están hardcodeados como fallback
```
TARGET = "https://gestiqcloud-api.onrender.com"
ALLOWED_ORIGINS = "https://admin.gestiqcloud.com,https://www.gestiqcloud.com"
```
- **Impacto:** Si dominios cambian, requiere modificación de código. Fallback inseguro en local.
- **Riesgo:** Seguridad (CORS), Flexibilidad
- **Solución:** Usar SOLO variables de `wrangler.toml`/environment

### 2. **Email Default (no-reply@localhost)**
- **Archivo:** `apps/backend/app/config/settings.py` (línea 289)
- **Problema:** 
```python
DEFAULT_FROM_EMAIL: str = "no-reply@localhost"
```
- **Impacto:** Todos los emails en producción saldrían de `no-reply@localhost` si no se configura
- **Riesgo:** Crítico - Los emails no serían entregables
- **Solución:** Requerir variable `DEFAULT_FROM_EMAIL` en env (ej: `no-reply@gestiqcloud.com`)

### 3. **Contraseña de Certificado E-Invoicing**
- **Archivo:** `apps/backend/app/workers/einvoicing_tasks.py` (líneas 473, 609)
- **Problema:**
```python
"password": "CERT_PASSWORD",  # TODO: Recuperar de credenciales seguras
```
- **Impacto:** E-invoicing no funcionará. Placeholder sin implementación
- **Riesgo:** Crítico - Feature incompleto
- **Solución:** 
  - Implementar integración con AWS Secrets Manager o HashiCorp Vault
  - Crear variable env: `CERT_PASSWORD`
  - Validar en startup que CERT_PASSWORD está configurado

### 4. **ElectricSQL WebSocket URL Fallback**
- **Archivo:** `apps/tenant/src/lib/electric.ts` (línea 10)
- **Problema:**
```typescript
const ELECTRIC_URL = (import.meta as any).env?.VITE_ELECTRIC_URL || 'ws://localhost:5133'
```
- **Impacto:** Fallback silencioso a localhost. En producción, sin ElectricSQL fallará sin error claro
- **Riesgo:** Crítico - La app fallará silenciosamente sin saber por qué
- **Solución:** 
  - Hacer obligatorio `VITE_ELECTRIC_URL`
  - Validar en startup que ElectricSQL está accesible
  - Lanzar error claro si no está disponible

### 5. **Redis URL Fallback (Backend)**
- **Archivo:** `apps/backend/celery_app.py` (línea 12)
- **Problema:**
```python
url = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
```
- **Impacto:** Fallback a localhost puede silenciosamente usar Redis local en staging
- **Riesgo:** Crítico - Posible pérdida de datos, comportamiento inesperado
- **Solución:** Hacer obligatorio `REDIS_URL`, fallar explícitamente si no está configurado

### 6. **CORS Origins Localhost (Backend)**
- **Archivo:** `apps/backend/app/config/settings.py` (línea 231)
- **Problema:**
```python
CORS_ORIGINS: str | list[str] = Field(
    default=["http://localhost:5173", "http://localhost:5174", "http://localhost:8081", "http://localhost:8082"],
)
```
- **Impacto:** En producción, si no se configura CORS_ORIGINS via env, permitirá localhost
- **Riesgo:** Seguridad - Brechas potenciales CORS
- **Solución:** 
  - Usar defaults vacíos para producción
  - Requerir variable env: `CORS_ORIGINS` (lista explícita)
  - Validar que localhost nunca esté en producción

### 7. **Admin Password en Test HTML**
- **Archivo:** `apps/admin/test-login.html` (línea 38)
- **Problema:**
```html
const adminPassword = 'Admin.2025';
```
- **Impacto:** Credencial de prueba hardcodeada (aunque en test)
- **Riesgo:** Moderado - Si se accede a test-login.html en prod, expone credenciales
- **Solución:** Eliminar archivo test-login.html de producción o usar env vars

### 8. **API Base URL en Test HTML**
- **Archivo:** `apps/admin/test-login.html` (línea 12)
- **Problema:**
```javascript
const API_BASE = 'https://api.gestiqcloud.com';
```
- **Impacto:** URL hardcodeada en archivo de prueba
- **Riesgo:** Moderado-Crítico si archivo se vuelve accesible en producción
- **Solución:** Remover archivo test-login.html de deployments de producción

---

## 🟡 MODERADOS (Revisar y Validar)

### 9. **API URL Fallbacks en Frontend**
- **Archivos:** 
  - `apps/tenant/vite.config.ts` (línea 11): `'http://localhost:8000'`
  - `apps/admin/src/services/incidents.ts` (línea 8): `'http://localhost:8000/api'`
  - `apps/admin/src/services/logs.ts` (línea 8): `'http://localhost:8000/api'`
- **Problema:** Fallback a localhost si VITE_API_URL no está configurado
- **Impacto:** Requests pueden ir a localhost en staging/prod si env no está bien configurado
- **Solución:** Validar que VITE_API_URL está siempre presente en .env antes de build

### 10. **Storage Keys Hardcodeados**
- **Archivos:**
  - `apps/tenant/src/shared/api/client.ts` (línea 11): `tokenKey: 'access_token_tenant'`
  - `apps/tenant/src/modules/pos/POSView.tsx`: `'posDraftState'`
  - Múltiples referencias a keys localStorage
- **Problema:** Storage keys distribuidos sin centralización
- **Impacto:** Cambios requieren actualizar múltiples archivos
- **Solución:** Centralizar en constantes (ej: `src/constants/storage.ts`)

### 11. **Rutas de API Hardcodeadas**
- **Archivos:** `apps/tenant/src/modules/pos/services.ts` (línea 20-22)
- **Problema:**
```typescript
const API_PATHS = {
  pos: '/api/v1/tenant/pos',
  // ... más paths
}
```
- **Impacto:** Versión de API (v1) está hardcodeada
- **Solución:** Usar variable env para versión de API

### 12. **Slugs de Empresas en Fallbacks**
- **Archivo:** `apps/tenant/src/modules/importador/components/ProcessingIndicator.tsx` (línea 14)
- **Problema:**
```typescript
return match ? match[1] : 'kusi-panaderia'
```
- **Impacto:** Fallback a empresa de prueba específica
- **Solución:** Remover fallback hardcodeado o hacerlo configurable

### 13. **Plantillas de Dashboard Hardcodeadas**
- **Archivos:** `apps/tenant/src/plantillas/` (múltiples)
  - `panaderia_pro.tsx`, `taller_pro.tsx`, `default.tsx`
- **Problema:** Plantillas hardcodeadas para tipos específicos de empresas
- **Impacto:** Inflexible, difícil de mantener
- **Solución:** Mover plantillas a base de datos o config

### 14. **Credenciales de Test en Backend**
- **Archivos:** `apps/backend/app/tests/test_*.py`
- **Problema:**
```python
password="secret"
password="Admin.2025"
```
- **Impacto:** Bajo (tests), pero expone patrones
- **Solución:** Usar fixtures aleatorias o factories

### 15. **Configuración de Render.yaml Hardcodeada**
- **Archivo:** `render.yaml` (línea 38-47, 155-157, 195-197)
- **Problema:** Múltiples dominios de producción hardcodeados
```yaml
value: https://www.gestiqcloud.com
value: https://api.gestiqcloud.com
value: https://admin.gestiqcloud.com
```
- **Impacto:** Cambios de dominio requieren actualizar archivo
- **Solución:** Usar variables de Render environment

### 16. **Redis URL en Systemd Service**
- **Archivo:** `ops/systemd/gestiq-worker-imports.service` (línea 13)
- **Problema:**
```
Environment="REDIS_URL=redis://localhost:6379/0"
```
- **Impacto:** Configuración fija, requiere actualización manual
- **Solución:** Usar systemd env files o variables globales

### 17. **Database Host Fallback**
- **Archivo:** `ops/scripts/migrate_all_migrations.py` (línea 124)
- **Problema:**
```python
host=parsed.hostname or "localhost"
```
- **Impacto:** Fallback a localhost si parsing falla
- **Solución:** Validar DATABASE_URL y fallar explícitamente

### 18. **Telegram Bot API URL**
- **Archivo:** `apps/backend/app/workers/notifications.py` (línea 240)
- **Problema:**
```python
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
```
- **Impacto:** URL de API externa hardcodeada (pero es estándar)
- **Solución:** Aceptable como está

### 19. **Email de Test Hardcodeada**
- **Archivo:** `apps/backend/app/config/settings.py` (línea 290)
- **Problema:** Email de desarrollo puede estar hardcodeado
- **Solución:** Usar env var

### 20. **Vite Proxy Configuration**
- **Archivo:** `apps/tenant/vite.config.js` (línea 45)
- **Problema:**
```javascript
target: process.env.VITE_API_URL || 'http://localhost:8000'
```
- **Impacto:** Fallback a localhost para proxy de desarrollo
- **Solución:** Aceptable para desarrollo local

---

## 🟢 BAJO RIESGO (Aceptables)

### 21. **Datos de Demostración**
- **Empresas:** `kusi-panaderia`, `bazar-omar`, `taller-lopez`
- **Uso:** README, documentación, ejemplos
- **Riesgo:** Bajo - son ejemplos claramente documentados
- **Solución:** Mantener pero documentar que son ejemplos

### 22. **Puertos por Defecto**
- **Desarrollo:** Puerto 8000 (API), 8081 (Admin), 8082 (Tenant), 5133 (ElectricSQL)
- **Riesgo:** Bajo - standard para desarrollo local
- **Solución:** Documentar en README.md

### 23. **URLs en Documentación**
- Múltiples referencias a `http://localhost:8000` en docs
- **Riesgo:** Bajo - claras como ejemplos
- **Solución:** Mantener para consistencia

### 24. **SVG XML Namespaces**
- `xmlns="http://www.w3.org/2000/svg"` (múltiples archivos)
- **Riesgo:** Bajo - son namespaces estándar
- **Solución:** Ignorar

### 25. **Render API URLs**
- Referencia a `https://api.render.com/v1/jobs/...`
- **Riesgo:** Bajo - es API externa estándar
- **Solución:** Aceptable

---

## 🏗️ Hardcodeos por Módulo

### **Backend (apps/backend)**

| Módulo | Hardcodeos | Severidad |
|--------|-----------|-----------|
| Config/Settings | CORS defaults, DEFAULT_FROM_EMAIL | 🔴🟡 |
| E-invoicing | CERT_PASSWORD placeholder | 🔴 |
| Celery | Redis localhost fallback | 🔴 |
| Workers | Notification URLs | 🟢 |
| Tests | Credenciales test | 🟡 |

### **Tenant Frontend (apps/tenant)**

| Módulo | Hardcodeos | Severidad |
|--------|-----------|-----------|
| Config | API URL fallback | 🟡 |
| Electric | WebSocket URL fallback | 🔴 |
| Services | Storage keys distribuidos | 🟡 |
| POS | Draft state key hardcodeado | 🟡 |
| Importador | Empresa slug fallback | 🟡 |
| Plantillas | Datos de empresas específicas | 🟡 |

### **Admin Frontend (apps/admin)**

| Módulo | Hardcodeos | Severidad |
|--------|-----------|-----------|
| Config | API URL fallback | 🟡 |
| Test HTML | Admin password + API URL | 🔴 |
| Services | Storage keys | 🟡 |

### **Workers (Cloudflare)**

| Elemento | Hardcodeos | Severidad |
|----------|-----------|-----------|
| wrangler.toml | Dominios production | 🔴 |
| edge-gateway.js | Origins hardcodeados | 🔴 |

### **Ops & Scripts**

| Elemento | Hardcodeos | Severidad |
|----------|-----------|-----------|
| Systemd service | Redis localhost | 🟡 |
| render.yaml | Dominios production | 🟡 |
| Migration scripts | DB host fallback | 🟡 |

---

## ✅ Plan de Acción (Priorizado)

### **Fase 1: Críticos (1-2 semanas)**

- [ ] **Email Default**: Actualizar `DEFAULT_FROM_EMAIL` a usar env var
  ```python
  DEFAULT_FROM_EMAIL: str = Field(default="", description="Requerido en producción")
  ```
  
- [ ] **E-invoicing CERT_PASSWORD**: Implementar Secrets Manager
  ```python
  cert_password = get_secret("cert_password")
  ```
  
- [ ] **Redis URL**: Remover fallback a localhost
  ```python
  url = os.getenv("REDIS_URL")
  if not url:
      raise ValueError("REDIS_URL es requerido")
  ```
  
- [ ] **CORS Origins**: Cambiar default a vacío
  ```python
  CORS_ORIGINS: list[str] = Field(
      default=[],  # En producción debe venir de env
  )
  ```
  
- [ ] **ElectricSQL URL**: Hacer obligatorio
  ```typescript
  const ELECTRIC_URL = import.meta.env.VITE_ELECTRIC_URL
  if (!ELECTRIC_URL) {
      throw new Error("VITE_ELECTRIC_URL no configurado")
  }
  ```
  
- [ ] **Remover test-login.html**: Eliminar del repo o de deployments

### **Fase 2: Moderados (2-3 semanas)**

- [ ] **API URL Fallbacks**: Validar configuración en startup
- [ ] **Storage Keys**: Centralizar en `constants/storage.ts`
- [ ] **Rutas de API**: Mover a configuración
- [ ] **Credenciales Test**: Usar factories aleatorias
- [ ] **Dominios Cloudflare**: Usar SOLO variables de env

### **Fase 3: Bajo Riesgo (Documentación)**

- [ ] **Documentar defaults** en README.md
- [ ] **Ejemplos claros** con variables de ejemplo
- [ ] **Validación de startup** para todas las vars críticas

---

## 🔧 Checklist de Validación

### Antes de hacer merge a main:

- [ ] No hay hardcodeos de dominios en código (solo en configs)
- [ ] Todas las variables críticas están documentadas en `.env.example`
- [ ] El servidor falla al iniciar si variables críticas faltan
- [ ] CORS_ORIGINS está vacío en settings.py (se carga de env)
- [ ] RedisURL no tiene fallback a localhost
- [ ] ElectricSQL URL es obligatorio
- [ ] Email default no es localhost
- [ ] CERT_PASSWORD viene de Secrets Manager
- [ ] test-login.html no está en producción

### Antes de deploy a producción:

- [ ] Todas las env vars críticas están configuradas en Render
- [ ] Dominios en render.yaml coinciden con VITE_API_URL en frontends
- [ ] CORS_ORIGINS incluye todos los dominios esperados (sin localhost)
- [ ] Health checks validan que servicios externos están disponibles
- [ ] Logs indican si algo está usando fallback a localhost
- [ ] Secrets están en AWS Secrets Manager/Vault (no en código)

---

## 📝 Notas Técnicas

### Variables de Entorno Críticas Requeridas:

```bash
# Backend
DEFAULT_FROM_EMAIL=no-reply@gestiqcloud.com
REDIS_URL=redis://cache.internal:6379/1
CERT_PASSWORD=[de Secrets Manager]
CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com

# Frontend Tenant
VITE_API_URL=https://api.gestiqcloud.com/api/v1
VITE_ELECTRIC_URL=ws://electric.internal:3000

# Frontend Admin
VITE_API_URL=https://api.gestiqcloud.com/api/v1

# Workers (Cloudflare)
TARGET=https://gestiqcloud-api.onrender.com
ALLOWED_ORIGINS=https://admin.gestiqcloud.com,https://www.gestiqcloud.com
```

### Patrón Recomendado para Settings:

```python
# ✅ BIEN (con validación)
SECRET_SETTING: str = Field(
    description="Campo obligatorio en producción"
)

# ✅ BIEN (con default seguro)
DEBUG: bool = Field(default=False)  # Never True in prod

# ❌ MALO (fallback silencioso)
API_URL: str = Field(default="http://localhost:8000")
```

---

## 🎯 Conclusiones

1. **Riesgo general MEDIO-ALTO**: Varios hardcodeos pueden afectar producción silenciosamente
2. **Punto crítico**: Fallbacks a localhost en múltiples lugares
3. **Seguridad**: CORS defaults pueden exponer a ataques
4. **Flexibilidad**: Dominios hardcodeados dificultan multi-tenant/multi-región
5. **Recomendación**: Implementar validación de startup obligatoria

---

**Elaborado por:** Análisis automático  
**Próxima revisión:** Después de implementar Fase 1
