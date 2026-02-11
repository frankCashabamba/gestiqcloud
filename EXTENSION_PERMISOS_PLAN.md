# Plan Extensión Sistema de Permisos - GestiqCloud

## Estado Actual (NO TOCAR)

### Backend
- ✅ **access_guard.py**: Decodifica JWT, extrae `permisos` (dict flatten a `module:action`)
- ✅ **permissions.py**: `_has_perm(db, user, "usuarios:create")` → consulta DB
- ✅ **CompanyRole**: almacena `permissions` (JSON dict) → `{"usuarios": {"create": true, "delete": false}}`
- ✅ **get_current_user**: inyecta `access_claims` con `is_superadmin`, `is_company_admin`, `permisos`

### Frontend
- ✅ **AuthContext**: almacena `profile` (user_id, tenant_id, roles, es_admin_empresa)
- ✅ **useAuth()**: Hook para acceder a perfil + token
- ✅ **ModuleLoader.tsx**: Chequea `allowedSlugs` via `useMisModulos()`
- ✅ **RoleModal.tsx**: UI para asignar permisos granulares a roles
- ✅ **Manifests**: cada módulo define `permissions: ['pos.read', 'pos.write']`
- ✅ **Endpoints base**: `/api/v1/roles-base/global-permissions` lista permisos disponibles

## Problemas Identificados

1. **Frontend no valida permisos en rutas internas**: ModuleLoader bloquea módulo entero, pero dentro del módulo no hay protección
2. **No hay HOC/guard para rutas específicas**: ej, en Billing puede haber btn "Editar factura" sin validar permisos
3. **i18n no está conectada a permisos**: no hay mensajes de "No tienes permiso para X"
4. **Permisos no se cachean en frontend**: cada operación hace fetch a backend
5. **No hay auditoría de quién hizo qué**: logs solo en backend si existen

## Estrategia: Extensión Capa by Capa

### CAPA 1: Traer permisos a frontend (NO cambia backend)

**Objetivo**: El frontend tiene los permisos del usuario en tiempo real para validar UI.

```typescript
// apps/tenant/src/contexts/PermissionsContext.tsx (NUEVO)
type PermissionsContextType = {
  permisos: Record<string, Record<string, boolean>>  // {'usuarios': {'create': true}}
  hasPermission: (action: string, resource?: string) => boolean  // 'usuarios:create'
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}
```

**Integración sin romper AuthContext:**
- AuthContext mantiene `profile` (roles, es_admin_empresa)
- PermissionsContext lee `/api/v1/me/tenant` que YA devuelve permisos en JWT
- Parsear permisos del token en frontend (NO requiere cambio backend)

### CAPA 2: HOCs y Guards (NO cambia lógica backend)

```typescript
// apps/tenant/src/auth/ProtectedRoute.tsx (NUEVO)
<ProtectedRoute 
  requiredPermission="billing:create_invoice" 
  fallback={<Unauthorized />}
>
  <BillingForm />
</ProtectedRoute>

// apps/tenant/src/hooks/usePermission.ts (NUEVO)
const can = usePermission('billing', 'create_invoice')
if (!can) return <p>No tienes acceso</p>
```

**Integración:**
- Lee de PermissionsContext
- Respeta `is_admin_empresa` como wildcard (admin = todos permisos)
- Fallback a serverside check en API (por seguridad)

### CAPA 3: i18n para mensajes de permisos (NO cambia backend)

```typescript
// locales/es/permisos.json (NUEVO)
{
  "usuarios:create": "Crear usuarios",
  "usuarios:delete": "Eliminar usuarios",
  "billing:create_invoice": "Crear facturas",
  "billing:edit_invoice": "Editar facturas",
  "denied": "No tienes permiso para {{action}}",
  "contactAdmin": "Contacta al administrador"
}
```

**Integración:**
- Hook `usePermissionLabel(permissionKey)` → traduce
- Mensajes de error: `t('permissions.denied', {action: label})`

### CAPA 4: Caché local de permisos (NO cambia backend)

```typescript
// apps/tenant/src/lib/permissionsCache.ts (NUEVO)
- Cache en-memory con TTL 5 min
- Sincroniza con backend al iniciar sesión
- Refresca en background (no bloquea UI)
```

---

## Plan Implementación (9 tareas, sin romper nada)

### FASE 1.1: PermissionsContext + Hooks

**Tarea 1.1.1: Crear PermissionsContext**
- Archivo: `apps/tenant/src/contexts/PermissionsContext.tsx`
- Lee permisos del JWT token (ya vienen en access_claims del backend)
- Inyecta en Provider
- Integrar en AuthProvider

**Tarea 1.1.2: Crear hooks usePermission()**
- Archivo: `apps/tenant/src/hooks/usePermission.ts`
- Función: `hasPermission(action, resource?): boolean`
- Respeta admin_empresa como override

**Tarea 1.1.3: Tests unitarios**
- Archivo: `apps/tenant/src/hooks/__tests__/usePermission.test.ts`
- Mock PermissionsContext
- Casos: has perm, no perm, admin override

### FASE 1.2: HOCs y Guards

**Tarea 1.2.1: ProtectedRoute HOC**
- Archivo: `apps/tenant/src/auth/ProtectedRoute.tsx`
- Props: `requiredPermission`, `fallback`, `children`
- Lógica: `usePermission()` → renderizar o fallback

**Tarea 1.2.2: ProtectedButton Component**
- Archivo: `apps/tenant/src/components/ProtectedButton.tsx`
- Props: `permission`, `action` (para tracking)
- Inhabilitar si no tiene permisos + tooltip

**Tarea 1.2.3: Tests**
- `apps/tenant/src/auth/__tests__/ProtectedRoute.test.tsx`
- `apps/tenant/src/components/__tests__/ProtectedButton.test.tsx`

### FASE 1.3: i18n

**Tarea 1.3.1: Agregar namespaces de permisos**
- Archivos: `apps/tenant/src/locales/es/permissions.json`, `en/permissions.json`
- Estructura: `module.action: "Descripción legible"`

**Tarea 1.3.2: Hook usePermissionLabel()**
- Archivo: `apps/tenant/src/hooks/usePermissionLabel.ts`
- Toma `"usuarios:create"` → `"Crear usuarios"`

**Tarea 1.3.3: Componente PermissionDenied**
- Archivo: `apps/tenant/src/components/PermissionDenied.tsx`
- Muestra: "No tienes acceso a [permiso]. Contacta admin."

### FASE 1.4: Caché y refetch

**Tarea 1.4.1: permissionsCache.ts**
- Archivo: `apps/tenant/src/lib/permissionsCache.ts`
- Almacena permisos en sessionStorage
- TTL + invalidation en logout

**Tarea 1.4.2: Integración en PermissionsContext**
- Refetch en background cada 10 min
- Manual refetch en cambios de rol

### FASE 2: Aplicar a Módulos Críticos (sin romper)

**Tarea 2.1: Billing**
- Proteger rutas: `/billing`, `/billing/create`, `/billing/:id/edit`
- Proteger botones: "Crear factura", "Editar", "Eliminar", "Pagar"
- Tests: verifica permisos en cada acción

**Tarea 2.2: Einvoicing**
- Proteger: `/einvoicing`, `/einvoicing/send`
- Permisos: `einvoicing:read`, `einvoicing:send`, `einvoicing:download`

**Tarea 2.3: Reconciliation**
- Proteger: `/reconciliation`, `/reconciliation/match`
- Permisos: `reconciliation:read`, `reconciliation:match`

**Tarea 2.4: Usuarios/Roles**
- Ya existe UI; agregar protección en formularios
- Validar: no puedo editar un rol con más permisos que los mios

---

## Compatibilidad

### Backend: 0 cambios

```python
# access_guard.py: YA tiene
request.state.access_claims = {
  ...,
  "permisos": {"usuarios": {"create": true, "delete": false}}
}

# permissions.py: mantiene helpers _has_perm()
# DB: no cambios en schema
```

### Frontend: 100% retrocompatible

```typescript
// ModuleLoader.tsx: sigue igual
// AuthContext: sigue igual (solo add PermissionsContext)
// Componentes viejos: sin <ProtectedRoute> = sin validación (pero backend protege)
// Módulos nuevos: <ProtectedRoute> = validación + UX mejor
```

### API: 100% segura

- Frontend protege UX (no muestra botones)
- Backend protege datos (endpoint devuelve 403)
- Permisos son "source of truth" en backend

---

## Ejemplo: Antes y Después

### ANTES (hoy)
```typescript
// apps/tenant/src/modules/billing/BillingForm.tsx
export default function BillingForm() {
  const { profile } = useAuth()
  
  // Hardcoded: solo admin?
  if (!profile?.es_admin_empresa) {
    return <p>No tienes acceso</p>
  }
  
  // Crear factura sin validación granular
  const handleCreate = async () => {
    await api.post('/invoices', data)  // Backend chequea permisos; si falla → 403
  }
}
```

### DESPUÉS (con extensión)
```typescript
// apps/tenant/src/modules/billing/BillingForm.tsx
export default function BillingForm() {
  const { hasPermission } = usePermission()
  const { t } = useTranslation()
  
  if (!hasPermission('billing', 'create')) {
    return <PermissionDenied permission="billing:create" />
  }
  
  const handleCreate = async () => {
    if (!hasPermission('billing', 'create')) {
      toastError(t('permissions.denied', {action: t('permissions.billing:create')}))
      return
    }
    await api.post('/invoices', data)
  }
}

// En render:
<ProtectedButton
  permission="billing:create"
  onClick={handleCreate}
>
  {t('billing.create')}
</ProtectedButton>
```

---

## Files a Crear

```
apps/tenant/src/
├── contexts/
│   ├── PermissionsContext.tsx      # NEW
│   └── __tests__/
│       └── PermissionsContext.test.tsx  # NEW
├── hooks/
│   ├── usePermission.ts             # NEW
│   ├── usePermissionLabel.ts        # NEW
│   └── __tests__/
│       ├── usePermission.test.ts    # NEW
│       └── usePermissionLabel.test.ts  # NEW
├── auth/
│   ├── ProtectedRoute.tsx           # NEW
│   └── __tests__/
│       └── ProtectedRoute.test.tsx  # NEW
├── components/
│   ├── ProtectedButton.tsx          # NEW
│   ├── ProtectedLink.tsx            # NEW
│   ├── PermissionDenied.tsx         # NEW
│   └── __tests__/
│       ├── ProtectedButton.test.tsx # NEW
│       ├── ProtectedLink.test.tsx   # NEW
│       └── PermissionDenied.test.tsx # NEW
├── lib/
│   └── permissionsCache.ts          # NEW
├── locales/
│   ├── es/
│   │   └── permissions.json         # NEW
│   └── en/
│       └── permissions.json         # NEW
└── ... (resto sin cambios)
```

## Files a Modificar (MÍNIMOS)

```
apps/tenant/src/
├── auth/
│   └── AuthContext.tsx              # EDIT: wrap <PermissionsContext>
├── app/
│   └── App.tsx                      # EDIT: agregar <PermissionsProvider>
└── modules/
    ├── billing/
    │   ├── Routes.tsx               # EDIT: wrap rutas con <ProtectedRoute>
    │   └── BillingForm.tsx          # EDIT: agregar <ProtectedButton>
    ├── einvoicing/
    │   ├── Routes.tsx               # EDIT: similar
    │   └── ...
    └── reconciliation/
        └── ...                      # EDIT: similar
```

---

## Orden de Ejecución

1. **Crear PermissionsContext** (1.1.1)
2. **Crear hooks** (1.1.2, 1.1.3, tests)
3. **Crear HOCs** (1.2.1, 1.2.2, 1.2.3, tests)
4. **i18n** (1.3.1, 1.3.2, 1.3.3)
5. **Caché** (1.4.1, 1.4.2)
6. **Integración en AuthContext** (modificar minimal)
7. **Aplicar a Billing** (2.1, tests E2E)
8. **Aplicar a Einvoicing** (2.2)
9. **Aplicar a Reconciliation** (2.3)
10. **Aplicar a otros módulos** (2.4+)

---

## Testing Strategy

**Unitarios:**
- PermissionsContext: parsea JWT correctamente
- usePermission: chequea dict correctamente
- ProtectedRoute: renderiza o fallback según permisos

**Integración:**
- AuthProvider + PermissionsProvider: flujo login → permisos disponibles
- Billing routes: solo permite acceso si tiene `billing:read`

**E2E (Playwright):**
- Login como usuario sin permisos → bloquea módulo
- Login como admin → acceso total
- Login con permisos parciales → muestra algunos botones, oculta otros

---

## Rollout

- **Week 1**: Context + Hooks (1.1, 1.2, 1.3, 1.4)
- **Week 2**: Integración minimal AuthContext
- **Week 3**: Aplicar a Billing + Einvoicing
- **Week 4**: Tests E2E + otros módulos
