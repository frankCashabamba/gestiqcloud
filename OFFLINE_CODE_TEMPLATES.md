# 💻 Offline Code Templates - Copy & Paste Ready

Templates listos para copiar-pegar para acelerar implementación.

---

## 1️⃣ ProductsAdapter Template

**Archivo:** `apps/tenant/src/modules/products/offlineSync.ts`

```typescript
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import * as productServices from './productsApi'
import { storeEntity } from '@/lib/offlineStore'

export const ProductsAdapter: SyncAdapter = {
  entity: 'product',
  canSyncOffline: true,

  async fetchAll() {
    try {
      return await productServices.listProductos()
    } catch (error) {
      console.error('Failed to fetch products:', error)
      return []
    }
  },

  async create(data: any) {
    const product = await productServices.createProducto(data)
    await storeEntity('product', product.id, product, 'synced')
    return product
  },

  async update(id: string, data: any) {
    const product = await productServices.updateProducto(id, data)
    await storeEntity('product', id, product, 'synced')
    return product
  },

  async delete(id: string) {
    await productServices.removeProducto(id)
  },

  async getRemoteVersion(id: string) {
    try {
      const product = await productServices.getProducto(id)
      return product?.version ?? product?.updated_at ? 1 : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    // Conflict if price, stock, or name differ
    return local.price !== remote.price ||
           local.stock !== remote.stock ||
           local.name !== remote.name
  }
}

export function registerProductsSyncAdapter() {
  getSyncManager().registerAdapter(ProductsAdapter)
}
```

---

## 2️⃣ CustomersAdapter Template

**Archivo:** `apps/tenant/src/modules/customers/offlineSync.ts`

```typescript
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
// Import your customer services
import { storeEntity } from '@/lib/offlineStore'

export const CustomersAdapter: SyncAdapter = {
  entity: 'customer',
  canSyncOffline: true,

  async fetchAll() {
    try {
      // TODO: implement
      return []
    } catch (error) {
      console.error('Failed to fetch customers:', error)
      return []
    }
  },

  async create(data: any) {
    // TODO: call your create service
    const customer = { id: data.id, ...data }
    await storeEntity('customer', customer.id, customer, 'synced')
    return customer
  },

  async update(id: string, data: any) {
    // TODO: call your update service
    await storeEntity('customer', id, data, 'synced')
  },

  async delete(id: string) {
    // TODO: call your delete service
  },

  async getRemoteVersion(id: string) {
    // TODO: return version or 0 if not found
    return 0
  },

  detectConflict(local: any, remote: any): boolean {
    // Conflict if email or name differ
    return local.email !== remote.email ||
           local.name !== remote.name
  }
}

export function registerCustomersSyncAdapter() {
  getSyncManager().registerAdapter(CustomersAdapter)
}
```

---

## 3️⃣ App.tsx Initialization

**Reemplaza o añade en tu función App:**

```typescript
import { useEffect } from 'react'
import { initOfflineStore } from '@/lib/offlineStore'
import { initSyncEventListener, getSyncManager } from '@/lib/syncManager'
import { registerPOSSyncAdapters } from '@/modules/pos/offlineSync'
import { registerProductsSyncAdapter } from '@/modules/products/offlineSync'
import { registerCustomersSyncAdapter } from '@/modules/customers/offlineSync'

function App() {
  useEffect(() => {
    // Initialize offline system
    Promise.all([
      initOfflineStore(),
    ]).then(() => {
      // Setup sync listener
      initSyncEventListener()

      // Register adapters
      registerPOSSyncAdapters()
      registerProductsSyncAdapter()
      registerCustomersSyncAdapter()
      // ... add more as you create them

      console.log('✅ Offline system initialized')
    }).catch(err => {
      console.error('❌ Failed to initialize offline:', err)
    })
  }, [])

  return (
    <>
      {/* Your existing App JSX */}
    </>
  )
}

export default App
```

---

## 4️⃣ Update POSView

**Reemplaza useOfflineSync con useOffline:**

```typescript
// BEFORE:
// import useOfflineSync from './hooks/useOfflineSync'

// AFTER:
import useOffline from '@/hooks/useOffline'

function POSView() {
  // BEFORE:
  // const { isOnline, pendingCount, syncNow } = useOfflineSync()

  // AFTER:
  const { isOnline, totalPending, syncNow, syncing } = useOffline()

  return (
    <>
      {/* Your existing POS UI */}

      {/* Status Badge */}
      <div style={{
        position: 'fixed',
        top: 10,
        right: 10,
        padding: '0.5rem 1rem',
        background: isOnline ? '#4CAF50' : '#f44336',
        color: 'white',
        borderRadius: 4,
        fontSize: 12,
      }}>
        {isOnline ? '🟢 Online' : '🔴 Offline'}
        {totalPending > 0 && ` • ${totalPending} pendientes`}
      </div>

      {/* Sync Button */}
      {totalPending > 0 && (
        <button
          onClick={() => syncNow('receipt')}
          disabled={syncing || !isOnline}
          style={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            padding: '0.5rem 1rem',
            background: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            cursor: syncing ? 'wait' : 'pointer',
          }}
        >
          {syncing ? 'Sincronizando...' : `Sincronizar (${totalPending})`}
        </button>
      )}
    </>
  )
}
```

---

## 5️⃣ Update ProductsView

```typescript
import useOffline from '@/hooks/useOffline'

function ProductsView() {
  const { syncStatus } = useOffline()
  const productsPending = syncStatus.product ?? 0

  return (
    <>
      {/* Your existing Products UI */}

      {productsPending > 0 && (
        <div style={{
          background: '#fff3cd',
          border: '1px solid #ffc107',
          padding: '1rem',
          borderRadius: 4,
          marginBottom: '1rem'
        }}>
          ⚠️ Tienes {productsPending} cambios de productos esperando sincronización
        </div>
      )}
    </>
  )
}
```

---

## 6️⃣ Improved OfflineBanner

**Reemplaza el componente en `packages/ui/src/OfflineBanner.tsx`:**

```typescript
import React, { useEffect, useRef, useState } from 'react'
import { sendTelemetry } from '@shared'
import useOffline from '@tenant/hooks/useOffline'

type Notice = { kind: 'info' | 'success' | 'warning' | 'error'; text: string; progress?: number }

export default function OfflineBanner() {
  const [notice, setNotice] = useState<Notice | null>(null)
  const timer = useRef<number | null>(null)
  const { isOnline, syncing } = useOffline()

  useEffect(() => {
    const show = (n: Notice, ms = 4000) => {
      setNotice(n)
      if (timer.current) window.clearTimeout(timer.current)
      if (ms > 0) {
        timer.current = window.setTimeout(() => setNotice(null), ms)
      }
    }

    const onMsg = (e: MessageEvent) => {
      const data = e.data || {}
      if (data.type === 'OUTBOX_QUEUED') {
        show({ kind: 'warning', text: 'Acción guardada offline. Se sincronizará al reconectarse.' })
        sendTelemetry('outbox_queued')
      }
      if (data.type === 'OUTBOX_SYNCED') {
        const ok = data.ok || 0
        const fail = data.fail || 0
        if (ok > 0) {
          show({
            kind: 'success',
            text: `✅ Sincronización completada: ${ok} cambios${fail ? `, ${fail} pendientes` : ''}.`,
          }, 5000)
          sendTelemetry('outbox_synced', { ok, fail, deferred: data.deferred || 0 })
        }
      }
    }

    const onOnline = () => {
      show({ kind: 'info', text: '🟢 Conectado. Sincronizando…' }, 2500)
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then((reg) => reg.active?.postMessage({ type: 'SYNC_NOW' }))
      }
      sendTelemetry('app_online')
    }

    const onOffline = () => {
      show({ kind: 'warning', text: '🔴 Sin conexión. Trabajarás en modo offline.', progress: 0 }, 0)
      sendTelemetry('app_offline')
    }

    navigator.serviceWorker?.addEventListener('message', onMsg)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)

    return () => {
      navigator.serviceWorker?.removeEventListener('message', onMsg)
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])

  // Show syncing indicator
  if (syncing) {
    return (
      <div style={{
        position: 'fixed', left: 12, right: 12, bottom: 12, zIndex: 1000,
        background: '#3498db', color: 'white', padding: '10px 12px', borderRadius: 8,
        border: '1px solid #2980b9', boxShadow: '0 6px 18px rgba(0,0,0,.18)',
        fontSize: 14
      }}>
        ⏳ Sincronizando cambios...
      </div>
    )
  }

  if (!notice) return null

  const bg = notice.kind === 'success' ? '#065f46' :
            notice.kind === 'warning' ? '#92400e' :
            notice.kind === 'error' ? '#7c2d12' : '#334155'
  const border = notice.kind === 'success' ? '#34d399' :
                notice.kind === 'warning' ? '#fbbf24' :
                notice.kind === 'error' ? '#fb923c' : '#94a3b8'

  return (
    <div style={{
      position: 'fixed', left: 12, right: 12, bottom: 12, zIndex: 1000,
      background: bg, color: 'white', padding: '10px 12px', borderRadius: 8,
      border: `1px solid ${border}`, boxShadow: '0 6px 18px rgba(0,0,0,.18)',
      fontSize: 14
    }}>
      {notice.text}
      {notice.progress !== undefined && (
        <div style={{
          marginTop: '0.5rem',
          background: 'rgba(255,255,255,0.2)',
          height: 4,
          borderRadius: 2,
          overflow: 'hidden'
        }}>
          <div style={{
            background: 'white',
            height: '100%',
            width: `${notice.progress * 100}%`,
            transition: 'width 0.3s ease'
          }} />
        </div>
      )}
    </div>
  )
}
```

---

## 7️⃣ ConflictResolver Component

**Archivo:** `apps/tenant/src/components/ConflictResolver.tsx`

```typescript
import React, { useEffect, useState } from 'react'
import { getSyncManager } from '@/lib/syncManager'
import { ConflictInfo } from '@/lib/offlineStore'

export default function ConflictResolver() {
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([])
  const [selectedIdx, setSelectedIdx] = useState<number>(-1)

  useEffect(() => {
    const checkConflicts = async () => {
      const manager = getSyncManager()
      const all = await manager.getConflicts()
      setConflicts(all)
    }

    // Check initially
    checkConflicts()

    // Re-check after sync completes
    const handler = () => checkConflicts()
    window.addEventListener('offline:sync-completed', handler)

    return () => window.removeEventListener('offline:sync-completed', handler)
  }, [])

  if (conflicts.length === 0) return null

  const selected = selectedIdx >= 0 ? conflicts[selectedIdx] : null

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '1rem'
    }}>
      <div style={{
        background: 'white',
        borderRadius: 8,
        padding: '2rem',
        maxWidth: 900,
        maxHeight: '85vh',
        overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
      }}>
        <h2>⚠️ Conflictos de Sincronización</h2>
        <p style={{ color: '#666' }}>{conflicts.length} conflicto(s) detectado(s)</p>

        {!selected ? (
          <div style={{ marginTop: '1rem' }}>
            {conflicts.map((c, idx) => (
              <div
                key={`${c.entity}:${c.id}`}
                onClick={() => setSelectedIdx(idx)}
                style={{
                  padding: '1rem',
                  border: '1px solid #ddd',
                  borderRadius: 4,
                  marginBottom: '0.5rem',
                  cursor: 'pointer',
                  background: '#f9f9f9',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#f0f0f0'}
                onMouseLeave={(e) => e.currentTarget.style.background = '#f9f9f9'}
              >
                <strong>{c.entity}</strong>: {c.id}
                <br />
                <small style={{ color: '#999' }}>
                  Local v{c.localVersion} vs Servidor v{c.remoteVersion}
                </small>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ marginTop: '1rem' }}>
            <h3>{selected.entity}: {selected.id}</h3>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '1.5rem',
              marginY: '1.5rem'
            }}>
              <div style={{
                border: '2px solid #4CAF50',
                borderRadius: 4,
                padding: '1rem',
                background: '#f1f8f4'
              }}>
                <h4 style={{ color: '#2e7d32', margin: '0 0 0.5rem' }}>
                  📱 Versión Local (v{selected.localVersion})
                </h4>
                <pre style={{
                  fontSize: 12,
                  maxHeight: 300,
                  overflow: 'auto',
                  background: 'white',
                  padding: '0.5rem',
                  borderRadius: 2,
                  margin: 0
                }}>
                  {JSON.stringify(selected.local, null, 2)}
                </pre>
              </div>

              <div style={{
                border: '2px solid #FF9800',
                borderRadius: 4,
                padding: '1rem',
                background: '#fff8f1'
              }}>
                <h4 style={{ color: '#e65100', margin: '0 0 0.5rem' }}>
                  🌐 Versión Servidor (v{selected.remoteVersion})
                </h4>
                <pre style={{
                  fontSize: 12,
                  maxHeight: 300,
                  overflow: 'auto',
                  background: 'white',
                  padding: '0.5rem',
                  borderRadius: 2,
                  margin: 0
                }}>
                  {JSON.stringify(selected.remote, null, 2)}
                </pre>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button
                onClick={async () => {
                  const manager = getSyncManager()
                  await manager.resolveConflict(selected.entity, selected.id, 'local')
                  setConflicts(c => c.filter((_, i) => i !== selectedIdx))
                  setSelectedIdx(-1)
                }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✅ Usar Cambios Locales
              </button>

              <button
                onClick={async () => {
                  const manager = getSyncManager()
                  await manager.resolveConflict(selected.entity, selected.id, 'remote', selected.remote)
                  setConflicts(c => c.filter((_, i) => i !== selectedIdx))
                  setSelectedIdx(-1)
                }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: '#FF9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✅ Usar Versión Servidor
              </button>

              <button
                onClick={() => setSelectedIdx(-1)}
                style={{
                  padding: '0.75rem 1.5rem',
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

---

## 8️⃣ Simple Offline Dashboard

```typescript
import React from 'react'
import useOffline from '@/hooks/useOffline'

export default function OfflineSyncDashboard() {
  const { isOnline, totalPending, syncStatus, syncing, syncNow } = useOffline()

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
      maxWidth: 320,
      zIndex: 1000
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
        {isOnline ? '🟢' : '🔴'} {isOnline ? 'Online' : 'Offline'}
      </div>

      {totalPending > 0 && (
        <>
          <div style={{ fontSize: 13, color: '#666', marginBottom: '0.5rem' }}>
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
              marginTop: '0.75rem',
              padding: '0.5rem',
              background: isOnline && !syncing ? '#007bff' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: isOnline && !syncing ? 'pointer' : 'default',
              fontSize: 12,
              fontWeight: 'bold'
            }}
          >
            {syncing ? '⏳ Sincronizando...' : '🔄 Sincronizar'}
          </button>
        </>
      )}
    </div>
  )
}
```

---

## 🚀 Quick Copy-Paste Checklist

```
□ 1. ProductsAdapter → modules/products/offlineSync.ts
□ 2. CustomersAdapter → modules/customers/offlineSync.ts
□ 3. App.tsx initialization
□ 4. Update POSView to use useOffline
□ 5. Update ProductsView to use useOffline
□ 6. Improved OfflineBanner
□ 7. ConflictResolver.tsx
□ 8. OfflineSyncDashboard (en App.tsx)
```

Cada template es independiente. Copia el que necesites y adapta imports/servicios a tu caso.

