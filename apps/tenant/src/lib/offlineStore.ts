/**
 * OfflineStore - Central offline data management using IndexedDB
 * 
 * Handles CRUD operations for offline-enabled entities:
 * - products, customers, sales, receipts, etc.
 * Tracks sync status and detects conflicts.
 */

import { createStore, get, set, del, entries } from 'idb-keyval'

export type EntityType = 'product' | 'customer' | 'sale' | 'receipt' | 'purchase' | 'shift' | 'invoice'
export type SyncStatus = 'pending' | 'synced' | 'conflict' | 'failed'

export interface StoredEntity {
  id: string
  entity: EntityType
  data: any
  syncStatus: SyncStatus
  localVersion: number
  remoteVersion: number
  lastModified: number // timestamp
  serverError?: string
}

export interface SyncMetadata {
  entity: EntityType
  lastSync: number
  pendingCount: number
}

const DB_NAME = 'gestiqcloud-offline'
const STORE_NAME = 'offline-store'
const METADATA_STORE = 'offline-metadata'

let entityStore: ReturnType<typeof createStore> | null = null
let metadataStore: ReturnType<typeof createStore> | null = null
let dbInitialized = false

/**
 * Initialize IndexedDB with proper store creation
 * Uses low-level IDB API to ensure stores are created correctly
 */
async function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      // Create stores if they don't exist
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'key' })
      }
      if (!db.objectStoreNames.contains(METADATA_STORE)) {
        db.createObjectStore(METADATA_STORE, { keyPath: 'key' })
      }
    }
  })
}

export async function initOfflineStore() {
  try {
    if (dbInitialized) return
    
    // Ensure database exists and stores are created
    await openDatabase()
    
    // Now create idb-keyval stores
    entityStore = createStore(DB_NAME, STORE_NAME)
    metadataStore = createStore(DB_NAME, METADATA_STORE)
    dbInitialized = true
    
    console.log('[offline] OfflineStore initialized')
  } catch (error) {
    console.error('[offline] Failed to initialize OfflineStore:', error)
    // Don't throw - allow app to continue without offline support
    dbInitialized = true
  }
}

async function getStore() {
  if (!entityStore) {
    await initOfflineStore()
  }
  return entityStore!
}

async function getMetadataStore() {
  if (!metadataStore) {
    await initOfflineStore()
  }
  return metadataStore!
}

// =============================================================================
// Entity CRUD
// =============================================================================

export async function storeEntity(
  entity: EntityType,
  id: string,
  data: any,
  syncStatus: SyncStatus = 'pending',
  remoteVersionOverride?: number
): Promise<void> {
  const store = await getStore()
  const key = `${entity}:${id}`
  const previous = await getEntity(entity, id)
  
  const stored: StoredEntity = {
    id,
    entity,
    data,
    syncStatus,
    localVersion: (previous?.localVersion ?? 0) + 1,
    remoteVersion: remoteVersionOverride ?? previous?.remoteVersion ?? 0,
    lastModified: Date.now(),
  }
  
  await set(key, stored, store)
  await updateMetadata(entity)
}

export async function getEntity(entity: EntityType, id: string): Promise<StoredEntity | undefined> {
  const store = await getStore()
  const key = `${entity}:${id}`
  return get<StoredEntity>(key, store)
}

export async function deleteEntity(entity: EntityType, id: string): Promise<void> {
  const store = await getStore()
  const key = `${entity}:${id}`
  await del(key, store)
  await updateMetadata(entity)
}

export async function listEntities(entity: EntityType): Promise<StoredEntity[]> {
  const store = await getStore()
  const allEntries = await entries<StoredEntity>(store)
  return allEntries
    .filter(([key]) => key.toString().startsWith(`${entity}:`))
    .map(([_, value]) => value)
}

// =============================================================================
// Sync Status Management
// =============================================================================

export async function markSynced(entity: EntityType, id: string, remoteVersion?: number): Promise<void> {
  const stored = await getEntity(entity, id)
  if (!stored) return

  stored.syncStatus = 'synced'
  if (remoteVersion !== undefined) {
    stored.remoteVersion = remoteVersion
  }
  
  await storeEntity(entity, id, stored.data, 'synced')
}

export async function markFailed(entity: EntityType, id: string, error?: string): Promise<void> {
  const stored = await getEntity(entity, id)
  if (!stored) return

  stored.syncStatus = 'failed'
  stored.serverError = error
  
  const store = await getStore()
  const key = `${entity}:${id}`
  await set(key, stored, store)
  await updateMetadata(entity)
}

export async function markConflict(entity: EntityType, id: string): Promise<void> {
  const stored = await getEntity(entity, id)
  if (!stored) return

  stored.syncStatus = 'conflict'
  
  const store = await getStore()
  const key = `${entity}:${id}`
  await set(key, stored, store)
  await updateMetadata(entity)
}

// =============================================================================
// Metadata & Statistics
// =============================================================================

async function updateMetadata(entity: EntityType): Promise<void> {
  const items = await listEntities(entity)
  const pending = items.filter(i => i.syncStatus === 'pending' || i.syncStatus === 'failed').length
  
  const metadata: SyncMetadata = {
    entity,
    lastSync: items.some(i => i.syncStatus === 'synced') 
      ? Math.max(...items.filter(i => i.syncStatus === 'synced').map(i => i.lastModified)) 
      : 0,
    pendingCount: pending,
  }
  
  const metaStore = await getMetadataStore()
  await set(entity, metadata, metaStore)
}

export async function getMetadata(entity: EntityType): Promise<SyncMetadata | undefined> {
  const metaStore = await getMetadataStore()
  return get<SyncMetadata>(entity, metaStore)
}

export async function getAllMetadata(): Promise<Record<EntityType, SyncMetadata>> {
  const metaStore = await getMetadataStore()
  const allEntries = await entries<SyncMetadata>(metaStore)
  
  const result: any = {}
  allEntries.forEach(([key, value]) => {
    result[key as EntityType] = value
  })
  return result
}

export async function getTotalPendingCount(): Promise<number> {
  const metadata = await getAllMetadata()
  return Object.values(metadata).reduce((sum, m) => sum + m.pendingCount, 0)
}

export async function getStatusCounts(): Promise<Record<SyncStatus, number>> {
  const stats = await getStorageStats()
  return stats.byStatus
}

// =============================================================================
// Batch Operations
// =============================================================================

export async function syncBatch(entity: EntityType, items: Array<{ id: string; data: any }>): Promise<void> {
  for (const item of items) {
    await storeEntity(entity, item.id, item.data, 'pending')
  }
}

export async function clearEntity(entity: EntityType): Promise<void> {
  const items = await listEntities(entity)
  for (const item of items) {
    await deleteEntity(entity, item.id)
  }
}

/**
 * Mark an entity for deletion (soft-delete) to be processed by the sync manager.
 */
export async function queueDeletion(entity: EntityType, id: string, data?: any): Promise<void> {
  await storeEntity(entity, id, { ...(data || {}), _deleted: true, _op: 'delete' }, 'pending')
}

// =============================================================================
// Conflict Detection
// =============================================================================

export interface ConflictInfo {
  id: string
  entity: EntityType
  local: any
  remote: any
  localVersion: number
  remoteVersion: number
  changedFields: string[]
}

export async function getConflicts(): Promise<ConflictInfo[]> {
  const store = await getStore()
  const allEntries = await entries<StoredEntity>(store)
  
  return allEntries
    .filter(([_, item]) => item.syncStatus === 'conflict')
    .map(([_, item]) => ({
      id: item.id,
      entity: item.entity,
      local: item.data,
      remote: {}, // Will be populated by sync manager
      localVersion: item.localVersion,
      remoteVersion: item.remoteVersion,
      changedFields: [],
    }))
}

export async function hasConflicts(): Promise<boolean> {
  const conflicts = await getConflicts()
  return conflicts.length > 0
}

// =============================================================================
// Utility Functions
// =============================================================================

export async function clearAllOfflineData(): Promise<void> {
  const store = await getStore()
  const metaStore = await getMetadataStore()
  
  const allEntries = await entries(store)
  for (const [key] of allEntries) {
    await del(key, store)
  }
  
  const allMetadata = await entries(metaStore)
  for (const [key] of allMetadata) {
    await del(key, metaStore)
  }
  
  console.log('[offline] All offline data cleared')
}

export async function getStorageStats(): Promise<{
  totalEntities: number
  byEntity: Record<EntityType, number>
  byStatus: Record<SyncStatus, number>
}> {
  const store = await getStore()
  const allEntries = await entries<StoredEntity>(store)
  
  const byEntity: any = {}
  const byStatus: any = {}
  
  allEntries.forEach(([_, item]) => {
    byEntity[item.entity] = (byEntity[item.entity] || 0) + 1
    byStatus[item.syncStatus] = (byStatus[item.syncStatus] || 0) + 1
  })
  
  return {
    totalEntities: allEntries.length,
    byEntity,
    byStatus: byStatus as Record<SyncStatus, number>,
  }
}

export async function debugDump(entity?: EntityType): Promise<void> {
  if (entity) {
    const items = await listEntities(entity)
    console.group(`[offline] Store - ${entity}`)
    console.table(items)
    console.groupEnd()
  } else {
    const stats = await getStorageStats()
    console.log('[offline] Store statistics:', stats)
  }
}
