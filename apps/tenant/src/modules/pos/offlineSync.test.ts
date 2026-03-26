import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  memoryStore,
  createReceiptMock,
  payReceiptMock,
  getReceiptMock,
  issueDocumentMock,
  backfillReceiptDocumentsMock,
  openShiftMock,
  closeShiftMock,
  getShiftSummaryMock,
} = vi.hoisted(() => ({
  memoryStore: {} as Record<string, Map<IDBValidKey, unknown>>,
  createReceiptMock: vi.fn(),
  payReceiptMock: vi.fn(),
  getReceiptMock: vi.fn(),
  issueDocumentMock: vi.fn(),
  backfillReceiptDocumentsMock: vi.fn(),
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
  issueDocument: issueDocumentMock,
  backfillReceiptDocuments: backfillReceiptDocumentsMock,
  openShift: openShiftMock,
  closeShift: closeShiftMock,
  getShiftSummary: getShiftSummaryMock,
}))

import { initOfflineStore, getEntity, storeEntity, listEntities } from '../../lib/offlineStore'
import { getSyncManager, resetSyncManager } from '../../lib/syncManager'
import { POSReceiptAdapter, POSShiftAdapter } from './offlineSync'

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
    backfillReceiptDocumentsMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-1', documents_created: {} })
    issueDocumentMock.mockResolvedValueOnce({ document: { id: 'doc-1' } })

    await storeEntity('receipt', 'local-checkout-1', {
      _op: 'create',
      _queueAction: 'checkout_existing',
      receipt_id: 'receipt-1',
      payments: [{ receipt_id: 'receipt-1', method: 'cash', amount: 25 }],
      warehouse_id: 'warehouse-1',
      stock_selections: [{ line_id: 'line-1', allocations: [{ lot: 'L1', qty: 1 }] }],
      document_issue: {
        tenantId: 'tenant-1',
        country: 'EC',
        posId: 'pos-1',
        currency: 'USD',
        buyer: { mode: 'CONSUMER_FINAL', idType: 'NONE', idNumber: '', name: 'CF' },
        items: [{ sku: 'SKU-1', name: 'Pan', qty: 1, unitPrice: 25, discount: 0, taxCategory: 'DEFAULT' }],
        payments: [{ method: 'CASH', amount: 25 }],
      },
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
    expect(backfillReceiptDocumentsMock).toHaveBeenCalledWith('receipt-1')
    expect(issueDocumentMock).toHaveBeenCalledOnce()
    const syncedReceipt = await getEntity('receipt', 'receipt-1')
    expect(syncedReceipt?.syncStatus).toBe('synced')
    expect(syncedReceipt?.data.status).toBe('paid')
  })

  it('creates and checks out an offline express sale when connection returns', async () => {
    createReceiptMock.mockResolvedValueOnce({
      id: 'receipt-2',
      status: 'draft',
      lines: [{
        id: 'remote-line-1',
        product_id: 'product-1',
        qty: 2,
        unit_price: 5,
        tax_rate: 0.12,
        discount_pct: 0,
        uom: 'unit',
        line_total: 10,
      }],
    })
    payReceiptMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-2', status: 'paid' })
    backfillReceiptDocumentsMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-2', documents_created: {} })
    issueDocumentMock.mockRejectedValueOnce(new Error('Failed to fetch'))
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
      stock_selections: [{ line_id: 'draft-0', allocations: [{ lot: 'L2', qty: 2 }] }],
      document_issue: {
        tenantId: 'tenant-1',
        country: 'EC',
        posId: 'pos-1',
        currency: 'USD',
        buyer: { mode: 'CONSUMER_FINAL', idType: 'NONE', idNumber: '', name: 'CF' },
        items: [{ sku: 'SKU-1', name: 'Pan', qty: 2, unitPrice: 5, discount: 0, taxCategory: 'DEFAULT' }],
        payments: [{ method: 'CASH', amount: 10 }],
      },
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
      {
        warehouse_id: 'warehouse-2',
        stock_selections: [{ line_id: 'remote-line-1', allocations: [{ lot: 'L2', qty: 2 }] }],
      },
    )
    expect(backfillReceiptDocumentsMock).toHaveBeenCalledWith('receipt-2')
    const syncedReceipt = await getEntity('receipt', 'receipt-2')
    expect(syncedReceipt?.syncStatus).toBe('synced')
    expect(syncedReceipt?.data.status).toBe('paid')
    const pendingDocumentOps = await listEntities('receipt')
    expect(pendingDocumentOps.some((item) => item.syncStatus === 'pending' && item.data?._queueAction === 'issue_document' && item.data?.receipt_id === 'receipt-2')).toBe(true)
  })

  it('does not attempt to charge again when the receipt is already paid remotely', async () => {
    getReceiptMock.mockResolvedValueOnce({ id: 'receipt-3', status: 'paid', lines: [] })
    backfillReceiptDocumentsMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-3', documents_created: {} })
    issueDocumentMock.mockResolvedValueOnce({ document: { id: 'doc-3' } })

    await storeEntity('receipt', 'local-checkout-2', {
      _op: 'create',
      _queueAction: 'checkout_existing',
      receipt_id: 'receipt-3',
      payments: [{ receipt_id: 'receipt-3', method: 'cash', amount: 12 }],
      document_issue: {
        tenantId: 'tenant-1',
        country: 'EC',
        posId: 'pos-1',
        currency: 'USD',
        buyer: { mode: 'CONSUMER_FINAL', idType: 'NONE', idNumber: '', name: 'CF' },
        items: [{ sku: 'SKU-1', name: 'Pan', qty: 1, unitPrice: 12, discount: 0, taxCategory: 'DEFAULT' }],
        payments: [{ method: 'CASH', amount: 12 }],
      },
    }, 'pending')

    const manager = getSyncManager()
    manager.registerAdapter(POSReceiptAdapter)

    const result = await manager.syncEntity('receipt')

    expect(result.synced).toBe(1)
    expect(payReceiptMock).not.toHaveBeenCalled()
    expect(backfillReceiptDocumentsMock).toHaveBeenCalledWith('receipt-3')
    expect(issueDocumentMock).toHaveBeenCalledOnce()
    const syncedReceipt = await getEntity('receipt', 'receipt-3')
    expect(syncedReceipt?.syncStatus).toBe('synced')
    expect(syncedReceipt?.data.status).toBe('paid')
  })

  it('syncs an offline-opened shift before uploading receipts that reference its local id', async () => {
    openShiftMock.mockResolvedValueOnce({
      id: 'server-shift-1',
      register_id: 'register-1',
      opened_by: 'cashier-1',
      opened_at: '2026-03-26T10:00:00Z',
      opening_float: 40,
      status: 'open',
    })
    createReceiptMock.mockResolvedValueOnce({
      id: 'receipt-4',
      status: 'draft',
      lines: [{
        id: 'remote-line-4',
        product_id: 'product-4',
        qty: 1,
        unit_price: 15,
        tax_rate: 0.12,
        discount_pct: 0,
        uom: 'unit',
        line_total: 15,
      }],
    })
    payReceiptMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-4', status: 'paid' })
    backfillReceiptDocumentsMock.mockResolvedValueOnce({ ok: true, receipt_id: 'receipt-4', documents_created: {} })
    getReceiptMock.mockResolvedValueOnce({ id: 'receipt-4', status: 'paid', lines: [] })

    await storeEntity('shift', 'shift-local-1', {
      _op: 'create',
      register_id: 'register-1',
      cashier_id: 'cashier-1',
      opening_float: 40,
      status: 'open',
    }, 'pending')

    await storeEntity('receipt', 'local-create-4', {
      _op: 'create',
      _queueAction: 'create_and_checkout',
      register_id: 'register-1',
      shift_id: 'shift-local-1',
      cashier_id: 'cashier-1',
      lines: [{
        product_id: 'product-4',
        qty: 1,
        unit_price: 15,
        tax_rate: 0.12,
        discount_pct: 0,
        uom: 'unit',
        line_total: 15,
      }],
      payments: [{ receipt_id: 'offline-receipt', method: 'cash', amount: 15 }],
    }, 'pending')

    const manager = getSyncManager()
    manager.registerAdapter(POSShiftAdapter)
    manager.registerAdapter(POSReceiptAdapter)

    const result = await manager.syncEntity('receipt')

    expect(result.synced).toBe(1)
    expect(openShiftMock).toHaveBeenCalledWith({
      register_id: 'register-1',
      cashier_id: 'cashier-1',
      opening_float: 40,
      notes: undefined,
    })
    expect(createReceiptMock).toHaveBeenCalledWith(expect.objectContaining({
      shift_id: 'server-shift-1',
      register_id: 'register-1',
    }))
    const syncedShift = await getEntity('shift', 'shift-local-1')
    expect(syncedShift?.syncStatus).toBe('synced')
    expect(syncedShift?.data.remote_shift_id).toBe('server-shift-1')
  })

  it('syncs an offline open+close shift as one reconciled server flow', async () => {
    openShiftMock.mockResolvedValueOnce({
      id: 'server-shift-2',
      register_id: 'register-1',
      opened_by: 'cashier-2',
      opened_at: '2026-03-26T11:00:00Z',
      opening_float: 60,
      status: 'open',
    })
    closeShiftMock.mockResolvedValueOnce({
      id: 'server-shift-2',
      register_id: 'register-1',
      opened_by: 'cashier-2',
      opened_at: '2026-03-26T11:00:00Z',
      closed_at: '2026-03-26T18:00:00Z',
      opening_float: 60,
      counted_cash: 95,
      status: 'closed',
    })

    await storeEntity('shift', 'shift-local-2', {
      _op: 'create',
      register_id: 'register-1',
      cashier_id: 'cashier-2',
      opening_float: 60,
      status: 'closed',
      _closeRequested: true,
      closing_cash: 95,
      loss_amount: 5,
      loss_note: 'cierre offline',
    }, 'pending')

    const manager = getSyncManager()
    manager.registerAdapter(POSShiftAdapter)

    const result = await manager.syncEntity('shift')

    expect(result.synced).toBe(1)
    expect(openShiftMock).toHaveBeenCalledWith({
      register_id: 'register-1',
      cashier_id: 'cashier-2',
      opening_float: 60,
      notes: undefined,
    })
    expect(closeShiftMock).toHaveBeenCalledWith({
      shift_id: 'server-shift-2',
      closing_cash: 95,
      loss_amount: 5,
      loss_note: 'cierre offline',
    })
    const syncedShift = await getEntity('shift', 'shift-local-2')
    expect(syncedShift?.syncStatus).toBe('synced')
    expect(syncedShift?.data.status).toBe('closed')
    expect(syncedShift?.data.remote_shift_id).toBe('server-shift-2')
  })
})
