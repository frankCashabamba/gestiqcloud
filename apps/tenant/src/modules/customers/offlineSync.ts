/**
 * Customers Offline Sync Adapter
 *
 * Synchronizes customers (clientes) with offline support.
 * - Full CRUD with conflict detection
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listClientes, getCliente, createCliente, updateCliente, removeCliente } from './services'
import type { Cliente } from './services'

export const CustomersAdapter: SyncAdapter = {
  entity: 'customer',
  canSyncOffline: true,

  async fetchAll(): Promise<Cliente[]> {
    try {
      return await listClientes()
    } catch (error) {
      console.error('Failed to fetch customers:', error)
      return []
    }
  },

  async create(data: any): Promise<Cliente> {
    const cliente = await createCliente(data)
    const remoteVersion = (cliente as any)?.updated_at ? new Date((cliente as any).updated_at as string).getTime() : Date.now()
    await storeEntity('customer', String(cliente.id), cliente, 'synced', remoteVersion)
    return cliente
  },

  async update(id: string, data: any): Promise<Cliente> {
    const cliente = await updateCliente(id, data)
    const remoteVersion = (cliente as any)?.updated_at ? new Date((cliente as any).updated_at as string).getTime() : Date.now()
    await storeEntity('customer', String(id), cliente, 'synced', remoteVersion)
    return cliente
  },

  async delete(id: string): Promise<void> {
    try {
      await removeCliente(id)
      await storeEntity('customer', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('customer', id)
      console.warn('[offline] Queued customer deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const cliente = await getCliente(id)
      const timestamp = (cliente as any)?.updated_at ?? (cliente as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.nombre !== remote.nombre ||
           local.email !== remote.email ||
           local.telefono !== remote.telefono ||
           local.identificacion !== remote.identificacion
  }
}

export function registerCustomersSyncAdapter() {
  getSyncManager().registerAdapter(CustomersAdapter)
}

export async function getCustomersWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('customer')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
