# Ejemplo: Integración de Permisos en Billing

Este documento muestra paso a paso cómo integrar el nuevo sistema de permisos en el módulo Billing.

## Paso 1: Revisar estructura actual

```
apps/tenant/src/modules/billing/
├── Routes.tsx           # Rutas del módulo
├── Panel.tsx           # Componente principal
├── BillingList.tsx     # Listado de facturas
├── BillingForm.tsx     # Formulario crear/editar
├── manifest.ts         # Definición del módulo
└── services.ts         # Llamadas API
```

## Paso 2: Actualizar manifest.ts

El manifest ya tiene permisos, pero asegúrate que estén correctos:

```typescript
// apps/tenant/src/modules/billing/manifest.ts

export const manifest = {
  id: 'billing',
  name: 'Facturación',
  version: '1.0.0',
  // ✅ Permisos esperados:
  permissions: [
    'billing:read',
    'billing:create',
    'billing:update',
    'billing:delete',
    'billing:send',
    'billing:pay',
  ],
  routes: [
    { path: '/billing', element: BillingPanel },
    { path: '/billing/create', element: BillingForm },
    { path: '/billing/:id', element: BillingDetail },
    { path: '/billing/:id/edit', element: BillingForm },
  ],
  menu: {
    title: 'Facturación',
    icon: '📄',
    route: '/billing',
  },
}
```

## Paso 3: Proteger Routes.tsx

```typescript
// apps/tenant/src/modules/billing/Routes.tsx

import { useMemo } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import { BillingPanel, BillingForm, BillingDetail } from '.'

export default function BillingRoutes() {
  return (
    <ProtectedRoute
      permission="billing:read"
      fallback={<PermissionDenied permission="billing:read" />}
    >
      <Routes>
        <Route path="/" element={<BillingPanel />} />
        <Route path="/create" element={
          <ProtectedRoute permission="billing:create">
            <BillingForm />
          </ProtectedRoute>
        } />
        <Route path="/:id" element={<BillingDetail />} />
        <Route path="/:id/edit" element={
          <ProtectedRoute permission="billing:update">
            <BillingForm />
          </ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
```

## Paso 4: Actualizar BillingList.tsx

Proteger acciones en la tabla:

```typescript
// apps/tenant/src/modules/billing/BillingList.tsx

import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import { useNavigate } from 'react-router-dom'

export default function BillingList() {
  const can = usePermission()
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState<Invoice[]>([])

  const handleDelete = async (id: string) => {
    if (!can('billing:delete')) return
    if (!window.confirm('¿Eliminar factura?')) return

    try {
      await api.delete(`/invoices/${id}`)
      setInvoices(inv => inv.filter(i => i.id !== id))
      toast.success('Factura eliminada')
    } catch (e) {
      toast.error('Error al eliminar')
    }
  }

  return (
    <div className="billing-list">
      <div className="header">
        <h1>Facturas</h1>
        {can('billing:create') && (
          <ProtectedButton
            permission="billing:create"
            variant="primary"
            onClick={() => navigate('/billing/create')}
          >
            + Nueva Factura
          </ProtectedButton>
        )}
      </div>

      <table>
        <thead>
          <tr>
            <th>Número</th>
            <th>Fecha</th>
            <th>Cliente</th>
            <th>Total</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map(inv => (
            <tr key={inv.id}>
              <td>{inv.number}</td>
              <td>{formatDate(inv.created_at)}</td>
              <td>{inv.customer_name}</td>
              <td>{formatCurrency(inv.total)}</td>
              <td>
                <Badge status={inv.status} />
              </td>
              <td className="actions">
                {can('billing:read') && (
                  <button onClick={() => navigate(`/billing/${inv.id}`)}>
                    Ver
                  </button>
                )}

                {can('billing:update') && (
                  <ProtectedButton
                    permission="billing:update"
                    variant="secondary"
                    onClick={() => navigate(`/billing/${inv.id}/edit`)}
                  >
                    Editar
                  </ProtectedButton>
                )}

                {can('billing:send') && inv.status === 'draft' && (
                  <ProtectedButton
                    permission="billing:send"
                    variant="secondary"
                    onClick={() => sendInvoice(inv.id)}
                  >
                    Enviar
                  </ProtectedButton>
                )}

                {can('billing:pay') && inv.status === 'sent' && (
                  <ProtectedButton
                    permission="billing:pay"
                    variant="secondary"
                    onClick={() => recordPayment(inv.id)}
                  >
                    Pagar
                  </ProtectedButton>
                )}

                {can('billing:delete') && (
                  <ProtectedButton
                    permission="billing:delete"
                    variant="danger"
                    onClick={() => handleDelete(inv.id)}
                  >
                    Eliminar
                  </ProtectedButton>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

## Paso 5: Actualizar BillingForm.tsx

```typescript
// apps/tenant/src/modules/billing/BillingForm.tsx

import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'

export default function BillingForm({ invoiceId }: { invoiceId?: string }) {
  const can = usePermission()
  const [form, setForm] = useState<InvoiceForm>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const isEdit = !!invoiceId

  // Validar permisos
  const requiredPerm = isEdit ? 'billing:update' : 'billing:create'
  if (!can(requiredPerm)) {
    return (
      <PermissionDenied
        permission={requiredPerm}
        footer={<p>Contacta al administrador para {
          isEdit ? 'editar facturas' : 'crear facturas'
        }</p>}
      />
    )
  }

  const handleSave = async () => {
    if (!form.customer_id) {
      setErrors({ customer_id: 'Cliente requerido' })
      return
    }

    try {
      if (isEdit) {
        await api.patch(`/invoices/${invoiceId}`, form)
        toast.success('Factura actualizada')
      } else {
        await api.post('/invoices', form)
        toast.success('Factura creada')
      }
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <form className="billing-form">
      <h1>{isEdit ? 'Editar Factura' : 'Crear Factura'}</h1>

      <div className="form-group">
        <label>Cliente *</label>
        <select
          value={form.customer_id || ''}
          onChange={(e) => setForm({...form, customer_id: e.target.value})}
        >
          <option value="">Selecciona cliente</option>
          {/* ... opciones ... */}
        </select>
        {errors.customer_id && <span className="error">{errors.customer_id}</span>}
      </div>

      <div className="form-group">
        <label>Fecha *</label>
        <input
          type="date"
          value={form.date}
          onChange={(e) => setForm({...form, date: e.target.value})}
        />
      </div>

      {/* Más campos ... */}

      <div className="form-actions">
        <ProtectedButton
          permission={requiredPerm}
          variant="primary"
          onClick={handleSave}
        >
          {isEdit ? 'Guardar' : 'Crear'}
        </ProtectedButton>

        <button
          type="button"
          onClick={() => window.history.back()}
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}
```

## Paso 6: Actualizar BillingDetail.tsx

```typescript
// apps/tenant/src/modules/billing/BillingDetail.tsx

import { useParams } from 'react-router-dom'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'

export default function BillingDetail() {
  const { id } = useParams<{ id: string }>()
  const can = usePermission()
  const [invoice, setInvoice] = useState<Invoice | null>(null)

  useEffect(() => {
    api.get(`/invoices/${id}`).then(setInvoice)
  }, [id])

  const handleSend = async () => {
    if (!can('billing:send')) return

    try {
      await api.post(`/invoices/${id}/send`)
      toast.success('Factura enviada')
      setInvoice({...invoice, status: 'sent'})
    } catch (e) {
      toast.error(e.message)
    }
  }

  const handleRecordPayment = async (amount: number) => {
    if (!can('billing:pay')) return

    try {
      await api.post(`/invoices/${id}/payments`, { amount })
      toast.success('Pago registrado')
      setInvoice(prev => ({...prev, paid_amount: (prev?.paid_amount || 0) + amount}))
    } catch (e) {
      toast.error(e.message)
    }
  }

  if (!invoice) return <div>Cargando...</div>

  return (
    <div className="invoice-detail">
      <div className="header">
        <h1>Factura {invoice.number}</h1>

        <div className="actions">
          {can('billing:update') && (
            <ProtectedButton permission="billing:update">
              Editar
            </ProtectedButton>
          )}

          {can('billing:send') && invoice.status === 'draft' && (
            <ProtectedButton
              permission="billing:send"
              onClick={handleSend}
            >
              Enviar
            </ProtectedButton>
          )}

          {can('billing:pay') && invoice.pending_amount > 0 && (
            <ProtectedButton
              permission="billing:pay"
              onClick={() => {/* modal de pago */}}
            >
              Registrar Pago
            </ProtectedButton>
          )}

          {can('billing:delete') && (
            <ProtectedButton
              permission="billing:delete"
              variant="danger"
            >
              Eliminar
            </ProtectedButton>
          )}
        </div>
      </div>

      {/* Detalles de factura ... */}
    </div>
  )
}
```

## Paso 7: Tests

Crear tests E2E con Playwright:

```typescript
// e2e/billing.spec.ts

import { test, expect } from '@playwright/test'

test.describe('Billing Module', () => {
  test('user without billing:read should not see module', async ({ page }) => {
    // Mock: usuario sin permisos
    page.evaluate(() => {
      sessionStorage.setItem('permisos', JSON.stringify({}))
    })

    await page.goto('/billing')
    await expect(page.locator('text=No autorizado')).toBeVisible()
  })

  test('user with billing:read but no billing:create should not see create button', async ({ page }) => {
    // Login como usuario con billing:read pero sin billing:create
    await loginAs(page, 'user_billing_read_only')

    await page.goto('/billing')

    // Ver lista
    await expect(page.locator('text=Facturas')).toBeVisible()

    // No ver botón crear
    const createBtn = page.locator('button:has-text("Nueva Factura")')
    await expect(createBtn).not.toBeVisible()
  })

  test('user with billing:create should see and use create button', async ({ page }) => {
    // Login como usuario con todos los permisos
    await loginAs(page, 'admin')

    await page.goto('/billing')

    // Ver botón crear
    const createBtn = page.locator('button:has-text("Nueva Factura")')
    await expect(createBtn).toBeVisible()
    await expect(createBtn).toBeEnabled()

    // Click
    await createBtn.click()

    // Ver formulario
    await expect(page.locator('h1:has-text("Crear Factura")')).toBeVisible()
  })

  test('user with billing:delete should see delete button', async ({ page }) => {
    await loginAs(page, 'admin')
    await page.goto('/billing')

    // Buscar primer fila con delete button
    const firstDeleteBtn = page.locator('button:has-text("Eliminar")').first()
    await expect(firstDeleteBtn).toBeVisible()
  })
})
```

## Paso 8: Documentación

Agregar a la documentación de usuario:

```markdown
## Facturación - Permisos Requeridos

### Ver facturas
- Permiso: `billing:read`
- Acceso: Lista de facturas, detalles

### Crear facturas
- Permiso: `billing:create`
- Acceso: Botón "Nueva Factura", formulario de creación

### Editar facturas
- Permiso: `billing:update`
- Acceso: Botón "Editar", formulario de edición

### Enviar facturas
- Permiso: `billing:send`
- Acceso: Botón "Enviar", notificaciones

### Registrar pagos
- Permiso: `billing:pay`
- Acceso: Botón "Registrar Pago", modal de pago

### Eliminar facturas
- Permiso: `billing:delete`
- Acceso: Botón "Eliminar"

Si no tienes alguno de estos permisos, contacta al administrador.
```

## Checklist de Implementación

- [ ] Revisar manifest.ts
- [ ] Actualizar Routes.tsx con ProtectedRoute
- [ ] Agregar usePermission() en componentes
- [ ] Proteger botones con ProtectedButton
- [ ] Mostrar PermissionDenied cuando sea necesario
- [ ] Tests unitarios (usePermission)
- [ ] Tests E2E (flujos con permisos)
- [ ] Documentación de usuario
- [ ] Code review
- [ ] Deploy

## Validación

Una vez integrado, verificar:

1. ✅ Usuario sin `billing:read` → `/billing` → redirige a Unauthorized
2. ✅ Usuario con `billing:read` → ve lista
3. ✅ Usuario sin `billing:create` → botón "Crear" deshabilitado
4. ✅ Usuario sin `billing:send` → botón "Enviar" no visible
5. ✅ Admin → todos los botones habilitados
6. ✅ Cambiar permisos en BD → refetch automático en frontend

## Próxima integración

Repetir este flujo para:
- Einvoicing
- Reconciliation
- Sales
- Purchases
- Otros módulos
