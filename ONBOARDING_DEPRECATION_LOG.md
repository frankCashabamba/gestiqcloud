# Onboarding Refactoring - Deprecation Log

Fecha: 2026-01-10

## Cambios Realizados

### ✅ Nuevos Archivos

1. **apps/tenant/src/pages/Onboarding.tsx** (ACTIVO)
   - Wizard de 4 pasos: Información → Regional → Branding → Resumen
   - Guarda en `Tenant` y `CompanySettings` con tenant_id
   - Redirecciona a `/set-password?token=token` después de guardar

2. **apps/backend/app/routers/onboarding_init.py** (ACTIVO)
   - Endpoint: `POST /api/v1/tenant/onboarding/init`
   - Guarda información de empresa (Tenant) y configuración (CompanySettings)
   - Usa RLS (Row Level Security) con `tenant_id` del token
   - Validación completa de datos

### 📌 Archivos Deprecados

1. **apps/packages/domain/src/onboarding.ts** (DEPRECADO)
   - ❌ Función `createOnboardingService` no se usaba
   - ✅ Comentada para referencia futura
   - 🗑️ Eliminar en próxima versión

2. **apps/tenant/src/pages/OnboardingWizard.tsx** (DEPRECADO)
   - ❌ Redundante con Onboarding.tsx
   - ✅ Comentado para referencia
   - 🗑️ Eliminar en próxima versión

3. **apps/backend/app/routers/initial_config.py** (DEPRECADO)
   - ❌ Endpoint antiguo `/api/v1/company-settings`
   - ✅ Mantenido temporalmente para compatibilidad
   - 🗑️ Eliminar en próxima versión

### 🔄 Actualizaciones

1. **apps/packages/endpoints/src/tenant.ts**
   - Endpoint actualizado:
     - Antes: `/api/v1/tenant/configuracion-inicial`
     - Después: `/api/v1/tenant/onboarding/init`

2. **apps/backend/app/main.py**
   - Agregado registro del nuevo router `onboarding_init_router`
   - Mantiene compatibilidad temporal con `initial_config` router

## Flujo Actual (Post-Refactoring)

```
Usuario registrado
     ↓
Email con enlace: /onboarding?token=xxx
     ↓
Onboarding.tsx (4 pasos)
     ↓
POST /api/v1/tenant/onboarding/init
     ↓
Backend: Guarda en Tenant + CompanySettings (con tenant_id)
     ↓
Redirecciona a /set-password?token=xxx
     ↓
Dashboard con login completado
```

## Limpieza Pendiente

- [ ] Eliminar `apps/packages/domain/src/onboarding.ts` (v2.0)
- [ ] Eliminar `apps/tenant/src/pages/OnboardingWizard.tsx` (v2.0)
- [ ] Eliminar `apps/backend/app/routers/initial_config.py` (v2.0)
- [ ] Actualizar imports si existen referencias a archivos deprecados

## Referencias de Código

- Onboarding wizard principal: [Onboarding.tsx](apps/tenant/src/pages/Onboarding.tsx)
- Backend endpoint: [onboarding_init.py](apps/backend/app/routers/onboarding_init.py)
- Endpoints definition: [endpoints/tenant.ts](apps/packages/endpoints/src/tenant.ts)
- Router registration: [main.py](apps/backend/app/main.py)
