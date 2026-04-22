/**
 * Purchases Offline Sync Adapter
 *
 * Synchronizes purchases with offline support.
 * - Create, update, soft-delete
 * - Conflict detection on total/status/line items
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listPurchases, getPurchase, createPurchase, updatePurchase, removePurchase } from './services'
import type { Purchase } from './services'

export const PurchasesAdapter: SyncAdapter = {
  entity: 'purchase',
  canSyncOffline: true,

  async fetchAll(): Promise<Purchase[]> {
    try {
      return await listPurchases()
    } catch (error) {
      console.error('Failed to fetch purchases:', error)
      return []
    }
  },

  async create(data: any): Promise<Purchase> {
    const purchase = await createPurchase(data)
    const remoteVersion = (purchase as any)?.updated_at ? new Date((purchase as any).updated_at as string).getTime() : Date.now()
    await storeEntity('purchase', String(purchase.id), purchase, 'synced', remoteVersion)
    return purchase
  },

  async update(id: string, data: any): Promise<Purchase> {
    const purchase = await updatePurchase(id, data)
    const remoteVersion = (purchase as any)?.updated_at ? new Date((purchase as any).updated_at as string).getTime() : Date.now()
    await storeEntity('purchase', String(id), purchase, 'synced', remoteVersion)
    return purchase
  },

  async delete(id: string): Promise<void> {
    try {
      await removePurchase(id)
      await storeEntity('purchase', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('purchase', id)
      console.warn('[offline] Queued purchase deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const purchase = await getPurchase(id)
      const timestamp = (purchase as any)?.updated_at ?? (purchase as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    const itemsDiffer = JSON.stringify(local.items || local.lines || []) !== JSON.stringify(remote.items || remote.lines || [])
    return itemsDiffer ||
           local.total !== remote.total ||
           local.status !== remote.status
  }
}

export function registerPurchasesSyncAdapter() {
  getSyncManager().registerAdapter(PurchasesAdapter)
}

export async function getPurchasesWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('purchase')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
