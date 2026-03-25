/**
 * Productions Offline Sync Adapter
 *
 * Synchronizes production orders with offline support.
 * - Create, update, soft-delete
 * - Conflict detection on status/quantity
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listProductionOrders, getProductionOrder, createProductionOrder, updateProductionOrder, removeProductionOrder } from './services'
import type { ProductionOrder } from './services'

export const ProductionAdapter: SyncAdapter = {
  entity: 'production',
  canSyncOffline: true,

  async fetchAll(): Promise<ProductionOrder[]> {
    try {
      return await listProductionOrders()
    } catch (error) {
      console.error('Failed to fetch production orders:', error)
      return []
    }
  },

  async create(data: any): Promise<ProductionOrder> {
    const order = await createProductionOrder(data)
    const remoteVersion = (order as any)?.updated_at ? new Date((order as any).updated_at as string).getTime() : Date.now()
    await storeEntity('production', String(order.id), order, 'synced', remoteVersion)
    return order
  },

  async update(id: string, data: any): Promise<ProductionOrder> {
    const order = await updateProductionOrder(id, data)
    const remoteVersion = (order as any)?.updated_at ? new Date((order as any).updated_at as string).getTime() : Date.now()
    await storeEntity('production', String(id), order, 'synced', remoteVersion)
    return order
  },

  async delete(id: string): Promise<void> {
    try {
      await removeProductionOrder(id)
      await storeEntity('production', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('production', id)
      console.warn('[offline] Queued production order deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const order = await getProductionOrder(id)
      const timestamp = (order as any)?.updated_at ?? (order as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.status !== remote.status ||
           local.quantity !== remote.quantity ||
           local.product_id !== remote.product_id
  }
}

export function registerProductionSyncAdapter() {
  getSyncManager().registerAdapter(ProductionAdapter)
}

export async function getProductionWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('production')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
