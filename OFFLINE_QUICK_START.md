# Offline Development - Quick Start Guide

## ✅ Completado

Archivos creados en Fase 1:
1. **`lib/offlineStore.ts`** - Central IndexedDB storage para todas las entidades
2. **`hooks/useOffline.ts`** - Hook global reemplazando `useOfflineSync` 
3. **`lib/syncManager.ts`** - Orquestador central de sincronización

## 🚀 Próximos Pasos (Implementar en Este Orden)

### Paso 1: Crear Sync Adapters para cada módulo (2-4 horas)

#### 1.1 POS Adapter
**Archivo:** `apps/tenant/src/modules/pos/offlineSync.ts`

```typescript
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import * as posServices from './services'
import { storeEntity, listEntities } from '@/lib/offlineStore'

export const POSReceiptAdapter: SyncAdapter = {
  entity: 'receipt',
  canSyncOffline: true,
  
  async fetchAll() {
    // Fetch from server - will be cached
    return [] // TODO: implement
  },
  
  async create(data: any) {
    return await posServices.createReceipt(data)
  },
  
  async update(id: string, data: any) {
    // POS receipts are immutable, so skip
  },
  
  async delete(id: string) {
    // Not supported for receipts
  },
  
  async getRemoteVersion(id: string) {
    // Check server version
    return 0
  },
  
  detectConflict(local: any, remote: any) {
    // Receipts don't conflict (immutable)
    return false
  }
}

// Register on app init
getSyncManager().registerAdapter(POSReceiptAdapter)
```

#### 1.2 Products Adapter
**Similar structure**

#### 1.3 Customers Adapter
**Similar structure**

### Paso 2: Integrar `useOffline` en componentes (2 horas)

#### En POS:
```typescript
// Reemplazar useOfflineSync
import useOffline from '@/hooks/useOffline'

function POSView() {
  const { isOnline, totalPending, syncNow } = useOffline()
  
  return (
    <>
      <OfflineBadge isOnline={isOnline} />
      {totalPending > 0 && (
        <button onClick={() => syncNow('receipt')}>
          Sincronizar {totalPending} cambios
        </button>
      )}
    </>
  )
}
```

### Paso 3: Crear Conflict Resolver UI (3 horas)

**Archivo:** `apps/tenant/src/components/ConflictResolver.tsx`

```typescript
import React from 'react'
import { ConflictInfo } from '@/lib/offlineStore'
import { getSyncManager } from '@/lib/syncManager'

interface ConflictResolverProps {
  conflicts: ConflictInfo[]
  onResolved?: () => void
}

export default function ConflictResolver({ conflicts, onResolved }: ConflictResolverProps) {
  const [selectedConflict, setSelectedConflict] = React.useState<ConflictInfo | null>(null)

  const handleResolve = async (resolution: 'local' | 'remote') => {
    if (!selectedConflict) return
    
    const manager = getSyncManager()
    await manager.resolveConflict(
      selectedConflict.entity,
      selectedConflict.id,
      resolution,
      selectedConflict.remote
    )
    
    setSelectedConflict(null)
    onResolved?.()
  }

  if (conflicts.length === 0) return null

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
      <div style={{ background: 'white', padding: '2rem', borderRadius: 8, maxWidth: 600, maxHeight: '80vh', overflow: 'auto' }}>
        <h2>Conflictos de Sincronización ({conflicts.length})</h2>
        
        {selectedConflict ? (
          <div>
            <h3>Conflicto en {selectedConflict.entity}: {selectedConflict.id}</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginY: '1rem' }}>
              <div>
                <h4>Cambios Locales</h4>
                <pre>{JSON.stringify(selectedConflict.local, null, 2)}</pre>
              </div>
              <div>
                <h4>Versión Servidor</h4>
                <pre>{JSON.stringify(selectedConflict.remote, null, 2)}</pre>
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={() => handleResolve('local')}>Usar Locales</button>
              <button onClick={() => handleResolve('remote')}>Usar Servidor</button>
              <button onClick={() => setSelectedConflict(null)}>Cancelar</button>
            </div>
          </div>
        ) : (
          <ul>
            {conflicts.map(c => (
              <li key={`${c.entity}:${c.id}`} onClick={() => setSelectedConflict(c)} style={{ cursor: 'pointer', padding: '0.5rem', border: '1px solid #ccc', marginBottom: '0.5rem' }}>
                {c.entity}: {c.id}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
```

### Paso 4: Completar Tests (3 horas)

Completar `offline-online.integration.test.tsx`:

```typescript
it('should sync receipts offline and handle conflicts', async () => {
  const user = userEvent.setup()
  
  render(
    <ElectricTestProvider>
      <POSView />
    </ElectricTestProvider>
  )
  
  // Simulate offline
  window.dispatchEvent(new Event('offline'))
  
  // Create receipt
  const receiptBtn = screen.getByText('Nueva Venta')
  await user.click(receiptBtn)
  // ... fill form ...
  await user.click(screen.getByText('Guardar'))
  
  // Should show offline message
  expect(screen.getByText(/offline/i)).toBeInTheDocument()
  
  // Go online
  window.dispatchEvent(new Event('online'))
  
  // Should sync automatically
  await waitFor(() => {
    expect(screen.getByText(/sincronizado/i)).toBeInTheDocument()
  })
})
```

### Paso 5: Mejorar UI (2 horas)

#### Dashboard Simple
```typescript
function OfflineSyncDashboard() {
  const { isOnline, syncStatus, totalPending, syncing } = useOffline()
  
  return (
    <div style={{ padding: '1rem', border: '1px solid #ccc' }}>
      <h3>Estado de Sincronización</h3>
      <p>Conexión: {isOnline ? '🟢 Online' : '🔴 Offline'}</p>
      <p>Pendientes: {totalPending}</p>
      
      {Object.entries(syncStatus).map(([entity, count]) => (
        count > 0 && <p key={entity}>{entity}: {count} cambios</p>
      ))}
      
      <button onClick={() => syncNow()} disabled={syncing || !isOnline}>
        {syncing ? 'Sincronizando...' : 'Sincronizar Ahora'}
      </button>
    </div>
  )
}
```

---

## 📋 Checklist de Implementación

```
FASE 1: INFRAESTRUCTURA ✅
- [x] offlineStore.ts creado
- [x] useOffline.ts creado
- [x] syncManager.ts creado

FASE 2: ADAPTERS (Siguiente)
- [ ] POSReceiptAdapter
- [ ] ProductsAdapter
- [ ] CustomersAdapter
- [ ] SalesAdapter (opcional)

FASE 3: INTEGRACIÓN
- [ ] useOffline integrado en POSView
- [ ] useOffline integrado en ProductsView
- [ ] useOffline integrado en CustomersView
- [ ] initSyncEventListener() llamado en App.tsx

FASE 4: CONFLICT RESOLUTION
- [ ] ConflictResolver.tsx creado
- [ ] Mostrado en App cuando hay conflictos
- [ ] Manejo de resoluciones

FASE 5: TESTING
- [ ] Tests offline-online.integration completados
- [ ] E2E tests con Playwright
- [ ] Coverage > 80%

FASE 6: UX POLISH
- [ ] OfflineSyncDashboard
- [ ] Mejorar banners
- [ ] Progress indicators
```

---

## 🔌 Integración en App.tsx

```typescript
import { initSyncEventListener, getSyncManager } from '@/lib/syncManager'
import { POSReceiptAdapter } from '@/modules/pos/offlineSync'
import { ProductsAdapter } from '@/modules/products/offlineSync'

function App() {
  useEffect(() => {
    // Initialize sync system
    initSyncEventListener()
    getSyncManager().registerAdapter(POSReceiptAdapter)
    getSyncManager().registerAdapter(ProductsAdapter)
    // ... register more adapters
  }, [])

  const { isOnline } = useOffline()

  return (
    <>
      {/* Existing UI */}
      <ConflictResolver conflicts={conflicts} />
      {isOnline && <OfflineSyncDashboard />}
    </>
  )
}
```

---

## 🐛 Testing Offline Localmente

### Chrome DevTools
1. F12 → Network tab
2. Check "Throttling" → "Offline"
3. Hacer cambios
4. Unchecked → cambios sync automáticamente

### Service Worker
1. DevTools → Application → Service Workers
2. Check "Offline" checkbox
3. Refresca página - funciona offline

---

## 📞 Debugging

```typescript
// En browser console
import { debugDump } from '@/lib/offlineStore'

debugDump()           // Ver todo
debugDump('receipt')  // Ver solo receipts
debugDump('product')  // Ver solo products

import { getStorageStats } from '@/lib/offlineStore'
getStorageStats()     // Stats: total, by entity, by status
```

---

## ⚠️ Notas Importantes

1. **Versioning**: Cada entidad necesita `localVersion` y `remoteVersion` para detectar conflictos
2. **Timestamps**: Usar `Date.now()` consistentemente
3. **IDB vs localStorage**: 
   - localStorage: max ~5-10MB, más lento
   - IndexedDB: ~50MB+, más rápido ✅
4. **Service Worker**: Mantener - no reemplazar con ElectricSQL
5. **Backoff**: SW ya tiene retry exponencial, SyncManager también

---

## 📚 Referencias

- [IndexedDB API](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
- [Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [idb-keyval](https://github.com/jakearchibald/idb-keyval)
- [Offline-first patterns](https://offlinefirst.org/)

