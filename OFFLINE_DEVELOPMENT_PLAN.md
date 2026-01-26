# Plan de Desarrollo: Soporte Offline Robusto

## Estado Actual ✅/⚠️
- ✅ Service Worker + Workbox (caching básico)
- ✅ Request Queue en IndexedDB (auto-retry)
- ✅ UI feedback (banners)
- ⚠️ Sync limitado a POS únicamente
- ⚠️ No hay sincronización de productos, clientes, etc.
- ❌ Conflict resolution no implementado
- ❌ ElectricSQL deshabilitado

---

## Fase 1: Infraestructura Offline (1-2 días)

### 1.1 Crear `OfflineStore` central (IndexedDB)
**Archivo:** `apps/tenant/src/lib/offlineStore.ts`

Funcionalidades:
- Abstracción sobre IndexedDB para CRUD offline
- Almacenar: productos, clientes, ventas, compras
- Timestamps de sincronización
- Estado de sincronización por tabla

```typescript
interface StoredEntity {
  id: string
  entity: 'product' | 'customer' | 'sale' | 'receipt'
  data: any
  syncStatus: 'pending' | 'synced' | 'conflict'
  localVersion: number
  remoteVersion: number
  lastModified: number
}
```

### 1.2 Crear `useOffline` Hook global
**Archivo:** `apps/tenant/src/hooks/useOffline.ts`

Reemplazar `useOfflineSync` (POS-only) con hook universal:
```typescript
interface UseOfflineReturn {
  isOnline: boolean
  pendingCount: number
  syncStatus: Record<'products' | 'customers' | 'sales', number>
  syncNow: (entity?: string) => Promise<void>
  getLocalData: (entity: string, id: string) => Promise<any>
  queueChange: (entity: string, id: string, data: any) => Promise<void>
}
```

---

## Fase 2: Sincronización Multimodular (2-3 días)

### 2.1 Adapter Sync para cada módulo
Crear en cada módulo: `modules/{modulo}/offlineSync.ts`

**Ejemplos:**
- `modules/products/offlineSync.ts` - Sync de productos
- `modules/customers/offlineSync.ts` - Sync de clientes
- `modules/pos/offlineSync.ts` - Mejorar existente

```typescript
export interface SyncAdapter {
  entity: string
  canSyncOffline: boolean
  localStorageKey: string

  fetchAll(): Promise<any[]>
  create(data: any): Promise<any>
  update(id: string, data: any): Promise<any>
  delete(id: string): Promise<void>

  // Detectar conflictos
  detectConflict(local: any, remote: any): Conflict | null
}
```

### 2.2 Sync Manager
**Archivo:** `apps/tenant/src/lib/syncManager.ts`

```typescript
class SyncManager {
  private adapters: Map<string, SyncAdapter>

  registerAdapter(adapter: SyncAdapter)
  syncAll(): Promise<SyncResult>
  sync(entity: string): Promise<SyncResult>
  getConflicts(): Conflict[]
  resolveConflict(id: string, resolution: 'local' | 'remote'): Promise<void>
}
```

---

## Fase 3: Detección y Resolución de Conflictos (1-2 días)

### 3.1 Conflict Detection
**Archivo:** `apps/tenant/src/lib/conflictDetection.ts`

```typescript
interface Conflict {
  id: string
  entity: string
  local: any
  remote: any
  localModified: number
  remoteModified: number
  fields: string[] // Campos en conflicto
}

function detectConflict(local: any, remote: any): Conflict | null {
  // Comparar timestamps y campos
}
```

### 3.2 Conflict Resolution UI
**Archivo:** `apps/tenant/src/components/ConflictResolver.tsx`

Mostrar modal con:
- Diff lado a lado (local vs remoto)
- Opción: usar local / usar remoto / merge manual
- Historial de cambios

---

## Fase 4: Tests E2E (1 día)

### 4.1 Completar tests en `offline-online.integration.test.tsx`

Casos:
- ✅ Crear recibo offline, sincronizar online
- ✅ Modificar producto offline, resolver conflicto
- ✅ Múltiples cambios offline, sync masivo
- ✅ Conexión intermitente (offline/online/offline)
- ✅ Data consistency después de conflictos

### 4.2 Tests con Playwright
**Archivo:** `e2e/offline.spec.ts`

```typescript
test('POS workflow offline', async ({ browser, context }) => {
  // 1. Abrir app
  // 2. Simular offline (DevTools)
  // 3. Crear recibo
  // 4. Ir online
  // 5. Verificar sincronización
})
```

---

## Fase 5: Mejoras UX (1 día)

### 5.1 Dashboard de Sincronización
**Componente:** `OfflineSyncDashboard.tsx`

- Estado por módulo (productos: 5 pendientes, clientes: 2)
- Última sincronización
- Botón forzar sync
- Advertencia si hay conflictos

### 5.2 Mejorar Banners
- Mostrar % progreso de sync
- Detalles de qué se está sincronizando
- Opción de pausar/reanudar

---

## Priorización Recomendada

**MVP (Semana 1):**
1. OfflineStore + useOffline Hook
2. Sync para POS (mejorar existente)
3. Detectar conflictos básico

**Siguiente (Semana 2):**
4. Sync para Products + Customers
5. ConflictResolver UI
6. E2E tests

**Nice-to-have (Después):**
7. Sync para compras/ventas
8. Dashboard offline
9. ElectricSQL cuando esté estable

---

## Archivos a Crear/Modificar

```
apps/tenant/src/
├── lib/
│   ├── offlineStore.ts          [NEW]
│   ├── syncManager.ts           [NEW]
│   ├── conflictDetection.ts     [NEW]
│   └── electric.ts              [MODIFY]
├── hooks/
│   ├── useOffline.ts            [NEW - reemplazar useOfflineSync]
│   └── useSync.ts               [NEW - hook para sync UI]
├── components/
│   └── ConflictResolver.tsx     [NEW]
├── modules/
│   ├── products/
│   │   └── offlineSync.ts       [NEW]
│   ├── customers/
│   │   └── offlineSync.ts       [NEW]
│   ├── sales/
│   │   └── offlineSync.ts       [NEW]
│   └── pos/
│       ├── hooks/useOfflineSync.tsx [MODIFY - usar nuevo Hook]
│       └── offlineSync.ts       [NEW]
└── __tests__/
    ├── offline-online.integration.test.tsx [MODIFY - completar tests]
    └── syncManager.test.ts       [NEW]
```

---

## Dependencias a Verificar

```json
{
  "idb-keyval": "^6.x",        // Ya existe
  "workbox-core": "^7.x",      // Ya existe
  "deep-diff": "^1.x",         // Nuevo - para detectar conflictos
  "immer": "^10.x"             // Nuevo - para merges complejos (opcional)
}
```

---

## Checklist de Implementación

- [ ] OfflineStore creado y testeado
- [ ] useOffline Hook funcionando
- [ ] Sync Manager integrado
- [ ] Conflict detection básica
- [ ] ConflictResolver UI visible
- [ ] 3+ módulos con sync (POS, Products, Customers)
- [ ] E2E tests pasando
- [ ] Dashboard offline funcional
- [ ] Documentación actualizada

---

## Notas Importantes

1. **No reemplazar Service Worker** - continuar con Workbox para caché
2. **IDB sobre localStorage** - más storage, mejor performance
3. **ElectricSQL** - mantener como feature flag, habilitar después
4. **Versioning** - necesario para detectar conflictos
5. **Backoff exponencial** - ya implementado en SW, reutilizar
