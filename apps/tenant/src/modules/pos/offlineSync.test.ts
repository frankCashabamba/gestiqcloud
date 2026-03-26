import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  memoryStore,
  createReceiptMock,
  payReceiptMock,
  getReceiptMock,
  openShiftMock,
  closeShiftMock,
  getShiftSummaryMock,
} = vi.hoisted(() => ({
  memoryStore: {} as Record<string, Map<IDBValidKey, unknown>>,
  createReceiptMock: vi.fn(),
  payReceiptMock: vi.fn(),
  getReceiptMock: vi.fn(),
  openShiftMock: vi.fn(),
  closeShiftMock: vi.fn(),
  getShiftSummaryMock: vi.fn(),
}))

function getMemStore(storeName: string) {
  if (!memoryStore[storeName]) memoryStore[storeName] = new Map()
  return memoryStore[storeName]
}

vi.mock('idb-keyval', () => ({
  createStore: (_db: string, store: string) => store,
  get: vi.fn(async (key: IDBValidKey, store: string) => getMemStore(store).get(key)),
  set: vi.fn(async (key: IDBValidKey, value: unknown, store: string) => {
    getMemStore(store).set(key, value)
  }),
  del: vi.fn(async (key: IDBValidKey, store: string) => {
    getMemStore(store).delete(key)
  }),
  entries: vi.fn(async (store: string) => Array.from(getMemStore(store).entries())),
}))

vi.mock('../../lib/offlineDb', () => ({
  ensureOfflineDatabase: vi.fn(async () => {}),
  OFFLINE_DB_NAME: 'gestiqcloud-offline',
  OFFLINE_DB_STORES: {
    entity: 'offline-store',
    metadata: 'offline-metadata',
    auth: 'offline-auth',
  },
}))

vi.mock('./services', () => ({
  createReceipt: createReceiptMock,
  payReceipt: payReceiptMock,
  getReceipt: getReceiptMock,
  openShift: openShiftMock,
  closeShift: closeShiftMock,
  getShiftSummary: getShiftSummaryMock,
}))

import { initOfflineStore, getEntity, storeEntity } from '../../lib/offlineStore'
import { getSyncManager, resetSyncManager } from '../../lib/syncManager'
import { POSReceiptAdapter } from './offlineSync'

function clearMemoryStores() {
  Object.keys(memoryStore).forEach((key) => delete memoryStore[key])
}

describe('POS offline sync', () => {
  beforeEach(async () => {
    clearMemoryStores()
    resetSyncManager()
    vi.clearAllMocks()
    await initOfflineStore()
  })

  it('syncs a queued checkout for an existing receipt after reconnect', async () => {
    getReceiptMock
      .mockResolvedValueOnce({ id: 'receipt-1', status: 'draft', lines: [] })
      .mockResolvedValueOnce({ id: 'receipt-1', status: 'paid', lines: [] })
    payReceiptMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-1', status: 'paid' })

    await storeEntity('receipt', 'local-checkout-1', {
      _op: 'create',
      _queueAction: 'checkout_existing',
      receipt_id: 'receipt-1',
      payments: [{ receipt_id: 'receipt-1', method: 'cash', amount: 25 }],
      warehouse_id: 'warehouse-1',
      stock_selections: [{ line_id: 'line-1', allocations: [{ lot: 'L1', qty: 1 }] }],
    }, 'pending')

    const manager = getSyncManager()
    manager.registerAdapter(POSReceiptAdapter)

    const result = await manager.syncEntity('receipt')

    expect(result.synced).toBe(1)
    expect(payReceiptMock).toHaveBeenCalledWith(
      'receipt-1',
      [{ receipt_id: 'receipt-1', method: 'cash', amount: 25 }],
      {
        warehouse_id: 'warehouse-1',
        stock_selections: [{ line_id: 'line-1', allocations: [{ lot: 'L1', qty: 1 }] }],
      },
    )
    const syncedReceipt = await getEntity('receipt', 'receipt-1')
    expect(syncedReceipt?.syncStatus).toBe('synced')
    expect(syncedReceipt?.data.status).toBe('paid')
  })

  it('creates and checks out an offline express sale when connection returns', async () => {
    createReceiptMock.mockResolvedValueOnce({ id: 'receipt-2', status: 'draft', lines: [] })
    payReceiptMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-2', status: 'paid' })
    getReceiptMock.mockResolvedValueOnce({ id: 'receipt-2', status: 'paid', lines: [] })

    await storeEntity('receipt', 'local-create-1', {
      _op: 'create',
      _queueAction: 'create_and_checkout',
      register_id: 'register-1',
      shift_id: 'shift-1',
      cashier_id: 'cashier-1',
      customer_id: 'customer-1',
      lines: [{
        product_id: 'product-1',
        qty: 2,
        unit_price: 5,
        tax_rate: 0.12,
        discount_pct: 0,
        uom: 'unit',
        line_total: 10,
      }],
      metadata: { notes: 'offline express' },
      payments: [{ receipt_id: 'offline-receipt', method: 'cash', amount: 10 }],
      warehouse_id: 'warehouse-2',
    }, 'pending')

    const manager = getSyncManager()
    manager.registerAdapter(POSReceiptAdapter)

    const result = await manager.syncEntity('receipt')

    expect(result.synced).toBe(1)
    expect(createReceiptMock).toHaveBeenCalledWith(expect.objectContaining({
      register_id: 'register-1',
      shift_id: 'shift-1',
      cashier_id: 'cashier-1',
      customer_id: 'customer-1',
      metadata: { notes: 'offline express' },
    }))
    expect(payReceiptMock).toHaveBeenCalledWith(
      'receipt-2',
      [{ receipt_id: 'receipt-2', method: 'cash', amount: 10 }],
      { warehouse_id: 'warehouse-2' },
    )
    const syncedReceipt = await getEntity('receipt', 'receipt-2')
    expect(syncedReceipt?.syncStatus).toBe('synced')
    expect(syncedReceipt?.data.status).toBe('paid')
  })

  it('does not attempt to charge again when the receipt is already paid remotely', async () => {
    getReceiptMock.mockResolvedValueOnce({ id: 'receipt-3', status: 'paid', lines: [] })

    await storeEntity('receipt', 'local-checkout-2', {
      _op: 'create',
      _queueAction: 'checkout_existing',
      receipt_id: 'receipt-3',
      payments: [{ receipt_id: 'receipt-3', method: 'cash', amount: 12 }],
    }, 'pending')

    const manager = getSyncManager()
    manager.registerAdapter(POSReceiptAdapter)

    const result = await manager.syncEntity('receipt')

    expect(result.synced).toBe(1)
    expect(payReceiptMock).not.toHaveBeenCalled()
    const syncedReceipt = await getEntity('receipt', 'receipt-3')
    expect(syncedReceipt?.syncStatus).toBe('synced')
    expect(syncedReceipt?.data.status).toBe('paid')
  })
})
