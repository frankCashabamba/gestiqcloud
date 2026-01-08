# Análisis de Hardcodeos en Gestiqcloud

## 🔴 Críticos (Deben ser corregidos)

### 1. **Dominios y Origins hardcodeados en Cloudflare Worker**
- **Archivo**: `workers/edge-gateway.js` (líneas 177-181)
- **Problema**: Origins de production están hardcodeados como defaults
```javascript
const defaults = [
  'https://gestiqcloud.com',
  'https://www.gestiqcloud.com',
  'https://admin.gestiqcloud.com',
];
```
- **Impacto**: Si estos dominios cambian, hay que modificar el código
- **Solución**: Usar solo `ALLOWED_ORIGINS` de wrangler.toml

### 2. **Email default hardcodeado**
- **Archivo**: `apps/backend/app/config/settings.py` (línea 289)
- **Problema**: `DEFAULT_FROM_EMAIL: str = "no-reply@localhost"`
- **Impacto**: Emails en producción saldrían de localhost
- **Solución**: Configurar vía ENV variable

### 3. **Contraseña de certificado para e-invoicing**
- **Archivo**: `apps/backend/app/workers/einvoicing_tasks.py` (líneas 473, 609)
- **Problema**: 
```python
"password": "CERT_PASSWORD",  # TODO: Recuperar de credenciales seguras
```
- **Impacto**: Placeholder sin implementar - e-invoicing no funcionará
- **Solución**: Implementar recuperación desde vault/secrets manager

### 4. **ElectricSQL WebSocket URL hardcodeado**
- **Archivo**: `apps/tenant/src/lib/electric.ts` (línea 10)
- **Problema**: `const ELECTRIC_URL = (import.meta as any).env?.VITE_ELECTRIC_URL || 'ws://localhost:5133'`
- **Impacto**: Si ElectricSQL no está en localhost:5133, fallará silenciosamente
- **Solución**: Pasar por env var o config

---

## 🟡 Moderados (Revisar)

### 5. **CORS Origins de desarrollo en settings.py**
- **Archivo**: `apps/backend/app/config/settings.py` (línea 231)
```python
CORS_ORIGINS: str | list[str] = Field(
    default=["http://localhost:5173", "http://localhost:5174", "http://localhost:8081", "http://localhost:8082"],
)
```
- **Impacto**: En producción, estos valores por defecto permitirían localhost (seguridad)
- **Solución**: Validar que se configuren vía env en producción

### 6. **API Target hardcodeado en vite configs**
- **Archivos**: 
  - `apps/tenant/vite.config.ts` (línea 11): `'http://localhost:8000'`
  - `apps/admin/vite.config.js` (línea 47): similar
- **Impacto**: Fallback incorrecto si env var no se configura
- **Solución**: Estos están bien (tienen fallbacks) pero validar configuración

### 7. **Credenciales de prueba en repositorio**
- **Archivos**: `apps/backend/app/tests/*.py`
- **Problema**: Usuarios hardcodeados: `password="secret"`, `password="tenant123"`
- **Impacto**: Bajo (son tests), pero es mala práctica
- **Solución**: Usar fixtures con valores aleatorios o que vengan de env

### 8. **Host/port de backend para desarrollo**
- **Archivos múltiples**:
  - `scripts/start_local.ps1`: `http://localhost:8000/api` (línea 69)
  - `docs/backend.md`: múltiples referencias a `http://localhost:8000`
  - `README.md`: valores por defecto
- **Impacto**: Bajo (solo documentación), pero documentan values por defecto
- **Solución**: Documentar que estos son valores por defecto, no requeridos

### 9. **Redis URLs en scripts de deployment**
- **Archivo**: `ops/systemd/gestiq-worker-imports.service` (líneas 12-13)
- **Problema**: 
```
Environment="DB_DSN=postgresql://gestiq:PASSWORD@localhost:5432/gestiqcloud"
Environment="REDIS_URL=redis://localhost:6379/0"
```
- **Impacto**: Necesita actualización manual para cada deployment
- **Solución**: Usar template variables o usar system env vars

### 10. **DB connection hardcoded en migration scripts**
- **Archivos**: `ops/scripts/migrate_all_migrations.py` (línea 124)
```python
host=parsed.hostname or "localhost"
```
- **Impacto**: Fallback a localhost si hostname no se parsea
- **Solución**: Validar que DATABASE_URL siempre esté correcto

---

## 🟢 Bajo Riesgo (Aceptables)

### 11. **Datos de prueba (empresas slug)**
- **Archivos**: 
  - `apps/admin/admin-panel-full.html`
  - README files con ejemplos usando `kusi-panaderia`, `bazar-omar`, `taller-lopez`
- **Impacto**: Bajo, son datos de demostración
- **Solución**: Documentar claramente que son ejemplos

### 12. **Puertos por defecto en vite**
- **Archivos**: `apps/tenant/vite.config.ts` (línea 52), `apps/admin/vite.config.ts`
- **Problema**: `port: Number(process.env.PORT || 8082)`
- **Impacto**: Bajo (config de desarrollo local)
- **Solución**: Aceptable como fallback

### 13. **Configuración de payments base_url**
- **Archivo**: `apps/backend/app/routers/payments.py` (líneas 160-162)
```python
base_url = str(request.base_url).rstrip("/") if request else ""
success_url = data.success_url or f"{base_url}/payments/success?..."
```
- **Impacto**: Dinámico, usa request.base_url
- **Solución**: Aceptable

### 14. **Interpolación de URLs en componentes**
- **Archivo**: `apps/tenant/src/modules/importador/components/ProcessingIndicator.tsx` (línea 14)
```typescript
return match ? match[1] : 'kusi-panaderia'
```
- **Impacto**: Fallback a tenant slug por defecto
- **Solución**: Aceptable si hay lógica de extracción primaria

---

## 📋 Resumen de Acciones

| Severidad | Cantidad | Acción |
|-----------|----------|--------|
| 🔴 Crítico | 4 | Resolver inmediatamente |
| 🟡 Moderado | 6 | Revisar y validar en producción |
| 🟢 Bajo | 4 | Documentar claramente |

---

## ✅ Recomendaciones Generales

1. **Crear archivo `.env.example`** en cada app mostrando todas las variables obligatorias
2. **Validar en startup** que todas las vars críticas estén configuradas
3. **Usar un servicio de secrets** (AWS Secrets Manager, Vault, etc) para CERT_PASSWORD
4. **Remover valores por defecto de localhost** en settings de producción
5. **Implementar health checks** que validen que URLs están correctas
6. **Documentar claramente** qué es hardcoded, qué tiene fallback, qué es obligatorio
