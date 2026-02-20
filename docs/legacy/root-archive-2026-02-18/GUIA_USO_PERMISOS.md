# Guía de Uso - Sistema de Permisos

## ¿Qué cambió?

Se agregó una **capa frontend de validación de permisos** que NO modifica el backend existente. Ahora tienes:

1. ✅ **PermissionsContext**: almacena permisos del usuario
2. ✅ **usePermission()**: hook para chequear permisos
3. ✅ **ProtectedRoute**: HOC para proteger rutas/componentes
4. ✅ **ProtectedButton**: botón que se deshabilita si no tiene permiso
5. ✅ **PermissionDenied**: componente para mostrar mensaje de denegación
6. ✅ **i18n**: permisos traducidos al español e inglés

## Cómo Usar

### 1. Hook usePermission()

```typescript
import { usePermission } from '@/hooks/usePermission'

export default function BillingForm() {
  const can = usePermission()

  if (!can('billing:create')) {
    return <PermissionDenied permission="billing:create" />
  }

  return <form>...</form>
}
```

Variantes:
```typescript
const can = usePermission()

// Formato "module:action"
can('billing:create')          // true/false
can('usuarios:delete')

// Formato separado (module, action)
can('billing', 'create')
can('usuarios', 'delete')

// Módulo solo (asume 'read')
can('pos')                     // = can('pos:read')
```

### 2. ProtectedRoute HOC

Protege componentes:
```typescript
import ProtectedRoute from '@/auth/ProtectedRoute'
import PermissionDenied from '@/components/PermissionDenied'

export default function BillingPage() {
  return (
    <ProtectedRoute
      permission="billing:read"
      fallback={<PermissionDenied permission="billing:read" />}
    >
      <BillingList />
    </ProtectedRoute>
  )
}
```

O anidado:
```typescript
<ProtectedRoute permission="billing:read">
  <div>Contenido visible solo si tiene billing:read</div>

  <ProtectedRoute permission="billing:create">
    <button>Crear factura (solo si tiene billing:create)</button>
  </ProtectedRoute>
</ProtectedRoute>
```

### 3. ProtectedButton

Botón que se deshabilita automáticamente:
```typescript
import ProtectedButton from '@/components/ProtectedButton'

export default function BillingActions() {
  const handleCreate = async () => {
    await api.post('/invoices', data)
  }

  return (
    <>
      <ProtectedButton
        permission="billing:create"
        variant="primary"
        onClick={handleCreate}
      >
        Crear factura
      </ProtectedButton>

      <ProtectedButton
        permission="billing:delete"
        variant="danger"
        onClick={handleDelete}
      >
        Eliminar
      </ProtectedButton>
    </>
  )
}
```

Variantes disponibles:
- `variant="primary"` (azul)
- `variant="danger"` (rojo)
- `variant="secondary"` (gris)
- `variant="ghost"` (transparente)

### 4. PermissionDenied Component

Mostrar mensaje de acceso denegado:
```typescript
import PermissionDenied from '@/components/PermissionDenied'

export default function ProtectedFeature() {
  const can = usePermission()

  if (!can('einvoicing:send')) {
    return (
      <PermissionDenied
        permission="einvoicing:send"
        severity="error"
        footer={<p>Contacta al admin para activar e-facturación</p>}
      />
    )
  }

  return <EinvoicingForm />
}
```

Props:
- `permission`: permiso requerido (ej: "einvoicing:send")
- `action`: acción separada (opcional)
- `severity`: "error" o "warning"
- `message`: reemplaza mensaje default
- `footer`: personaliza el footer

### 5. usePermissionLabel()

Traducir permisos a texto legible:
```typescript
import { usePermissionLabel } from '@/hooks/usePermissionLabel'

export default function RoleForm() {
  const getLabel = usePermissionLabel()

  const permissions = ['billing:create', 'billing:read', 'usuarios:delete']

  return (
    <ul>
      {permissions.map(p => (
        <li key={p}>{getLabel(p)}</li>
      ))}
    </ul>
  )
}

// Output:
// - Crear facturas
// - Ver facturas
// - Eliminar usuarios
```

## Patrones Comunes

### Patrón 1: Proteger ruta completa

```typescript
// apps/tenant/src/modules/billing/Routes.tsx
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import BillingPage from './BillingPage'

export default function BillingRoutes() {
  return (
    <ProtectedRoute permission="billing:read">
      <BillingPage />
    </ProtectedRoute>
  )
}
```

### Patrón 2: Permisos condicionales en tabla

```typescript
const columns = [
  { header: 'Invoice', accessor: 'invoice_number' },
  {
    header: 'Actions',
    accessor: 'actions',
    cell: ({ row }: any) => {
      const can = usePermission()
      return (
        <>
          {can('billing:update') && (
            <ProtectedButton permission="billing:update">Edit</ProtectedButton>
          )}
          {can('billing:delete') && (
            <ProtectedButton permission="billing:delete" variant="danger">
              Delete
            </ProtectedButton>
          )}
        </>
      )
    },
  },
]
```

### Patrón 3: Flujo wizard con permisos

```typescript
export default function InvoiceWizard() {
  const can = usePermission()
  const [step, setStep] = useState(1)

  return (
    <>
      <Step1 />

      {can('billing:create') && (
        <>
          <Step2 />

          {can('billing:send') && <Step3 />}

          {can('einvoicing:send') && <Step4 />}
        </>
      )}
    </>
  )
}
```

### Patrón 4: Admin override

```typescript
// Este se maneja automáticamente:
// Si profile.es_admin_empresa = true, usePermission() devuelve true para TODO
```

## Estructura de Permisos

Los permisos siguen este formato:

```typescript
{
  "modulo": {
    "accion": boolean
  }
}

// Ejemplo:
{
  "billing": {
    "read": true,
    "create": true,
    "delete": false
  },
  "usuarios": {
    "create": true,
    "delete": false
  },
  "pos": {
    "read": true,
    "write": true,
    "cashier": false
  }
}
```

Acciones comunes:
- `read`: ver/listar
- `create`: crear
- `update`: editar
- `delete`: eliminar
- Específicas: `send`, `pay`, `match`, `download`, etc.

## Permisos Disponibles

Todos los módulos tienen estos permisos:

**Usuarios y Roles:**
- `usuarios:create`, `usuarios:read`, `usuarios:update`, `usuarios:delete`, `usuarios:set_password`
- `roles:create`, `roles:read`, `roles:update`, `roles:delete`

**Billing & E-invoicing:**
- `billing:create`, `billing:read`, `billing:update`, `billing:delete`, `billing:send`, `billing:pay`
- `einvoicing:read`, `einvoicing:send`, `einvoicing:download`, `einvoicing:retry`

**Reconciliation:**
- `reconciliation:read`, `reconciliation:match`, `reconciliation:resolve`

**Sales & Purchases:**
- `sales:create`, `sales:read`, `sales:update`, `sales:delete`
- `purchases:create`, `purchases:read`, `purchases:update`, `purchases:delete`

**Inventory & Products:**
- `inventory:read`, `inventory:update`, `inventory:adjust`
- `products:create`, `products:read`, `products:update`, `products:delete`

**Finances & Accounting:**
- `finances:read`, `finances:forecast`, `finances:report`
- `accounting:read`, `accounting:entry`, `accounting:adjust`

**Otros:**
- `pos:read`, `pos:write`, `pos:cashier`
- `settings:read`, `settings:write`
- `reportes:read`, `reportes:export`
- Etc. (ver `locales/es/permissions.json`)

## ¿Dónde está el backend?

**No cambió.** El backend sigue usando:
- `_has_perm()` en `permissions.py`
- `require_perm_*()` decorators
- Validación en `access_guard.py`

El frontend ahora valida **antes** de hacer la llamada API.
Si el backend deniega, el cliente muestra error normalmente.

## Flujo Completo

```
1. Usuario login
   └─ JWT token con "permisos": {...}

2. AuthProvider inicializa
   └─ Token se almacena en sessionStorage

3. PermissionsProvider inicializa
   └─ Lee permisos del token
   └─ Cachea en sessionStorage

4. Componente usa usePermission()
   └─ Chequea contra cache
   └─ Si expired, refetch del API

5. UI se renderiza
   └─ Botones habilitados/deshabilitados
   └─ Rutas protegidas renderizadas/bloqueadas

6. Usuario hace click
   └─ Si no tiene permiso → preventDefault
   └─ Si tiene permiso → API call

7. Backend valida
   └─ 403 si no tiene permiso
   └─ 200 si correcto
```

## Testing

Ejemplo de test:
```typescript
import { renderHook } from '@testing-library/react'
import { usePermission } from '@/hooks/usePermission'

// Mock PermissionsContext
vi.mock('@/contexts/PermissionsContext', () => ({
  usePermissions: () => ({
    permisos: {
      billing: { read: true, create: false },
    },
    hasPermission: (module: string, action: string) => {
      // Lógica del test
    },
  }),
}))

test('should deny billing:create', () => {
  const { result } = renderHook(() => usePermission())
  expect(result.current('billing:create')).toBe(false)
})
```

## Debugging

Si tienes dudas sobre permisos actuales:

```typescript
import { usePermissions } from '@/contexts/PermissionsContext'

export default function DebugPermisos() {
  const { permisos, loading, error } = usePermissions()

  return (
    <pre>
      {JSON.stringify({ permisos, loading, error }, null, 2)}
    </pre>
  )
}
```

O en la consola:
```javascript
// En DevTools
const ctx = document.querySelector('[data-react-root]').__reactInternalInstance
console.log(ctx) // Explora hasta encontrar PermissionsContext
```

## Migrando módulos existentes

Para cada módulo (ej: Billing):

1. **Envolver la ruta:**
   ```typescript
   <ProtectedRoute permission="billing:read">
     <BillingPage />
   </ProtectedRoute>
   ```

2. **Proteger botones de acción:**
   ```typescript
   <ProtectedButton permission="billing:create" onClick={handleCreate}>
     Create
   </ProtectedButton>
   ```

3. **Mostrar acceso denegado:**
   ```typescript
   const can = usePermission()
   if (!can('billing:send')) {
     return <PermissionDenied permission="billing:send" />
   }
   ```

4. **Tests:**
   ```typescript
   // Mockear usePermission() para devolver true/false
   // Verificar que UI se renderiza o se oculta
   ```

## Próximos pasos

1. ✅ Integración Billing (ruta + botones)
2. ✅ Integración Einvoicing
3. ✅ Integración Reconciliation
4. ✅ Todos los módulos
5. ✅ Tests E2E
6. ✅ Documentación de usuario
