/**
 * Customers Offline Sync Adapter
 *
 * Synchronizes customers with offline support:
 * - Create, update, delete
 * - Conflict detection on core contact fields
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listClientes, getCliente, createCliente, updateCliente, removeCliente } from './services'

export const CustomersAdapter: SyncAdapter = {
  entity: 'customer',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      return await listClientes()
    } catch (error) {
      console.error('Failed to fetch customers:', error)
      return []
    }
  },

  async create(data: any): Promise<any> {
    const customer = await createCliente(data)
    const remoteVersion = (customer as any)?.updated_at ? new Date((customer as any).updated_at as string).getTime() : Date.now()
    await storeEntity('customer', String(customer.id), customer, 'synced', remoteVersion)
    return customer
  },

  async update(id: string, data: any): Promise<any> {
    const customer = await updateCliente(id, data)
    const remoteVersion = (customer as any)?.updated_at ? new Date((customer as any).updated_at as string).getTime() : Date.now()
    await storeEntity('customer', String(id), customer, 'synced', remoteVersion)
    return customer
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
      const customer = await getCliente(id)
      const timestamp = (customer as any)?.updated_at ?? (customer as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false

    return local.email !== remote.email ||
           local.phone !== remote.phone ||
           local.name !== remote.name ||
           local.identificacion !== remote.identificacion ||
           local.tax_id !== remote.tax_id
  }
}

export function registerCustomersSyncAdapter() {
  getSyncManager().registerAdapter(CustomersAdapter)
  console.log('[offline] Customers sync adapter registered')
}

/**
 * Cache customers locally for offline access
 */
export async function syncCustomersToOffline(customers: any[]) {
  for (const customer of customers) {
    const remoteVersion = (customer as any)?.updated_at ? new Date((customer as any).updated_at as string).getTime() : Date.now()
    await storeEntity('customer', customer.id, customer, 'synced', remoteVersion)
  }
}

/**
 * Get locally cached customers
 */
export async function getOfflineCustomers(): Promise<any[]> {
  const items = await listEntities('customer')
  return items.map(i => i.data)
}

/**
 * Get customers with pending changes
 */
export async function getCustomersWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('customer')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
