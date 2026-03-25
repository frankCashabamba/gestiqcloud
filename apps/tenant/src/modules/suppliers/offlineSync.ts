/**
 * Suppliers Offline Sync Adapter
 *
 * Synchronizes suppliers (proveedores) with offline support.
 * - Full CRUD with conflict detection
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listProveedores, getProveedor, createProveedor, updateProveedor, removeProveedor } from './services'
import type { Proveedor } from './services'

export const SuppliersAdapter: SyncAdapter = {
  entity: 'supplier',
  canSyncOffline: true,

  async fetchAll(): Promise<Proveedor[]> {
    try {
      return await listProveedores()
    } catch (error) {
      console.error('Failed to fetch suppliers:', error)
      return []
    }
  },

  async create(data: any): Promise<Proveedor> {
    const proveedor = await createProveedor(data)
    const remoteVersion = (proveedor as any)?.updated_at ? new Date((proveedor as any).updated_at as string).getTime() : Date.now()
    await storeEntity('supplier', String(proveedor.id), proveedor, 'synced', remoteVersion)
    return proveedor
  },

  async update(id: string, data: any): Promise<Proveedor> {
    const proveedor = await updateProveedor(id, data)
    const remoteVersion = (proveedor as any)?.updated_at ? new Date((proveedor as any).updated_at as string).getTime() : Date.now()
    await storeEntity('supplier', String(id), proveedor, 'synced', remoteVersion)
    return proveedor
  },

  async delete(id: string): Promise<void> {
    try {
      await removeProveedor(id)
      await storeEntity('supplier', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('supplier', id)
      console.warn('[offline] Queued supplier deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const proveedor = await getProveedor(id)
      const timestamp = (proveedor as any)?.updated_at ?? (proveedor as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.nombre !== remote.nombre ||
           local.email !== remote.email ||
           local.ruc !== remote.ruc ||
           local.telefono !== remote.telefono
  }
}

export function registerSuppliersSyncAdapter() {
  getSyncManager().registerAdapter(SuppliersAdapter)
}

export async function getSuppliersWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('supplier')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
