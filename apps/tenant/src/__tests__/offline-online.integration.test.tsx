/**
 * Integration tests for offline/online functionality
 *
 * Tests the real offlineStore + syncManager pipeline using mocked idb-keyval
 * and mocked sync adapters. No ElectricSQL dependency.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Mock idb-keyval with an in-memory store
// ---------------------------------------------------------------------------
const memoryStore: Record<string, Map<IDBValidKey, unknown>> = {}

function getMemStore(storeName: string) {
  if (!memoryStore[storeName]) memoryStore[storeName] = new Map()
  return memoryStore[storeName]
}

vi.mock('idb-keyval', () => ({
  createStore: (_db: string, store: string) => store,
  get: vi.fn(async (key: IDBValidKey, store: string) => getMemStore(store).get(key)),
  set: vi.fn(async (key: IDBValidKey, value: unknown, store: string) => {
    getMemStore(store).set(key, value)
  }),
  del: vi.fn(async (key: IDBValidKey, store: string) => {
    getMemStore(store).delete(key)
  }),
  entries: vi.fn(async (store: string) => Array.from(getMemStore(store).entries())),
}))

// Mock indexedDB.open used by openDatabase()
vi.stubGlobal('indexedDB', {
  open: () => {
    const req: any = {}
    req.onerror = null
    req.onsuccess = null
    req.onupgradeneeded = null
    setTimeout(() => {
      if (req.onsuccess) req.onsuccess({ target: { result: { objectStoreNames: { contains: () => false }, createObjectStore: () => {} } } })
    }, 0)
    return req
  },
})

// ---------------------------------------------------------------------------
// Imports after mocks
// ---------------------------------------------------------------------------
import {
  initOfflineStore,
  storeEntity,
  getEntity,
  listEntities,
  markSynced,
  markFailed,
  markConflict,
  queueDeletion,
  getTotalPendingCount,
  getConflicts,
  clearAllOfflineData,
} from '../lib/offlineStore'
import {
  getSyncManager,
  resetSyncManager,
  initSyncEventListener,
  resetSyncListener,
  type SyncAdapter,
} from '../lib/syncManager'
import { isOfflineQueuedResponse, createOfflineTempId, isNetworkIssue, stripOfflineMeta } from '../lib/offlineHttp'

function simulateNetworkChange(online: boolean) {
  Object.defineProperty(navigator, 'onLine', { writable: true, value: online })
  window.dispatchEvent(new Event(online ? 'online' : 'offline'))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeAdapter(overrides: Partial<SyncAdapter> = {}): SyncAdapter {
  return {
    entity: 'product',
    canSyncOffline: true,
    fetchAll: vi.fn(async () => []),
    create: vi.fn(async (data) => ({ ...data, id: data.id ?? 'server-id' })),
    update: vi.fn(async (_id, data) => data),
    delete: vi.fn(async () => {}),
    getRemoteVersion: vi.fn(async () => 0),
    detectConflict: vi.fn(() => false),
    ...overrides,
  }
}

function clearMemoryStores() {
  Object.keys(memoryStore).forEach((k) => delete memoryStore[k])
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(async () => {
  clearMemoryStores()
  resetSyncManager()
  resetSyncListener()
  await initOfflineStore()
})

afterEach(() => {
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// offlineStore unit tests
// ---------------------------------------------------------------------------

describe('offlineStore', () => {
  it('stores and retrieves an entity', async () => {
    await storeEntity('product', 'p1', { name: 'Widget', price: 9.99 })
    const entity = await getEntity('product', 'p1')
    expect(entity).toBeDefined()
    expect(entity!.data.name).toBe('Widget')
    expect(entity!.syncStatus).toBe('pending')
    expect(entity!.localVersion).toBe(1)
  })

  it('increments localVersion on subsequent stores', async () => {
    await storeEntity('product', 'p1', { name: 'v1' })
    await storeEntity('product', 'p1', { name: 'v2' })
    const entity = await getEntity('product', 'p1')
    expect(entity!.localVersion).toBe(2)
    expect(entity!.data.name).toBe('v2')
  })

  it('markSynced does NOT increment localVersion', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' })
    const before = await getEntity('product', 'p1')
    await markSynced('product', 'p1', 5)
    const after = await getEntity('product', 'p1')
    expect(after!.syncStatus).toBe('synced')
    expect(after!.remoteVersion).toBe(5)
    expect(after!.localVersion).toBe(before!.localVersion) // must NOT change
  })

  it('markFailed sets status and error message', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' })
    await markFailed('product', 'p1', 'Server error 500')
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('failed')
    expect(entity!.serverError).toBe('Server error 500')
  })

  it('markConflict sets status to conflict', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' })
    await markConflict('product', 'p1')
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('conflict')
  })

  it('queueDeletion marks entity with _deleted flag', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' })
    await queueDeletion('product', 'p1', { name: 'Widget' })
    const entity = await getEntity('product', 'p1')
    expect(entity!.data._deleted).toBe(true)
    expect(entity!.data._op).toBe('delete')
    expect(entity!.syncStatus).toBe('pending')
  })

  it('listEntities filters by entity type', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' })
    await storeEntity('product', 'p2', { name: 'Gadget' })
    await storeEntity('customer', 'c1', { name: 'Alice' })
    const products = await listEntities('product')
    expect(products).toHaveLength(2)
    expect(products.every(p => p.entity === 'product')).toBe(true)
  })

  it('getTotalPendingCount counts pending and failed only', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' }, 'pending')
    await storeEntity('product', 'p2', { name: 'Gadget' }, 'failed')
    await storeEntity('product', 'p3', { name: 'Doohickey' }, 'synced')
    const count = await getTotalPendingCount()
    expect(count).toBe(2)
  })

  it('getConflicts returns only conflicted entities', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' }, 'conflict')
    await storeEntity('product', 'p2', { name: 'Gadget' }, 'pending')
    const conflicts = await getConflicts()
    expect(conflicts).toHaveLength(1)
    expect(conflicts[0].id).toBe('p1')
  })

  it('clearAllOfflineData wipes all entities', async () => {
    await storeEntity('product', 'p1', { name: 'Widget' })
    await storeEntity('customer', 'c1', { name: 'Alice' })
    await clearAllOfflineData()
    const products = await listEntities('product')
    const customers = await listEntities('customer')
    expect(products).toHaveLength(0)
    expect(customers).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// syncManager unit tests
// ---------------------------------------------------------------------------

describe('syncManager', () => {
  it('registers an adapter and reports adapter count', () => {
    const manager = getSyncManager()
    const adapter = makeAdapter()
    manager.registerAdapter(adapter)
    expect(manager.getAdapterCount()).toBe(1)
    expect(manager.hasAdapter('product')).toBe(true)
  })

  it('syncs a pending create operation', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'local-1', { id: 'local-1', name: 'Widget', _op: 'create' }, 'pending')
    await manager.syncEntity('product')

    expect(adapter.create).toHaveBeenCalledOnce()
    const entity = await getEntity('product', 'local-1')
    expect(entity!.syncStatus).toBe('synced')
  })

  it('syncs a pending update operation', async () => {
    const adapter = makeAdapter({ getRemoteVersion: vi.fn(async () => 1) })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    // remoteVersionOverride=1 means localVersion was synced at 1
    await storeEntity('product', 'p1', { id: 'p1', name: 'Updated', _op: 'update' }, 'pending', 1)
    await manager.syncEntity('product')

    expect(adapter.update).toHaveBeenCalledWith('p1', expect.objectContaining({ name: 'Updated' }))
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('synced')
  })

  it('syncs a pending delete operation', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await queueDeletion('product', 'p1', { id: 'p1', name: 'Widget' })
    await manager.syncEntity('product')

    expect(adapter.delete).toHaveBeenCalledWith('p1')
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('synced')
  })

  it('marks conflict when remote version is newer', async () => {
    const adapter = makeAdapter({ getRemoteVersion: vi.fn(async () => 10) })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    // localVersion=1, remoteVersion stored=1, but server is at 10
    await storeEntity('product', 'p1', { id: 'p1', name: 'Local edit', _op: 'update' }, 'pending', 1)
    const result = await manager.syncEntity('product')

    expect(result.conflicts).toBe(1)
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('conflict')
  })

  it('marks failed and schedules backoff on adapter error', async () => {
    const adapter = makeAdapter({
      create: vi.fn(async () => { throw new Error('Network timeout') }),
    })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', name: 'Widget', _op: 'create' }, 'pending')
    const result = await manager.syncEntity('product')

    expect(result.failed).toBe(1)
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('failed')
    expect(entity!.serverError).toBe('Network timeout')
  })

  it('respects backoff: skips item before nextAttemptAt', async () => {
    const adapter = makeAdapter({
      create: vi.fn(async () => { throw new Error('Fail') }),
    })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', _op: 'create' }, 'pending')

    // First attempt fails and sets nextAttemptAt in the future
    await manager.syncEntity('product')
    expect(adapter.create).toHaveBeenCalledTimes(1)

    // Second attempt should be skipped (backoff not elapsed)
    await manager.syncEntity('product')
    expect(adapter.create).toHaveBeenCalledTimes(1) // still 1
  })

  it('does not sync adapters with canSyncOffline=false', async () => {
    const adapter = makeAdapter({ canSyncOffline: false })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', _op: 'create' }, 'pending')
    await manager.syncAll()

    expect(adapter.create).not.toHaveBeenCalled()
  })

  it('dispatches offline:sync-complete after syncAll', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    const completeSpy = vi.fn()
    window.addEventListener('offline:sync-complete', completeSpy)

    await manager.syncAll()
    window.removeEventListener('offline:sync-complete', completeSpy)

    expect(completeSpy).toHaveBeenCalledOnce()
  })

  it('dispatches offline:sync-complete after syncEntity', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    const completeSpy = vi.fn()
    window.addEventListener('offline:sync-complete', completeSpy)

    await manager.syncEntity('product')
    window.removeEventListener('offline:sync-complete', completeSpy)

    expect(completeSpy).toHaveBeenCalledOnce()
  })

  it('resolves conflict with local: pushes to server', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', name: 'Local' }, 'conflict')
    await manager.resolveConflict('product', 'p1', 'local')

    expect(adapter.update).toHaveBeenCalledWith('p1', expect.objectContaining({ name: 'Local' }))
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('synced')
  })

  it('resolves conflict with remote: marks synced without pushing', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', name: 'Local' }, 'conflict')
    await manager.resolveConflict('product', 'p1', 'remote', { id: 'p1', name: 'Remote' })

    expect(adapter.update).not.toHaveBeenCalled()
    const entity = await getEntity('product', 'p1')
    expect(entity!.syncStatus).toBe('synced')
  })
})

// ---------------------------------------------------------------------------
// initSyncEventListener — guard against double registration
// ---------------------------------------------------------------------------

describe('initSyncEventListener', () => {
  it('registers listener once even if called multiple times', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', _op: 'create' }, 'pending')

    initSyncEventListener()
    initSyncEventListener() // second call must be no-op

    window.dispatchEvent(new CustomEvent('offline:sync-requested'))

    // Give the async handler time to complete
    await new Promise(r => setTimeout(r, 50))

    // create should be called exactly once, not twice
    expect(adapter.create).toHaveBeenCalledTimes(1)
  })
})

// ---------------------------------------------------------------------------
// Offline/Online integration scenarios
// ---------------------------------------------------------------------------

describe('Offline/Online Integration', () => {
  it('queues changes offline and syncs them when online', async () => {
    const adapter = makeAdapter()
    const manager = getSyncManager()
    manager.registerAdapter(adapter)
    initSyncEventListener()

    // Go offline and create two products
    simulateNetworkChange(false)
    await storeEntity('product', 'p1', { id: 'p1', name: 'Widget', _op: 'create' }, 'pending')
    await storeEntity('product', 'p2', { id: 'p2', name: 'Gadget', _op: 'create' }, 'pending')

    expect(await getTotalPendingCount()).toBe(2)

    // Come back online — fires the sync-requested event
    simulateNetworkChange(true)
    window.dispatchEvent(new CustomEvent('offline:sync-requested'))

    await new Promise(r => setTimeout(r, 50))

    expect(adapter.create).toHaveBeenCalledTimes(2)
    expect(await getTotalPendingCount()).toBe(0)
  })

  it('handles create → conflict → resolve flow end to end', async () => {
    // Item was created locally at remoteVersion=0, but server already has remoteVersion=3
    const adapter = makeAdapter({ getRemoteVersion: vi.fn(async () => 3) })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', name: 'Local edit', _op: 'update' }, 'pending', 0)

    // Sync detects conflict
    const result = await manager.syncEntity('product')
    expect(result.conflicts).toBe(1)

    const conflicts = await getConflicts()
    expect(conflicts).toHaveLength(1)

    // User resolves with local version
    await manager.resolveConflict('product', 'p1', 'local')
    expect(adapter.update).toHaveBeenCalledWith('p1', expect.objectContaining({ name: 'Local edit' }))
    expect((await getConflicts())).toHaveLength(0)
  })

  it('retries failed item on subsequent sync if backoff has elapsed', async () => {
    vi.useFakeTimers()

    const createFn = vi.fn()
      .mockRejectedValueOnce(new Error('Transient error'))
      .mockResolvedValueOnce({ id: 'p1' })

    const adapter = makeAdapter({ create: createFn })
    const manager = getSyncManager()
    manager.registerAdapter(adapter)

    await storeEntity('product', 'p1', { id: 'p1', _op: 'create' }, 'pending')

    // First attempt — fails
    await manager.syncEntity('product')
    expect(createFn).toHaveBeenCalledTimes(1)
    expect((await getEntity('product', 'p1'))!.syncStatus).toBe('failed')

    // Advance past backoff (baseDelay * 2^0 = 1000ms)
    vi.advanceTimersByTime(2000)

    // Second attempt — succeeds
    await manager.syncEntity('product')
    expect(createFn).toHaveBeenCalledTimes(2)
    expect((await getEntity('product', 'p1'))!.syncStatus).toBe('synced')

    vi.useRealTimers()
  })
})

// ---------------------------------------------------------------------------
// offlineHttp helpers
// ---------------------------------------------------------------------------

describe('offlineHttp helpers', () => {
  it('isOfflineQueuedResponse detects 202 + queued body', () => {
    expect(isOfflineQueuedResponse({ status: 202, data: { queued: true }, headers: {} })).toBe(true)
  })

  it('isOfflineQueuedResponse detects 202 + X-Offline-Queued header', () => {
    expect(isOfflineQueuedResponse({ status: 202, data: {}, headers: { 'x-offline-queued': '1' } })).toBe(true)
  })

  it('isOfflineQueuedResponse rejects non-202 status', () => {
    expect(isOfflineQueuedResponse({ status: 200, data: { queued: true }, headers: {} })).toBe(false)
  })

  it('createOfflineTempId returns prefixed unique string', () => {
    const id1 = createOfflineTempId('product')
    const id2 = createOfflineTempId('product')
    expect(id1.startsWith('product-')).toBe(true)
    expect(id1).not.toBe(id2)
  })

  it('isNetworkIssue detects ERR_NETWORK code', () => {
    expect(isNetworkIssue({ code: 'ERR_NETWORK', message: '' })).toBe(true)
  })

  it('isNetworkIssue detects "failed to fetch" message', () => {
    expect(isNetworkIssue({ code: '', message: 'Failed to fetch' })).toBe(true)
  })

  it('stripOfflineMeta removes underscore-prefixed keys', () => {
    const cleaned = stripOfflineMeta({ name: 'Widget', _op: 'create', _deleted: false, price: 9.99 })
    expect(cleaned).toEqual({ name: 'Widget', price: 9.99 })
  })
})
