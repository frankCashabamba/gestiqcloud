# 🔧 Offline Integration Step-by-Step

Guía detallada para integrar el sistema offline en la app.

## ✅ Estado Actual

- [x] `lib/offlineStore.ts` - Central storage
- [x] `lib/syncManager.ts` - Sync orchestrator  
- [x] `lib/offlineValidation.ts` - Type safety
- [x] `hooks/useOffline.ts` - Global hook
- [x] `modules/pos/offlineSync.ts` - POS adapter (ejemplo)

---

## 📝 Paso 1: Inicializar en App.tsx (30 min)

### 1.1 Imports
```typescript
import { initOfflineStore } from '@/lib/offlineStore'
import { initSyncEventListener, getSyncManager } from '@/lib/syncManager'
import { registerPOSSyncAdapters } from '@/modules/pos/offlineSync'
```

### 1.2 En useEffect de App
```typescript
function App() {
  useEffect(() => {
    // Initialize offline system
    Promise.all([
      initOfflineStore(),
    ]).then(() => {
      initSyncEventListener()
      registerPOSSyncAdapters()
      // Register other adapters as they're created
    }).catch(err => {
      console.error('Failed to initialize offline:', err)
    })
  }, [])

  return (
    // ... your App JSX
  )
}
```

### 1.3 Verificar en console
```javascript
// After app loads
// Debería no haber errores
```

---

## 📝 Paso 2: Crear Adapters para cada Módulo (2 horas c/u)

### Patrón General

Crear en cada módulo: `modules/{modulo}/offlineSync.ts`

```typescript
// modules/products/offlineSync.ts
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import * as productServices from './productsApi'

export const ProductsAdapter: SyncAdapter = {
  entity: 'product',
  canSyncOffline: true,

  async fetchAll() {
    try {
      return await productServices.listProductos()
    } catch {
      return []
    }
  },

  async create(data: any) {
    return await productServices.createProducto(data)
  },

  async update(id: string, data: any) {
    return await productServices.updateProducto(id, data)
  },

  async delete(id: string) {
    await productServices.removeProducto(id)
  },

  async getRemoteVersion(id: string) {
    try {
      const product = await productServices.getProducto(id)
      return product?.version ?? 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    // Products: conflict si price o stock difieren
    return local.price !== remote.price || 
           local.stock !== remote.stock
  }
}

export function registerProductsSyncAdapter() {
  getSyncManager().registerAdapter(ProductsAdapter)
}
```

**Lista de adapters a crear:**

1. **Products** (Media priority)
   - Archivo: `modules/products/offlineSync.ts`
   - Entidad: `product`
   - Campos clave: sku, name, price, stock
   - Conflictos: precio, stock

2. **Customers** (Media priority)
   - Archivo: `modules/customers/offlineSync.ts`
   - Entidad: `customer`
   - Campos clave: name, email, phone
   - Conflictos: contacto, categoría

3. **Sales** (Baja priority)
   - Archivo: `modules/sales/offlineSync.ts`
   - Entidad: `sale`
   - Campos clave: items, customer_id, total
   - Conflictos: items modificados

---

## 📝 Paso 3: Integrar useOffline en UI (2 horas c/u)

### 3.1 En POSView

**Antes:**
```typescript
import useOfflineSync from './hooks/useOfflineSync'

function POSView() {
  const { isOnline, pendingCount } = useOfflineSync()
```

**Después:**
```typescript
import useOffline from '@/hooks/useOffline'

function POSView() {
  const { isOnline, totalPending, syncNow } = useOffline()
  
  // Si necesitas stats por módulo:
  const { syncStatus } = useOffline()
  const receiptsPending = syncStatus.receipt ?? 0
```

### 3.2 Mejorar Badge de Status
```typescript
function OfflineBadge() {
  const { isOnline, totalPending, syncing, syncNow } = useOffline()

  if (!isOnline) {
    return (
      <div className="badge-offline">
        🔴 Offline
        {totalPending > 0 && (
          <button onClick={syncNow} disabled={syncing}>
            Sincronizar ({totalPending})
          </button>
        )}
      </div>
    )
  }

  return <div className="badge-online">🟢 Online</div>
}
```

### 3.3 En Products View
```typescript
import useOffline from '@/hooks/useOffline'

function ProductsView() {
  const { syncStatus } = useOffline()
  const pending = syncStatus.product ?? 0

  return (
    <>
      {pending > 0 && (
        <Alert>
          Tienes {pending} cambios de productos pendientes de sincronizar
        </Alert>
      )}
      {/* ... rest of view */}
    </>
  )
}
```

---

## 📝 Paso 4: Crear Conflict Resolver (2 horas)

### 4.1 Componente
**Archivo:** `components/ConflictResolver.tsx`

```typescript
import React, { useEffect, useState } from 'react'
import { getSyncManager } from '@/lib/syncManager'
import { ConflictInfo } from '@/lib/offlineStore'

export default function ConflictResolver() {
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    const checkConflicts = async () => {
      const manager = getSyncManager()
      const all = await manager.getConflicts()
      setConflicts(all)
    }

    // Check initially
    checkConflicts()

    // Re-check after syncs
    window.addEventListener('offline:sync-completed', checkConflicts)
    return () => window.removeEventListener('offline:sync-completed', checkConflicts)
  }, [])

  if (conflicts.length === 0) return null

  const selected = conflicts.find(c => `${c.entity}:${c.id}` === selectedId)

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999
    }}>
      <div style={{
        background: 'white',
        borderRadius: 8,
        padding: '2rem',
        maxWidth: 800,
        maxHeight: '80vh',
        overflow: 'auto'
      }}>
        <h2>⚠️ Conflictos de Sincronización</h2>
        
        {!selected ? (
          <div>
            <p>{conflicts.length} conflictos detectados</p>
            <ul>
              {conflicts.map(c => (
                <li 
                  key={`${c.entity}:${c.id}`}
                  onClick={() => setSelectedId(`${c.entity}:${c.id}`)}
                  style={{
                    padding: '0.5rem',
                    border: '1px solid #ddd',
                    marginBottom: '0.5rem',
                    cursor: 'pointer',
                    borderRadius: 4
                  }}
                >
                  <strong>{c.entity}</strong>: {c.id}
                  <br />
                  <small>Local v{c.localVersion} vs Remote v{c.remoteVersion}</small>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div>
            <h3>{selected.entity}: {selected.id}</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginY: '1rem' }}>
              <div style={{ border: '1px solid #4CAF50', padding: '1rem', borderRadius: 4 }}>
                <h4 style={{ color: '#4CAF50' }}>📱 Local (v{selected.localVersion})</h4>
                <pre style={{ fontSize: 12, maxHeight: 300, overflow: 'auto' }}>
                  {JSON.stringify(selected.local, null, 2)}
                </pre>
              </div>

              <div style={{ border: '1px solid #FF9800', padding: '1rem', borderRadius: 4 }}>
                <h4 style={{ color: '#FF9800' }}>🌐 Servidor (v{selected.remoteVersion})</h4>
                <pre style={{ fontSize: 12, maxHeight: 300, overflow: 'auto' }}>
                  {JSON.stringify(selected.remote, null, 2)}
                </pre>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button
                onClick={async () => {
                  const manager = getSyncManager()
                  await manager.resolveConflict(selected.entity, selected.id, 'local')
                  setSelectedId(null)
                }}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer'
                }}
              >
                ✅ Usar Local
              </button>

              <button
                onClick={async () => {
                  const manager = getSyncManager()
                  await manager.resolveConflict(selected.entity, selected.id, 'remote', selected.remote)
                  setSelectedId(null)
                }}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#FF9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer'
                }}
              >
                ✅ Usar Servidor
              </button>

              <button
                onClick={() => setSelectedId(null)}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#999',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer'
                }}
              >
                Atrás
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

### 4.2 En App.tsx
```typescript
import ConflictResolver from '@/components/ConflictResolver'

function App() {
  return (
    <>
      <ConflictResolver />
      {/* ... rest of app */}
    </>
  )
}
```

---

## 📝 Paso 5: Tests (3-4 horas)

### 5.1 Actualizar `offline-online.integration.test.tsx`

Completar los TODOs:

```typescript
it('should sync receipts when coming online', async () => {
  const user = userEvent.setup()
  
  render(<POSView />)
  
  // Go offline
  window.dispatchEvent(new Event('offline'))
  expect(screen.getByText(/offline/i)).toBeInTheDocument()
  
  // Create receipt
  await user.click(screen.getByText('Nueva Venta'))
  // ... fill form ...
  await user.click(screen.getByText('Guardar'))
  
  // Should show offline message
  expect(screen.getByText(/guardado offline/i)).toBeInTheDocument()
  
  // Go online
  window.dispatchEvent(new Event('online'))
  
  // Should auto-sync
  await waitFor(() => {
    expect(screen.getByText(/sincronizado/i)).toBeInTheDocument()
  }, { timeout: 3000 })
})
```

### 5.2 E2E con Playwright

**Archivo:** `e2e/offline.spec.ts`

```typescript
import { test, expect } from '@playwright/test'

test('POS offline workflow', async ({ browser }) => {
  const context = await browser.createBrowserContext()
  const page = await context.newPage()
  
  // Navigate
  await page.goto('http://localhost:5173/pos')
  
  // Simulate offline
  await context.setOffline(true)
  
  // Create receipt
  await page.click('button:has-text("Nueva Venta")')
  await page.fill('[name="qty"]', '1')
  await page.fill('[name="price"]', '100')
  await page.click('button:has-text("Guardar")')
  
  // Should see offline message
  await expect(page.locator('text=Offline')).toBeVisible()
  
  // Go online
  await context.setOffline(false)
  
  // Should sync
  await expect(page.locator('text=Sincronizado')).toBeVisible()
  
  await context.close()
})
```

---

## 📝 Paso 6: Polish UI (2 horas)

### 6.1 Dashboard Simple
```typescript
function OfflineSyncDashboard() {
  const { isOnline, syncStatus, totalPending, syncing, syncNow } = useOffline()
  
  if (isOnline && totalPending === 0) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: 20,
      right: 20,
      background: 'white',
      border: '1px solid #ddd',
      borderRadius: 8,
      padding: '1rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      maxWidth: 300,
      zIndex: 1000
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
        {isOnline ? '🟢' : '🔴'} {isOnline ? 'Online' : 'Offline'}
      </div>
      
      {totalPending > 0 && (
        <>
          <div style={{ fontSize: 12, color: '#666', marginBottom: '0.5rem' }}>
            {totalPending} cambios pendientes
          </div>
          
          {Object.entries(syncStatus).map(([entity, count]) => (
            count > 0 && (
              <div key={entity} style={{ fontSize: 11, color: '#999' }}>
                • {entity}: {count}
              </div>
            )
          ))}
          
          <button
            onClick={() => syncNow()}
            disabled={syncing || !isOnline}
            style={{
              width: '100%',
              marginTop: '0.5rem',
              padding: '0.5rem',
              background: isOnline ? '#007bff' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: isOnline ? 'pointer' : 'default'
            }}
          >
            {syncing ? 'Sincronizando...' : 'Sincronizar'}
          </button>
        </>
      )}
    </div>
  )
}
```

---

## ✅ Checklist de Integración

```
INICIALIZACIÓN
- [ ] App.tsx: initOfflineStore()
- [ ] App.tsx: initSyncEventListener()
- [ ] App.tsx: registerPOSSyncAdapters()

ADAPTERS
- [ ] modules/products/offlineSync.ts
- [ ] modules/customers/offlineSync.ts
- [ ] Registrados en App.tsx

COMPONENTES
- [ ] OfflineBadge mejorado
- [ ] ConflictResolver.tsx
- [ ] OfflineSyncDashboard
- [ ] Integrados en App.tsx

TESTS
- [ ] offline-online.integration.test.tsx completado (7/7 tests)
- [ ] E2E offline.spec.ts (3/3 scenarios)
- [ ] Coverage > 80%

UI/UX
- [ ] Banner offline mejorado
- [ ] Progress durante sync
- [ ] Error handling visible
- [ ] Mensajes claros en español
```

---

## 🚀 Orden de Ejecución Recomendado

**Día 1 (2 horas):**
1. Paso 1: Inicializar en App.tsx

**Día 2-3 (4 horas):**
2. Paso 2: Crear 2-3 adapters (Products, Customers)

**Día 4 (2 horas):**
3. Paso 3: Integrar useOffline en componentes

**Día 5 (2 horas):**
4. Paso 4: ConflictResolver

**Día 6-7 (5 horas):**
5. Paso 5: Tests

**Día 8 (2 horas):**
6. Paso 6: Polish UI

---

## 🐛 Troubleshooting

### IndexedDB no abre
```javascript
// Clear & reinitialize
import { clearAllOfflineData } from '@/lib/offlineStore'
await clearAllOfflineData()
location.reload()
```

### Sync no funciona
```javascript
// Check if adapters registered
import { getSyncManager } from '@/lib/syncManager'
const mgr = getSyncManager()
console.log(`Adapters registered: ${mgr.getAdapterCount()}`)
```

### Conflictos no aparecen
```javascript
// Check conflicts directly
import { getConflicts } from '@/lib/offlineStore'
const conflicts = await getConflicts()
console.log(conflicts)
```

---

## 📞 Soporte

En caso de dudas:
- Ver `OFFLINE_QUICK_START.md` para ejemplos
- Ver código en `lib/offlineStore.ts`, `lib/syncManager.ts`
- Usar `debugDump()` para inspeccionar datos
- Abrir DevTools → Application → IndexedDB

