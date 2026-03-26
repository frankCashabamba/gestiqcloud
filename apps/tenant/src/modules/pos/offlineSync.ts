/**
 * POS Offline Sync Adapter
 *
 * Handles synchronization of POS receipts and shifts
 * - Receipts are immutable (create-only)
 * - Shifts can be opened/closed
 */

import { SyncAdapter, getSyncManager } from '../../lib/syncManager'
import { storeEntity, listEntities } from '../../lib/offlineStore'
import * as posServices from './services'
import type { POSReceipt, POSShift } from '../../types/pos'
import type { POSLineStockSelection, POSPayment, ReceiptCreateRequest } from '../../types/pos'

function buildReceiptPayload(data: any): ReceiptCreateRequest {
  return {
    register_id: data.register_id ?? data.registerId,
    shift_id: data.shift_id ?? data.shiftId,
    cashier_id: data.cashier_id,
    customer_id: data.customer_id,
    currency: data.currency,
    lines: data.lines ?? data.items ?? [],
    payment_method: data.payment_method,
    metadata: data.metadata,
  }
}

function buildCheckoutOptions(data: any): { warehouse_id?: string; stock_selections?: POSLineStockSelection[] } | undefined {
  const warehouseId = data.warehouse_id
  const stockSelections = Array.isArray(data.stock_selections) ? data.stock_selections : undefined
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

  async create(data: any): Promise<POSReceipt> {
    const queueAction = data?._queueAction ?? 'create_receipt'
    let receipt: POSReceipt

    if (queueAction === 'checkout_existing') {
      const receiptId = String(data.receipt_id || '')
      if (!receiptId) throw new Error('offline_checkout_missing_receipt_id')

      const existing = await posServices.getReceipt(receiptId)
      if (existing?.status === 'paid' || existing?.status === 'invoiced') {
        receipt = existing
      } else {
        await posServices.payReceipt(
          receiptId,
          normalizePayments(data.payments as POSPayment[] | undefined, receiptId),
          buildCheckoutOptions(data),
        )
        receipt = await posServices.getReceipt(receiptId)
      }
    } else if (queueAction === 'create_and_checkout') {
      const createdReceipt = await posServices.createReceipt(buildReceiptPayload(data))
      const receiptId = String(createdReceipt.id || '')
      if (!receiptId) throw new Error('offline_checkout_missing_receipt_id')

      await posServices.payReceipt(
        receiptId,
        normalizePayments(data.payments as POSPayment[] | undefined, receiptId),
        buildCheckoutOptions(data),
      )
      receipt = await posServices.getReceipt(receiptId)
    } else {
      receipt = await posServices.createReceipt(buildReceiptPayload(data))
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

  async create(data: any): Promise<POSShift> {
    // Open shift on server
    const shift = await posServices.openShift({
      register_id: data.register_id,
      cashier_id: data.cashier_id,
      opening_float: data.opening_balance ?? data.opening_float ?? 0,
      notes: data.notes,
    })

    await storeEntity('shift', String(shift.id), shift, 'synced', 1)
    return shift
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
  manager.registerAdapter(POSReceiptAdapter)
  manager.registerAdapter(POSShiftAdapter)

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
