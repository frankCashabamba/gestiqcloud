/**
 * POS Offline Sync Adapter
 *
 * Handles synchronization of POS receipts and shifts
 * - Receipts are immutable (create-only)
 * - Shifts can be opened/closed
 */

import { SyncAdapter, getSyncManager } from '../../lib/syncManager'
import { getEntity, storeEntity, listEntities } from '../../lib/offlineStore'
import * as posServices from './services'
import { createOfflineTempId } from '../../lib/offlineHttp'
import type { POSReceipt, POSShift } from '../../types/pos'
import type { POSLineStockSelection, POSPayment, ReceiptCreateRequest } from '../../types/pos'
import type { SaleDraft } from './services'

async function resolveRemoteShiftId(shiftId?: string): Promise<string | undefined> {
  const normalized = String(shiftId || '').trim()
  if (!normalized) return undefined

  const stored = await getEntity('shift', normalized)
  const directRemote = String(stored?.data?.remote_shift_id || '').trim()
  if (directRemote) return directRemote

  if (stored && (stored.syncStatus === 'pending' || stored.syncStatus === 'failed')) {
    const manager = getSyncManager()
    if (manager.hasAdapter('shift')) {
      await manager.syncEntity('shift', false)
      const refreshed = await getEntity('shift', normalized)
      const refreshedRemote = String(refreshed?.data?.remote_shift_id || refreshed?.data?.id || '').trim()
      if (refreshedRemote) return refreshedRemote
    }
  }

  return String(stored?.data?.id || normalized)
}

async function buildReceiptPayload(data: any, localId?: string): Promise<ReceiptCreateRequest> {
  const clientRequestId = data.client_request_id || (localId ? `offline-sync-${localId}` : undefined)
  return {
    register_id: data.register_id ?? data.registerId,
    shift_id: (await resolveRemoteShiftId(data.shift_id ?? data.shiftId)) || '',
    cashier_id: data.cashier_id,
    customer_id: data.customer_id,
    client_request_id: clientRequestId,
    currency: data.currency,
    lines: data.lines ?? data.items ?? [],
    payment_method: data.payment_method,
    metadata: data.metadata,
  }
}

function resolveStockSelections(
  stockSelections: POSLineStockSelection[] | undefined,
  receiptLines?: Array<{ id?: string }>,
): POSLineStockSelection[] | undefined {
  if (!stockSelections?.length) return undefined
  return stockSelections.map((selection) => {
    const match = /^draft-(\d+)$/.exec(String(selection.line_id || ''))
    if (!match) return selection
    const lineIndex = Number(match[1])
    const resolvedLineId = receiptLines?.[lineIndex]?.id
    return resolvedLineId ? { ...selection, line_id: String(resolvedLineId) } : selection
  })
}

function buildCheckoutOptions(
  data: any,
  receiptLines?: Array<{ id?: string }>,
): { warehouse_id?: string; stock_selections?: POSLineStockSelection[] } | undefined {
  const warehouseId = data.warehouse_id
  const stockSelections = resolveStockSelections(
    Array.isArray(data.stock_selections) ? data.stock_selections : undefined,
    receiptLines,
  )
  if (!warehouseId && !stockSelections?.length) return undefined
  return {
    ...(warehouseId ? { warehouse_id: warehouseId } : {}),
    ...(stockSelections?.length ? { stock_selections: stockSelections } : {}),
  }
}

function normalizePayments(payments: POSPayment[] | undefined, receiptId: string): POSPayment[] {
  return (payments || []).map((payment) => ({
    ...payment,
    receipt_id: receiptId,
  }))
}

async function queueDocumentIssueOffline(receiptId: string, saleDraft: SaleDraft) {
  await storeEntity('receipt', createOfflineTempId('receipt'), {
    _queueAction: 'issue_document',
    receipt_id: receiptId,
    sale_draft: saleDraft,
    _op: 'create',
    _pending: true,
    _createdAt: new Date().toISOString(),
    _source: 'pos-document',
  }, 'pending')
}

async function issueDocumentSafely(receiptId: string, saleDraft: SaleDraft | undefined) {
  if (!saleDraft) return
  try {
    await posServices.issueDocument(saleDraft)
  } catch (error) {
    console.warn('[offline] Document issue deferred for receipt:', receiptId, error)
    await queueDocumentIssueOffline(receiptId, saleDraft)
  }
}

// =============================================================================
// Receipt Adapter (Immutable - Create Only)
// =============================================================================

export const POSReceiptAdapter: SyncAdapter = {
  entity: 'receipt',
  canSyncOffline: true,

  async fetchAll(): Promise<POSReceipt[]> {
    // Receipts are immutable, fetch from cache if available
    try {
      // In real implementation, would fetch paginated
      return []
    } catch (error) {
      console.error('Failed to fetch receipts:', error)
      return []
    }
  },

  async create(data: any, _localId?: string): Promise<POSReceipt> {
    const queueAction = data?._queueAction ?? 'create_receipt'
    let receipt: POSReceipt

    if (queueAction === 'issue_document') {
      const receiptId = String(data.receipt_id || '')
      if (!receiptId) throw new Error('offline_document_missing_receipt_id')
      await posServices.issueDocument(data.sale_draft as SaleDraft)
      receipt = await posServices.getReceipt(receiptId)
    } else if (queueAction === 'checkout_existing') {
      const receiptId = String(data.receipt_id || '')
      if (!receiptId) throw new Error('offline_checkout_missing_receipt_id')

      const existing = await posServices.getReceipt(receiptId)
      if (existing?.status === 'paid' || existing?.status === 'invoiced') {
        await posServices.backfillReceiptDocuments(receiptId)
        await issueDocumentSafely(receiptId, data.document_issue as SaleDraft | undefined)
        receipt = existing
      } else {
        await posServices.payReceipt(
          receiptId,
          normalizePayments(data.payments as POSPayment[] | undefined, receiptId),
          buildCheckoutOptions(data, existing?.lines),
        )
        await posServices.backfillReceiptDocuments(receiptId)
        await issueDocumentSafely(receiptId, data.document_issue as SaleDraft | undefined)
        receipt = await posServices.getReceipt(receiptId)
      }
    } else if (queueAction === 'create_and_checkout') {
      const createdReceipt = await posServices.createReceipt(await buildReceiptPayload(data, _localId))
      const receiptId = String(createdReceipt.id || '')
      if (!receiptId) throw new Error('offline_checkout_missing_receipt_id')
      const targetReceipt =
        Array.isArray(createdReceipt?.lines) && createdReceipt.lines.length > 0
          ? createdReceipt
          : await posServices.getReceipt(receiptId)

      if (targetReceipt?.status === 'paid' || targetReceipt?.status === 'invoiced') {
        await posServices.backfillReceiptDocuments(receiptId)
        await issueDocumentSafely(receiptId, data.document_issue as SaleDraft | undefined)
        receipt = targetReceipt
      } else {
        await posServices.payReceipt(
          receiptId,
          normalizePayments(data.payments as POSPayment[] | undefined, receiptId),
          buildCheckoutOptions(data, targetReceipt?.lines),
        )
        await posServices.backfillReceiptDocuments(receiptId)
        await issueDocumentSafely(receiptId, data.document_issue as SaleDraft | undefined)
        receipt = await posServices.getReceipt(receiptId)
      }
    } else {
      receipt = await posServices.createReceipt(await buildReceiptPayload(data, _localId))
    }

    // Store locally as synced
    await storeEntity('receipt', String(receipt.id), receipt, 'synced', 1)

    return receipt
  },

  async update(id: string, data: any): Promise<POSReceipt> {
    // Receipts are immutable - updates not allowed
    throw new Error('Cannot update receipt - receipts are immutable')
  },

  async delete(id: string): Promise<void> {
    // Receipts cannot be deleted
    throw new Error('Cannot delete receipt - receipts are immutable')
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const receipt = await posServices.getReceipt(id)
      return receipt ? 1 : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    // Receipts are immutable, no conflicts possible
    return false
  },
}

// =============================================================================
// Shift Adapter
// =============================================================================

export const POSShiftAdapter: SyncAdapter = {
  entity: 'shift',
  canSyncOffline: true,

  async fetchAll(): Promise<POSShift[]> {
    try {
      // In real implementation, would filter by register and status
      return []
    } catch (error) {
      console.error('Failed to fetch shifts:', error)
      return []
    }
  },

  async create(data: any, localId?: string): Promise<POSShift> {
    // Open shift on server
    const openedShift = await posServices.openShift({
      register_id: data.register_id,
      cashier_id: data.cashier_id,
      opening_float: data.opening_balance ?? data.opening_float ?? 0,
      notes: data.notes,
    })

    const remoteShiftId = String(openedShift.id)

    if (data._closeRequested) {
      const closedShift = await posServices.closeShift({
        shift_id: remoteShiftId,
        closing_cash: data.closing_balance ?? data.closing_cash ?? 0,
        loss_amount: data.variance ?? data.loss_amount,
        loss_note: data.notes ?? data.loss_note,
      })

      const syncedClosedShift = {
        ...closedShift,
        remote_shift_id: remoteShiftId,
      }
      await storeEntity('shift', String(localId || remoteShiftId), syncedClosedShift, 'synced', 1)
      return syncedClosedShift
    }

    const syncedOpenedShift = {
      ...openedShift,
      remote_shift_id: remoteShiftId,
    }
    await storeEntity('shift', String(localId || remoteShiftId), syncedOpenedShift, 'synced', 1)
    return syncedOpenedShift
  },

  async update(id: string, data: any): Promise<POSShift> {
    // Close shift on server
    const shift = await posServices.closeShift({
      shift_id: id,
      closing_cash: data.closing_balance ?? data.closing_cash ?? 0,
      loss_amount: data.variance ?? data.loss_amount,
      loss_note: data.notes,
    })

    await storeEntity('shift', String(shift.id), shift, 'synced', 1)
    return shift
  },

  async delete(id: string): Promise<void> {
    // Cannot delete shifts
    throw new Error('Cannot delete shift')
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const shift = await posServices.getShiftSummary(id)
      return shift ? 1 : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    // Check if shift status differs
    return local.status !== remote.status
  },
}

// =============================================================================
// Initialization
// =============================================================================

let adaptersRegistered = false

export function registerPOSSyncAdapters() {
  if (adaptersRegistered) return

  const manager = getSyncManager()
  manager.registerAdapter(POSShiftAdapter)
  manager.registerAdapter(POSReceiptAdapter)

  adaptersRegistered = true
}

// =============================================================================
// Offline Receipt Queueing (Utility)
// =============================================================================

/**
 * Queue a receipt for offline sync
 * Called when network fails during receipt creation
 */
export async function queueReceiptOffline(data: {
  items: any[]
  customer_id?: string
  payment_method: string
  metadata?: any
}): Promise<string> {
  const id = `receipt-${Date.now()}-${Math.random().toString(36).slice(2)}`

  await storeEntity('receipt', id, {
    ...data,
    _op: 'create',
    _pending: true,
    _createdAt: new Date().toISOString(),
  }, 'pending')

  return id
}

/**
 * Get offline queued receipts waiting to sync
 */
export async function getPendingReceipts(): Promise<any[]> {
  const items = await listEntities('receipt')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => i.data)
}

/**
 * Get failed receipts that need manual retry
 */
export async function getFailedReceipts(): Promise<any[]> {
  const items = await listEntities('receipt')
  return items
    .filter(i => i.syncStatus === 'failed')
    .map(i => ({ ...i.data, error: i.data.serverError }))
}

/**
 * Retry failed receipts
 */
export async function retryFailedReceipts(): Promise<void> {
  const manager = getSyncManager()
  await manager.syncEntity('receipt')
}

// =============================================================================
// Debug/Utility
// =============================================================================

/**
 * Get offline sync stats for POS
 */
export async function getPOSOfflineStats() {
  const receipts = await listEntities('receipt')
  const shifts = await listEntities('shift')

  return {
    receipts: {
      total: receipts.length,
      pending: receipts.filter(r => r.syncStatus === 'pending').length,
      synced: receipts.filter(r => r.syncStatus === 'synced').length,
      failed: receipts.filter(r => r.syncStatus === 'failed').length,
      conflicts: receipts.filter(r => r.syncStatus === 'conflict').length,
    },
    shifts: {
      total: shifts.length,
      pending: shifts.filter(s => s.syncStatus === 'pending').length,
      synced: shifts.filter(s => s.syncStatus === 'synced').length,
      failed: shifts.filter(s => s.syncStatus === 'failed').length,
      conflicts: shifts.filter(s => s.syncStatus === 'conflict').length,
    },
  }
}

/**
 * Clear all offline POS data (for testing)
 */
export async function clearPOSOfflineData() {
  const receipts = await listEntities('receipt')
  for (const receipt of receipts) {
    // Don't delete, just mark as synced if pending
    if (receipt.syncStatus === 'pending') {
      // Discard without syncing
    }
  }
}
