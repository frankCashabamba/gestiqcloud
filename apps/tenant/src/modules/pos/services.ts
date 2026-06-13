/**
 * POS Services - API calls
 */
import tenantApi from '../../shared/api/client'
import { TENANT_INVOICING, TENANT_DOCUMENTS, TENANT_POS, TENANT_PRODUCTS } from '@shared/endpoints'
import { API_PATHS } from '../../constants/api'
import { getSyncManager } from '../../lib/syncManager'
import { getEntity, listEntities, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue } from '../../lib/offlineHttp'
import { getOfflineCacheScope, readCachedResource, writeCachedResource } from '../../lib/offlineResourceCache'
import type {
    POSRegister,
    POSShift,
    POSReceipt,
    StoreCredit,
    Product,
    ShiftOpenRequest,
    ShiftCloseRequest,
    ShiftSummary,
    ReceiptCreateRequest,
    ReceiptToInvoiceRequest,
    RefundRequest,
    PaymentLinkRequest,
    POSLineStockSelection,
    POSPayment
} from '../../types/pos'
export type { POSReceipt } from '../../types/pos'

const PAYMENTS_URL = API_PATHS.PAYMENTS.BASE

function registersCacheKey() {
    return `pos:registers:${getOfflineCacheScope('pos')}`
}

function currentShiftCacheKey(registerId: string) {
    return `pos:current-shift:${registerId}:${getOfflineCacheScope('pos')}`
}

function shiftSummaryCacheKey(shiftId: string) {
    return `pos:shift-summary:${shiftId}:${getOfflineCacheScope('pos')}`
}

function dailyCountsCacheKey(registerId?: string) {
    return `pos:daily-counts:${registerId || 'all'}:${getOfflineCacheScope('pos')}`
}

function isOfflineShiftId(shiftId?: string | null) {
    return String(shiftId || '').startsWith('shift-')
}

function cacheCurrentShift(registerId: string, shift: POSShift | null) {
    writeCachedResource(currentShiftCacheKey(registerId), shift)
}

function clearCachedCurrentShift(registerId: string) {
    try {
        localStorage.removeItem(`gc:offline-resource:${currentShiftCacheKey(registerId)}`)
    } catch {}
}

async function rememberShift(shift: POSShift, remoteShiftId?: string) {
    await storeEntity('shift', String(shift.id), {
        ...shift,
        remote_shift_id: remoteShiftId || String(shift.id),
    }, 'synced', 1)
}

async function resolveShiftRecord(shiftId: string) {
    const stored = await getEntity('shift', shiftId)
    if (stored?.data) return stored.data as POSShift & Record<string, any>

    const shifts = await listEntities('shift')
    const match = shifts.find((item) => String((item.data as any)?.remote_shift_id || '') === shiftId)
    return (match?.data as (POSShift & Record<string, any>) | undefined) || null
}

async function buildOfflineShiftSummary(shiftId: string): Promise<ShiftSummary & { opening_float?: number; _offlineSummary?: boolean }> {
    const shift = await resolveShiftRecord(shiftId)
    const receipts = await listEntities('receipt')
    const pendingReceipts = receipts.filter((item) => {
        const data = item.data || {}
        const linkedShiftId = String(data.shift_id ?? data.shiftId ?? '')
        return linkedShiftId === shiftId && data._queueAction !== 'create_and_checkout'
    })
    const paidReceipts = receipts.filter((item) => {
        const data = item.data || {}
        const linkedShiftId = String(data.shift_id ?? data.shiftId ?? '')
        return linkedShiftId === shiftId && data._queueAction === 'create_and_checkout'
    })

    const payments = paidReceipts.reduce<Record<string, number>>((acc, item) => {
        const data = item.data || {}
        const queuedPayments = Array.isArray(data.payments) ? data.payments : []
        queuedPayments.forEach((payment: POSPayment) => {
            const key = payment.method || 'other'
            acc[key] = Number(acc[key] || 0) + Number(payment.amount || 0)
        })
        return acc
    }, {})

    const salesTotal = Object.values(payments).reduce((sum, value) => sum + Number(value || 0), 0)

    return {
        pending_receipts: pendingReceipts.length,
        items_sold: [],
        sales_total: salesTotal,
        receipts_count: paidReceipts.length,
        payments,
        opening_float: Number(shift?.opening_float || 0),
        _offlineSummary: true,
    }
}

// Ensure Authorization header is always present even across dev proxies/redirects
function authHeaders(): Record<string, string> {
    try {
        const t = sessionStorage.getItem('access_token_tenant') || localStorage.getItem('authToken')
        return t ? { Authorization: `Bearer ${t}` } : {}
    } catch {
        return {}
    }
}

// ============================================================================
// Registers
// ============================================================================

export async function listRegisters(): Promise<POSRegister[]> {
    try {
        const { data } = await tenantApi.get<POSRegister[] | { items?: POSRegister[] }>(TENANT_POS.registers, { headers: authHeaders() })
        const normalized = Array.isArray(data) ? data : Array.isArray((data as any)?.items) ? (data as any).items : []
        writeCachedResource(registersCacheKey(), normalized)
        return normalized
    } catch (error) {
        if (isNetworkIssue(error)) {
            const cached = readCachedResource<POSRegister[]>(registersCacheKey())
            if (cached) return cached
        }
        throw error
    }
}

export async function createRegister(payload: { code: string; name: string; default_warehouse_id?: string; metadata?: any }): Promise<POSRegister> {
    const { data } = await tenantApi.post<POSRegister>(TENANT_POS.registers, payload)
    return data
}

export async function getRegister(id: string): Promise<POSRegister> {
    const { data } = await tenantApi.get<POSRegister>(TENANT_POS.registerById(id), { headers: authHeaders() })
    return data
}

// ============================================================================
// Shifts
// ============================================================================

export async function openShift(payload: ShiftOpenRequest): Promise<POSShift> {
    try {
        const { data } = await tenantApi.post<POSShift>(TENANT_POS.shifts, payload, { headers: authHeaders() })
        cacheCurrentShift(payload.register_id, data)
        await rememberShift(data)
        return data
    } catch (error) {
        if (!isNetworkIssue(error)) throw error

        const offlineShift: POSShift & Record<string, any> = {
            id: createOfflineTempId('shift'),
            register_id: payload.register_id,
            opened_by: String(payload.cashier_id || 'offline'),
            opened_at: new Date().toISOString(),
            opening_float: Number(payload.opening_float || 0),
            status: 'open',
            _offline: true,
            _op: 'create',
            _pending: true,
            _createdAt: new Date().toISOString(),
            _source: 'pos-shift',
            cashier_id: payload.cashier_id,
            notes: payload.notes,
        }

        await storeEntity('shift', offlineShift.id, offlineShift, 'pending')
        cacheCurrentShift(payload.register_id, offlineShift)
        return offlineShift
    }
}

export async function getShiftSummary(shiftId: string, params?: { cashier_id?: string }): Promise<ShiftSummary> {
    try {
        const { data } = await tenantApi.get<ShiftSummary>(TENANT_POS.shiftSummary(shiftId), { params, headers: authHeaders() })
        const shift = await resolveShiftRecord(shiftId)
        writeCachedResource(shiftSummaryCacheKey(shiftId), {
            ...data,
            opening_float: Number(shift?.opening_float || 0),
        })
        return data
    } catch (error) {
        if (!isNetworkIssue(error)) throw error
        const cached = readCachedResource<ShiftSummary>(shiftSummaryCacheKey(shiftId))
        if (cached) return cached
        return await buildOfflineShiftSummary(shiftId)
    }
}

export async function closeShift(payload: ShiftCloseRequest): Promise<POSShift> {
    const { shift_id, ...body } = payload
    try {
        const { data } = await tenantApi.post<POSShift>(TENANT_POS.closeShift(shift_id), body, { headers: authHeaders() })
        await rememberShift(data)
        const currentShift = await resolveShiftRecord(shift_id)
        if (currentShift?.register_id) clearCachedCurrentShift(String(currentShift.register_id))
        return data
    } catch (error) {
        if (!isNetworkIssue(error)) throw error

        const currentShift = await resolveShiftRecord(shift_id)
        const closedAt = new Date().toISOString()
        const offlineClosedShift: POSShift & Record<string, any> = {
            ...(currentShift || {}),
            id: shift_id,
            register_id: String(currentShift?.register_id || ''),
            opened_by: String(currentShift?.opened_by || 'offline'),
            opened_at: currentShift?.opened_at || closedAt,
            opening_float: Number(currentShift?.opening_float || 0),
            status: 'closed',
            closed_at: closedAt,
            counted_cash: Number(payload.closing_cash || 0),
            closing_total: Number(payload.closing_cash || 0),
            loss_amount: payload.loss_amount,
            loss_note: payload.loss_note,
            difference: Number(payload.closing_cash || 0) - Number(currentShift?.expected_cash || 0),
            _offline: true,
        }

        if (currentShift?.register_id) clearCachedCurrentShift(String(currentShift.register_id))

        const existing = await getEntity('shift', shift_id)
        if (existing?.data?._op === 'create' || isOfflineShiftId(shift_id)) {
            await storeEntity('shift', shift_id, {
                ...(existing?.data || currentShift || {}),
                _closeRequested: true,
                closing_cash: Number(payload.closing_cash || 0),
                loss_amount: payload.loss_amount,
                loss_note: payload.loss_note,
                status: 'closed',
                closed_at: closedAt,
            }, 'pending', existing?.remoteVersion)
        } else {
            await storeEntity('shift', shift_id, {
                ...(currentShift || {}),
                shift_id,
                closing_cash: Number(payload.closing_cash || 0),
                loss_amount: payload.loss_amount,
                loss_note: payload.loss_note,
                _op: 'update',
                _pending: true,
                _createdAt: closedAt,
                _source: 'pos-shift',
                status: 'closed',
                closed_at: closedAt,
            }, 'pending', existing?.remoteVersion)
        }

        return offlineClosedShift
    }
}

export async function getCurrentShift(registerId: string): Promise<POSShift | null> {
    try {
        const { data } = await tenantApi.get<POSShift>(TENANT_POS.currentShift(registerId), { headers: authHeaders() })
        cacheCurrentShift(registerId, data)
        await rememberShift(data)
        return data
    } catch (error: any) {
        if (error.response?.status === 404) {
            clearCachedCurrentShift(registerId)
            return null
        }
        if (isNetworkIssue(error)) {
            const cached = readCachedResource<POSShift | null>(currentShiftCacheKey(registerId))
            return cached?.status === 'open' ? cached : null
        }
        throw error
    }
}

// ============================================================================
// Receipts
// ============================================================================

export type ReceiptTotals = {
    subtotal: number
    line_discounts: number
    global_discount: number
    base_after_discounts: number
    tax: number
    total: number
}

export type CalculateTotalsLine = {
    qty: number
    unit_price: number
    tax_rate: number
    discount_pct: number
}

export async function calculateReceiptTotals(payload: {
    lines: CalculateTotalsLine[]
    global_discount_pct?: number
}): Promise<ReceiptTotals> {
    const { data } = await tenantApi.post<ReceiptTotals>(
        TENANT_POS.receiptCalculateTotals,
        { lines: payload.lines, global_discount_pct: payload.global_discount_pct || 0 },
        { headers: authHeaders() }
    )
    return data
}

export async function createReceipt(payload: ReceiptCreateRequest): Promise<POSReceipt> {
    const { data } = await tenantApi.post<POSReceipt>(TENANT_POS.receipts, payload, { headers: authHeaders() })
    return data
}

export async function getReceipt(id: string): Promise<POSReceipt> {
    const { data } = await tenantApi.get<POSReceipt>(TENANT_POS.receiptById(id), { headers: authHeaders() })
    return data
}

export async function deleteReceipt(id: string): Promise<void> {
    await tenantApi.delete(TENANT_POS.receiptById(id), { headers: authHeaders() })
}

export async function listReceipts(params?: { shift_id?: string; status?: string; cashier_id?: string }): Promise<POSReceipt[]> {
    const { data } = await tenantApi.get<POSReceipt[] | { items?: POSReceipt[] }>(TENANT_POS.receipts, { params, headers: authHeaders() })
    if (Array.isArray(data)) return data
    const items = (data as any)?.items
    return Array.isArray(items) ? items : []
}

export type CheckoutResponse = {
    ok: boolean
    receipt_id: string
    status: string
    totals: {
        subtotal: number
        tax: number
        total: number
        paid: number
        change: number
    }
    documents_created?: {
        invoice?: {
            invoice_id: string
            invoice_number: string
            status: string
            subtotal: number
            tax: number
            total: number
        }
        sale?: {
            sale_id: string
            sale_type: string
            status: string
            total: number
        }
        expense?: {
            expense_id: string
            expense_type: string
            amount: number
            status: string
        }
    }
}

export type QueuedPOSCheckoutExisting = {
    _queueAction: 'checkout_existing'
    receipt_id: string
    payments: POSPayment[]
    warehouse_id?: string
    stock_selections?: POSLineStockSelection[]
    document_issue?: SaleDraft
    metadata?: Record<string, any>
}

export type QueuedPOSCreateAndCheckout = {
    _queueAction: 'create_and_checkout'
    register_id: string
    shift_id: string
    cashier_id?: string
    customer_id?: string
    currency?: string
    lines: ReceiptCreateRequest['lines']
    metadata?: Record<string, any>
    payments: POSPayment[]
    warehouse_id?: string
    stock_selections?: POSLineStockSelection[]
    document_issue?: SaleDraft
}

export type QueuedPOSIssueDocument = {
    _queueAction: 'issue_document'
    receipt_id: string
    sale_draft: SaleDraft
}

export type QueuedPOSOutboxPayload =
    | QueuedPOSCheckoutExisting
    | QueuedPOSCreateAndCheckout
    | QueuedPOSIssueDocument
    | (ReceiptCreateRequest & { _queueAction?: 'create_receipt' })

export async function payReceipt(
    receiptId: string,
    payments: any[],
    opts?: { warehouse_id?: string; stock_selections?: POSLineStockSelection[] }
): Promise<CheckoutResponse> {
    const payload: any = { payments }
    if (opts?.warehouse_id) payload.warehouse_id = opts.warehouse_id
    if (opts?.stock_selections?.length) payload.stock_selections = opts.stock_selections
    const { data } = await tenantApi.post<CheckoutResponse>(
        TENANT_POS.receiptCheckout(receiptId),
        payload,
        { headers: authHeaders() }
    )
    return data
}

export async function convertToInvoice(receiptId: string, payload: ReceiptToInvoiceRequest): Promise<any> {
    const { data } = await tenantApi.post(TENANT_POS.receiptToInvoice(receiptId), payload, { headers: authHeaders() })
    return data
}

/**
 * Create an invoice in the invoicing module from a POS receipt
 * Syncs with the Billing module
 */
export async function createInvoiceFromReceipt(receiptId: string, receipt: POSReceipt, payload: ReceiptToInvoiceRequest): Promise<any> {
    // Get current receipt if not provided
    const currentReceipt = receipt || (await getReceipt(receiptId))
    const r = currentReceipt as any

    // Map lines from the POS receipt with explicit totals and taxes
    const lineas = Array.isArray(r?.lines)
        ? r.lines.map((line: any) => {
              const qty = Number(line.qty) || 0
              const unitPrice = Number(line.unit_price) || 0
              const discountPct = Number(line.discount_pct || 0)
              const taxRate = Number(line.tax_rate || 0)

              const netBeforeTax = +(qty * unitPrice * (1 - discountPct / 100)).toFixed(2)
              const taxAmount = +(netBeforeTax * taxRate).toFixed(2)

              return {
                  sector: 'pos',
                  description: line?.product?.name || line?.product_name || `Producto ${line.product_id}`,
                  cantidad: qty,
                  precio_unitario: unitPrice,
                  iva: taxAmount,
                  sku: line?.product?.code || line?.product_code || line?.product?.sku,
              }
          })
        : []

    // Totales seguros (usa receipt si por alguna razon no hay lineas)
    const subtotalFromLines = lineas.reduce((sum, l: any) => sum + (l.precio_unitario || 0) * (l.cantidad || 0), 0)
    const taxFromLines = lineas.reduce((sum, l: any) => sum + (l.iva || 0), 0)
    const totalFromLines = subtotalFromLines + taxFromLines

    const subtotal = lineas.length ? subtotalFromLines : Math.max(0, Number(r?.gross_total || 0) - Number(r?.tax_total || 0))
    const iva = lineas.length ? taxFromLines : Number(r?.tax_total || 0)
    const total = lineas.length ? totalFromLines : Number(r?.gross_total || 0)

    // Dejar que el backend numere si no se pasa serie
    const invoiceData = {
        numero: payload.series ? `${payload.series}-001` : r?.number || `INV-${Date.now()}`,
        fecha: new Date().toISOString().split('T')[0],
        cliente_id: r?.customer_id ? String(r.customer_id) : undefined,
        supplier: payload.customer.name,
        lineas: lineas.length > 0 ? lineas : [
            {
                sector: 'pos',
                description: 'POS Sale',
                cantidad: 1,
                precio_unitario: subtotal || total,
                iva,
            },
        ],
        subtotal: +subtotal.toFixed(2),
        iva: +iva.toFixed(2),
        total: +total.toFixed(2),
        estado: 'emitida',
        meta: { pos_receipt_id: receiptId },
    }

    // Create invoice via invoicing endpoint using the correct API client
    try {
        // Use the invoicing endpoint
        const { data } = await tenantApi.post(TENANT_INVOICING.base, invoiceData)
        return data
    } catch (error: any) {
        console.error('Error creating invoice from receipt:', error.response?.data || error.message)
        throw error
    }
}

export async function refundReceipt(receiptId: string, payload: RefundRequest): Promise<any> {
    const { data } = await tenantApi.post(TENANT_POS.receiptRefund(receiptId), payload, { headers: authHeaders() })
    return data
}

export async function printReceipt(receiptId: string, width: '58mm' | '80mm' = '58mm'): Promise<string> {
    const { data } = await tenantApi.get<string>(TENANT_POS.receiptPrint(receiptId), {
        params: { width },
        headers: authHeaders(),
    })
    return data
}

// ============================================================================
// Documents (new emission pipeline)
// ============================================================================

export type SaleDraft = {
    tenantId: string
    country: string
    posId: string
    currency: string
    buyer: {
        mode: 'CONSUMER_FINAL' | 'IDENTIFIED'
        idType: string
        idNumber: string
        name: string
        email?: string
    }
    items: Array<{
        sku: string
        name: string
        qty: number
        unitPrice: number
        discount: number
        taxCategory: string
    }>
    payments: Array<{
        method: 'CASH' | 'CARD' | 'TRANSFER' | 'OTHER'
        amount: number
    }>
    meta?: Record<string, any>
}

export type DocumentModel = {
    document: { id: string }
}

export async function createDocumentDraft(payload: SaleDraft): Promise<DocumentModel> {
    const { data } = await tenantApi.post<DocumentModel>(TENANT_DOCUMENTS.salesDraft, payload, { headers: authHeaders() })
    return data
}

export async function issueDocument(payload: SaleDraft): Promise<DocumentModel> {
    const { data } = await tenantApi.post<DocumentModel>(TENANT_DOCUMENTS.salesIssue, payload, { headers: authHeaders() })
    return data
}

export async function backfillReceiptDocuments(receiptId: string): Promise<{ ok: boolean; receipt_id: string; documents_created?: Record<string, any> }> {
    const { data } = await tenantApi.post<{ ok: boolean; receipt_id: string; documents_created?: Record<string, any> }>(
        TENANT_POS.receiptBackfillDocuments(receiptId),
        {},
        { headers: authHeaders() },
    )
    return data
}

export async function renderDocument(documentId: string): Promise<string> {
    const { data } = await tenantApi.get<string>(TENANT_DOCUMENTS.render(documentId), {
        headers: authHeaders(),
    })
    return data
}

export async function renderDocumentWithFormat(documentId: string, format: 'THERMAL_80MM' | 'A4_PDF'): Promise<string> {
    const { data } = await tenantApi.get<string>(TENANT_DOCUMENTS.render(documentId), {
        params: { format },
        headers: authHeaders(),
    })
    return data
}

export async function printDocument(documentId: string, format?: 'THERMAL_80MM' | 'A4_PDF'): Promise<string> {
    const { data } = await tenantApi.get<string>(TENANT_DOCUMENTS.print(documentId), {
        params: format ? { format } : undefined,
        headers: authHeaders(),
    })
    return data
}

// ============================================================================
// Store Credits
// ============================================================================

export async function listStoreCredits(): Promise<StoreCredit[]> {
    const { data } = await tenantApi.get<StoreCredit[] | { items?: StoreCredit[] }>(TENANT_POS.storeCredits, { headers: authHeaders() })
    if (Array.isArray(data)) return data
    const items = (data as any)?.items
    return Array.isArray(items) ? items : []
}

export async function getStoreCreditByCode(code: string): Promise<StoreCredit> {
    const { data } = await tenantApi.get<StoreCredit>(TENANT_POS.storeCreditByCode(code), { headers: authHeaders() })
    return data
}

export async function redeemStoreCredit(code: string, amount: number): Promise<StoreCredit> {
    const { data } = await tenantApi.post<StoreCredit>(TENANT_POS.redeemStoreCredit, { code, amount }, { headers: authHeaders() })
    return data
}

// ============================================================================
// Products (para POS)
// ============================================================================

const PRODUCTS_BASE = TENANT_PRODUCTS.products.list

export async function listAllProducts(limit: number = 200): Promise<Product[]> {
    const { data } = await tenantApi.get<Product[] | { items: Product[] }>(`${PRODUCTS_BASE}/`, {
        params: { limit, active_only: true },
        headers: authHeaders(),
    })
    // Soportar ambos formatos: array directo o {items: array}
    if (Array.isArray(data)) return data
    return (data as any)?.items || []
}

export async function searchProducts(query: string): Promise<Product[]> {
    const { data } = await tenantApi.get<Product[]>(`${PRODUCTS_BASE}/search`, {
        params: { q: query, limit: 20 },
        headers: authHeaders(),
    })
    return data || []
}

export async function getProductByCode(code: string): Promise<Product> {
    const { data } = await tenantApi.get<Product>(`${PRODUCTS_BASE}/by_code/${code}`, { headers: authHeaders() })
    return data
}

// ============================================================================
// Payments
// ============================================================================

export async function createPaymentLink(payload: PaymentLinkRequest): Promise<{ url: string; session_id: string }> {
    const { data } = await tenantApi.post(`${PAYMENTS_URL}/link`, payload, { headers: authHeaders() })
    return data
}

// ============================================================================
// Offline Support
// ============================================================================

export async function syncOfflineReceipts(): Promise<void> {
    await getSyncManager().syncEntity('receipt')
}

export async function listDailyCounts(params?: { register_id?: string; since?: string; until?: string; limit?: number }): Promise<any[]> {
    try {
        const { data } = await tenantApi.get(TENANT_POS.dailyCounts, { params, headers: authHeaders() })
        if (params?.register_id) writeCachedResource(dailyCountsCacheKey(params.register_id), data || [])
        return data || []
    } catch (error) {
        if (isNetworkIssue(error)) {
            const cached = readCachedResource<any[]>(dailyCountsCacheKey(params?.register_id))
            if (cached) return cached
        }
        throw error
    }
}

export async function getLastDailyCount(registerId: string): Promise<any | null> {
    const counts = await listDailyCounts({ register_id: registerId, limit: 1 })
    return counts.length > 0 ? counts[0] : null
}

export async function addToOutbox(payload: QueuedPOSOutboxPayload | any): Promise<string> {
    const id = createOfflineTempId('receipt')
    const normalized = payload?.type === 'receipt' ? payload.data : payload
    const queueAction = normalized?._queueAction || 'create_receipt'

    await storeEntity('receipt', id, {
        ...(normalized || {}),
        _queueAction: queueAction,
        _op: 'create',
        _pending: true,
        _createdAt: new Date().toISOString(),
        _source: 'pos',
    }, 'pending')

    return id
}
