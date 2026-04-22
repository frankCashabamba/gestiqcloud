/**
 * Billing/Invoices Offline Sync Adapter
 *
 * Synchronizes invoices with offline support.
 * - Create, update, soft-delete
 * - Conflict detection on total/status/line items
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listInvoices, getInvoice, createInvoice, updateInvoice, deleteInvoice } from './services'
import type { Invoice } from './services'

export const InvoicesAdapter: SyncAdapter = {
  entity: 'invoice',
  canSyncOffline: true,

  async fetchAll(): Promise<Invoice[]> {
    try {
      return await listInvoices()
    } catch (error) {
      console.error('Failed to fetch invoices:', error)
      return []
    }
  },

  async create(data: any): Promise<Invoice> {
    const invoice = await createInvoice(data)
    const remoteVersion = (invoice as any)?.updated_at ? new Date((invoice as any).updated_at as string).getTime() : Date.now()
    await storeEntity('invoice', String(invoice.id), invoice, 'synced', remoteVersion)
    return invoice
  },

  async update(id: string, data: any): Promise<Invoice> {
    const invoice = await updateInvoice(id, data)
    const remoteVersion = (invoice as any)?.updated_at ? new Date((invoice as any).updated_at as string).getTime() : Date.now()
    await storeEntity('invoice', String(id), invoice, 'synced', remoteVersion)
    return invoice
  },

  async delete(id: string): Promise<void> {
    try {
      await deleteInvoice(id)
      await storeEntity('invoice', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('invoice', id)
      console.warn('[offline] Queued invoice deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const invoice = await getInvoice(id)
      const timestamp = (invoice as any)?.updated_at ?? (invoice as any)?.created_at
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
           local.status !== remote.status ||
           local.status !== remote.status
  }
}

export function registerInvoicesSyncAdapter() {
  getSyncManager().registerAdapter(InvoicesAdapter)
}

export async function getInvoicesWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('invoice')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
