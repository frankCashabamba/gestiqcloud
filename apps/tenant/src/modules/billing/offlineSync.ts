/**
 * Billing Offline Sync Adapter
 *
 * Reuses the global offline infrastructure to sync invoices.
 * Supports create/update/delete and conflict detection on totals/lines.
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import {
  storeEntity,
  queueDeletion,
  EntityType,
} from '@/lib/offlineStore'
import {
  listInvoices,
  getInvoice,
  createInvoice,
  updateInvoice,
  deleteInvoice,
  type InvoiceCreate,
  type Invoice,
} from './services'

const entity: EntityType = 'invoice'

function getVersion(inv: any): number {
  const ts = inv?.updated_at || inv?.fecha || inv?.fecha_emision || inv?.created_at
  const parsed = ts ? Date.parse(ts) : NaN
  return Number.isFinite(parsed) ? parsed : Date.now()
}

function linesSignature(inv: any) {
  return JSON.stringify(inv?.lineas || inv?.lines || [])
}

export const InvoiceAdapter: SyncAdapter = {
  entity,
  canSyncOffline: true,

  async fetchAll(): Promise<Invoice[]> {
    try {
      return await listInvoices()
    } catch (error) {
      console.error('[offline] Failed to fetch invoices:', error)
      return []
    }
  },

  async create(data: any): Promise<Invoice> {
    const invoice = await createInvoice(data)
    const remoteVersion = getVersion(invoice)
    await storeEntity(entity, String(invoice.id), invoice, 'synced', remoteVersion)
    return invoice
  },

  async update(id: string, data: any): Promise<Invoice> {
    const invoice = await updateInvoice(id, data)
    const remoteVersion = getVersion(invoice)
    await storeEntity(entity, String(invoice.id ?? id), invoice, 'synced', remoteVersion)
    return invoice
  },

  async delete(id: string): Promise<void> {
    try {
      await deleteInvoice(id)
      await storeEntity(entity, id, { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion(entity, id)
      console.warn('[offline] Queued invoice deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const invoice = await getInvoice(id)
      return getVersion(invoice)
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    const sameLines = linesSignature(local) === linesSignature(remote)
    return local.total !== remote.total || local.estado !== remote.estado || !sameLines
  },
}

let registered = false

export function registerBillingSyncAdapter() {
  if (registered) return
  getSyncManager().registerAdapter(InvoiceAdapter)
  registered = true
  console.log('[offline] Billing (invoices) sync adapter registered')
}

export { queueInvoiceForSync, queueInvoiceDeletion } from './offlineQueue'
