/**
 * Sales Offline Sync Adapter
 *
 * Synchronizes sales/orders with offline support.
 * - Create and update (until invoiced)
 * - Soft delete if supported by API
 * - Conflict detection on items/totals/status
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listVentas, getVenta, createVenta, updateVenta, removeVenta } from './services'

export const SalesAdapter: SyncAdapter = {
  entity: 'sale',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      return await listVentas()
    } catch (error) {
      console.error('Failed to fetch sales:', error)
      return []
    }
  },

  async create(data: any): Promise<any> {
    const sale = await createVenta(data)
    const remoteVersion = (sale as any)?.updated_at ? new Date((sale as any).updated_at as string).getTime() : Date.now()
    await storeEntity('sale', sale.id, sale, 'synced', remoteVersion)
    return sale
  },

  async update(id: string, data: any): Promise<any> {
    const sale = await updateVenta(id, data)
    const remoteVersion = (sale as any)?.updated_at ? new Date((sale as any).updated_at as string).getTime() : Date.now()
    await storeEntity('sale', id, sale, 'synced', remoteVersion)
    return sale
  },

  async delete(id: string): Promise<void> {
    try {
      await removeVenta(id)
      await storeEntity('sale', id, { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('sale', id)
      console.warn('[offline] Queued sale deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const sale = await getVenta(id)
      const timestamp = (sale as any)?.updated_at ?? (sale as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false

    const itemsDiffer = JSON.stringify(local.items || local.lineas || []) !== JSON.stringify(remote.items || remote.lineas || [])
    return itemsDiffer ||
           local.total !== remote.total ||
           local.estado !== remote.estado ||
           local.status !== remote.status
  }
}

export function registerSalesSyncAdapter() {
  getSyncManager().registerAdapter(SalesAdapter)
  console.log('[offline] Sales sync adapter registered')
}

/**
 * Get sales with pending changes
 */
export async function getSalesWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('sale')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
