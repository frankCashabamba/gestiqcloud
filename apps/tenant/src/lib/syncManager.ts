/**
 * SyncManager - Central synchronization orchestrator
 *
 * Coordinates syncing across multiple entities, handles conflicts,
 * and manages retry logic.
 */

import {
  EntityType,
  StoredEntity,
  listEntities,
  markSynced,
  markFailed,
  markConflict,
  getEntity,
  getConflicts,
  ConflictInfo
} from './offlineStore'

export interface SyncAdapter {
  entity: EntityType
  canSyncOffline: boolean

  // Fetch all remote data for this entity
  fetchAll(): Promise<any[]>

  // Sync operations
  create(data: any): Promise<any>
  update(id: string, data: any): Promise<any>
  delete(id: string): Promise<void>

  // Get remote version for conflict detection
  getRemoteVersion(id: string): Promise<number>

  // Detect if local and remote differ
  detectConflict(local: any, remote: any): boolean
}

export interface SyncResult {
  entity: EntityType
  synced: number
  failed: number
  conflicts: number
  duration: number
}

class SyncManager {
  private adapters: Map<string, SyncAdapter> = new Map()
  private retryQueue: Map<string, number> = new Map() // key -> attempts
  private maxRetries = 3
  private baseDelay = 1000 // ms

  registerAdapter(adapter: SyncAdapter) {
    this.adapters.set(adapter.entity, adapter)
    console.log(`[offline] Registered sync adapter for: ${adapter.entity}`)
  }

  async syncAll(): Promise<SyncResult[]> {
    const results: SyncResult[] = []

    for (const [_, adapter] of this.adapters) {
      if (!adapter.canSyncOffline) continue

      try {
        const result = await this.syncEntity(adapter.entity)
        results.push(result)
      } catch (error) {
        console.error(`[offline] Sync failed for ${adapter.entity}:`, error)
        results.push({
          entity: adapter.entity,
          synced: 0,
          failed: 0,
          conflicts: 0,
          duration: 0,
        })
      }
    }

    return results
  }

  async syncEntity(entity: EntityType): Promise<SyncResult> {
    const startTime = Date.now()
    const adapter = this.adapters.get(entity)

    if (!adapter || !adapter.canSyncOffline) {
      throw new Error(`No sync adapter registered for ${entity}`)
    }

    let synced = 0
    let failed = 0
    let conflicts = 0

    const pending = await listEntities(entity)
    const pendingItems = pending.filter(i => i.syncStatus === 'pending' || i.syncStatus === 'failed')

    console.log(`[offline] Syncing ${entity}: ${pendingItems.length} pending items`)

    for (const item of pendingItems) {
      try {
        const key = `${entity}:${item.id}`
        const attempts = this.retryQueue.get(key) || 0

        if (attempts >= this.maxRetries) {
          await markFailed(entity, item.id, 'Max retries exceeded')
          failed++
          continue
        }

        const op = item.data?._op as 'create' | 'update' | 'delete' | undefined
        const isDelete = op === 'delete' || item.data?._deleted === true
        const isCreate = op === 'create' || (!isDelete && item.remoteVersion === 0)
        const isUpdate = !isDelete && !isCreate

        // Check for conflicts only on updates
        if (isUpdate) {
          try {
            const remoteVersion = await adapter.getRemoteVersion(item.id)

            if (remoteVersion > item.remoteVersion) {
              console.warn(`[offline] Conflict detected for ${entity}:${item.id}`)
              await markConflict(entity, item.id)
              conflicts++
              continue
            }
          } catch {
            // Remote missing; treat as creatable
          }
        }

        if (isDelete) {
          await adapter.delete(item.id)
          await markSynced(entity, item.id, item.remoteVersion)
        } else if (isCreate) {
          await adapter.create(item.data)
          await markSynced(entity, item.id, Math.max(item.remoteVersion, 1))
        } else {
          await adapter.update(item.id, item.data)
          await markSynced(entity, item.id, item.remoteVersion + 1)
        }

        synced++
        this.retryQueue.delete(key)

      } catch (error) {
        console.error(`[offline] Sync failed for ${entity}:${item.id}:`, error)
        failed++

        const key = `${entity}:${item.id}`
        const attempts = (this.retryQueue.get(key) || 0) + 1
        this.retryQueue.set(key, attempts)

        // Schedule retry with exponential backoff
        const delay = Math.min(this.baseDelay * Math.pow(2, attempts - 1), 5 * 60 * 1000)
        await markFailed(entity, item.id, error instanceof Error ? error.message : 'Unknown error')
      }
    }

    const duration = Date.now() - startTime

    console.log(`[offline] Sync complete for ${entity}: ${synced} synced, ${failed} failed, ${conflicts} conflicts in ${duration}ms`)

    return {
      entity,
      synced,
      failed,
      conflicts,
      duration,
    }
  }

  async getConflicts(): Promise<ConflictInfo[]> {
    const conflicts = await getConflicts()

    // Enrich with remote data
    for (const conflict of conflicts) {
      const adapter = this.adapters.get(conflict.entity)
      if (adapter) {
        try {
          // Try to fetch remote data for comparison
          const remote = (await adapter.fetchAll()).find(r => r.id === conflict.id)
          if (remote) {
            conflict.remote = remote
          }
        } catch (error) {
          console.error(`Failed to fetch remote for conflict ${conflict.id}:`, error)
        }
      }
    }

    return conflicts
  }

  async resolveConflict(entity: EntityType, id: string, resolution: 'local' | 'remote', remoteData?: any): Promise<void> {
    const item = await getEntity(entity, id)
    if (!item) return

    const adapter = this.adapters.get(entity)
    if (!adapter) throw new Error(`No sync adapter for ${entity}`)

    try {
      if (resolution === 'local') {
        // Keep local, push to server
        await adapter.update(id, item.data)
        await markSynced(entity, id)
      } else if (resolution === 'remote' && remoteData) {
        // Keep remote, update local
        await markSynced(entity, id)
        // Note: UI should refetch data after this
      }

      console.log(`[offline] Conflict resolved for ${entity}:${id} (${resolution})`)
    } catch (error) {
      console.error(`Failed to resolve conflict:`, error)
      throw error
    }
  }

  hasAdapter(entity: EntityType): boolean {
    return this.adapters.has(entity)
  }

  getAdapterCount(): number {
    return this.adapters.size
  }
}

// Singleton instance
let syncManagerInstance: SyncManager | null = null

export function getSyncManager(): SyncManager {
  if (!syncManagerInstance) {
    syncManagerInstance = new SyncManager()
  }
  return syncManagerInstance
}

export function resetSyncManager() {
  syncManagerInstance = null
}

// Global event listener for sync requests
export function initSyncEventListener() {
  window.addEventListener('offline:sync-requested', async (event: Event) => {
    const customEvent = event as CustomEvent
    const entity = customEvent.detail?.entity

    const manager = getSyncManager()

    try {
      if (entity) {
        await manager.syncEntity(entity)
      } else {
        await manager.syncAll()
      }
    } catch (error) {
      console.error('Sync failed:', error)
    }
  })
}
