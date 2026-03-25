/**
 * Purchases Offline Sync Adapter
 *
 * Synchronizes purchases (compras) with offline support.
 * - Create, update, soft-delete
 * - Conflict detection on total/status/line items
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listCompras, getCompra, createCompra, updateCompra, removeCompra } from './services'
import type { Compra } from './services'

export const PurchasesAdapter: SyncAdapter = {
  entity: 'purchase',
  canSyncOffline: true,

  async fetchAll(): Promise<Compra[]> {
    try {
      return await listCompras()
    } catch (error) {
      console.error('Failed to fetch purchases:', error)
      return []
    }
  },

  async create(data: any): Promise<Compra> {
    const compra = await createCompra(data)
    const remoteVersion = (compra as any)?.updated_at ? new Date((compra as any).updated_at as string).getTime() : Date.now()
    await storeEntity('purchase', String(compra.id), compra, 'synced', remoteVersion)
    return compra
  },

  async update(id: string, data: any): Promise<Compra> {
    const compra = await updateCompra(id, data)
    const remoteVersion = (compra as any)?.updated_at ? new Date((compra as any).updated_at as string).getTime() : Date.now()
    await storeEntity('purchase', String(id), compra, 'synced', remoteVersion)
    return compra
  },

  async delete(id: string): Promise<void> {
    try {
      await removeCompra(id)
      await storeEntity('purchase', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('purchase', id)
      console.warn('[offline] Queued purchase deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const compra = await getCompra(id)
      const timestamp = (compra as any)?.updated_at ?? (compra as any)?.created_at
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

export function registerPurchasesSyncAdapter() {
  getSyncManager().registerAdapter(PurchasesAdapter)
}

export async function getPurchasesWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('purchase')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
