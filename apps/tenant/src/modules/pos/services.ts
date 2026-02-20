/**
 * POS Services - API calls
 */
import tenantApi from '../../shared/api/client'
import { API_PATHS } from '../../constants/api'
import { getSyncManager } from '../../lib/syncManager'
import { storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId } from '../../lib/offlineHttp'
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
    PaymentLinkRequest
} from '../../types/pos'
export type { POSReceipt } from '../../types/pos'

const BASE_URL = API_PATHS.POS.REGISTERS.replace('/registers', '')
const PAYMENTS_URL = '/api/v1/payments' // TODO: mover a API_PATHS

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
    const { data } = await tenantApi.get<POSRegister[] | { items?: POSRegister[] }>(`${BASE_URL}/registers`, { headers: authHeaders() })
    if (Array.isArray(data)) return data
    const items = (data as any)?.items
    return Array.isArray(items) ? items : []
}

export async function createRegister(payload: { code: string; name: string; default_warehouse_id?: string; metadata?: any }): Promise<POSRegister> {
    const { data } = await tenantApi.post<POSRegister>(`${BASE_URL}/registers`, payload)
    return data
}

export async function getRegister(id: string): Promise<POSRegister> {
    const { data } = await tenantApi.get<POSRegister>(`${BASE_URL}/registers/${id}`, { headers: authHeaders() })
    return data
}

// ============================================================================
// Shifts
// ============================================================================

export async function openShift(payload: ShiftOpenRequest): Promise<POSShift> {
    const { data } = await tenantApi.post<POSShift>(`${BASE_URL}/shifts`, payload, { headers: authHeaders() })
    return data
}

export async function getShiftSummary(shiftId: string, params?: { cashier_id?: string }): Promise<ShiftSummary> {
    const { data } = await tenantApi.get<ShiftSummary>(`${BASE_URL}/shifts/${shiftId}/summary`, { params, headers: authHeaders() })
    return data
}

export async function closeShift(payload: ShiftCloseRequest): Promise<POSShift> {
    const { data } = await tenantApi.post<POSShift>(`${BASE_URL}/shifts/close`, payload, { headers: authHeaders() })
    return data
}

export async function getCurrentShift(registerId: string): Promise<POSShift | null> {
    try {
        const { data } = await tenantApi.get<POSShift>(`${BASE_URL}/shifts/current/${registerId}`, { headers: authHeaders() })
        return data
    } catch (error: any) {
        if (error.response?.status === 404) return null
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
        `${BASE_URL}/receipts/calculate_totals`,
        { lines: payload.lines, global_discount_pct: payload.global_discount_pct || 0 },
        { headers: authHeaders() }
    )
    return data
}

export async function createReceipt(payload: ReceiptCreateRequest): Promise<POSReceipt> {
    const { data } = await tenantApi.post<POSReceipt>(`${BASE_URL}/receipts`, payload, { headers: authHeaders() })
    return data
}

export async function getReceipt(id: string): Promise<POSReceipt> {
    const { data } = await tenantApi.get<POSReceipt>(`${BASE_URL}/receipts/${id}`, { headers: authHeaders() })
    return data
}

export async function deleteReceipt(id: string): Promise<void> {
    await tenantApi.delete(`${BASE_URL}/receipts/${id}`, { headers: authHeaders() })
}

export async function listReceipts(params?: { shift_id?: string; status?: string; cashier_id?: string }): Promise<POSReceipt[]> {
    const { data } = await tenantApi.get<POSReceipt[] | { items?: POSReceipt[] }>(`${BASE_URL}/receipts`, { params, headers: authHeaders() })
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

export async function payReceipt(
    receiptId: string,
    payments: any[],
    opts?: { warehouse_id?: string }
): Promise<CheckoutResponse> {
    // Checkout unificado: pagos + descuento de stock + documentos por backend
    const payload: any = { payments }
    if (opts?.warehouse_id) payload.warehouse_id = opts.warehouse_id
    try {
        const { data } = await tenantApi.post<CheckoutResponse>(`${BASE_URL}/receipts/${receiptId}/checkout`, payload, { headers: authHeaders() })
        return data
    } catch (err: any) {
        // Fallback para entornos donde /checkout aún no está disponible
        const status = err?.response?.status
        if (status === 404) {
            try {
                // 1) Registrar pagos con endpoint legacy
                await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/take_payment`, { payments }, { headers: authHeaders() })
                // 2) Confirmar/postear el recibo (aplica descuento de stock)
                const altBody: any = {}
                if (opts?.warehouse_id) altBody.warehouse_id = opts.warehouse_id
                await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/post`, altBody, { headers: authHeaders() })
            } catch (legacyErr) {
                throw err // re-lanza el 404 original si el fallback falla
            }
        } else {
            throw err
        }
    }
    const { data } = await tenantApi.get<POSReceipt>(`${BASE_URL}/receipts/${receiptId}`, { headers: authHeaders() })
    return {
        ok: true,
        receipt_id: data.id,
        status: data.status,
        totals: {
            subtotal: data.subtotal || 0,
            tax: data.tax_total || 0,
            total: data.gross_total || 0,
            paid: data.gross_total || 0,
            change: 0
        }
    }
}

export async function convertToInvoice(receiptId: string, payload: ReceiptToInvoiceRequest): Promise<any> {
    const { data } = await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/to_invoice`, payload, { headers: authHeaders() })
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
        const { data } = await tenantApi.post('/api/v1/tenant/invoicing', invoiceData)
        return data
    } catch (error: any) {
        console.error('Error creating invoice from receipt:', error.response?.data || error.message)
        throw error
    }
}

export async function refundReceipt(receiptId: string, payload: RefundRequest): Promise<any> {
    const { data } = await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/refund`, payload, { headers: authHeaders() })
    return data
}

export async function printReceipt(receiptId: string, width: '58mm' | '80mm' = '58mm'): Promise<string> {
    const { data } = await tenantApi.get<string>(`${BASE_URL}/receipts/${receiptId}/print`, {
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

const DOCUMENTS_SALES_URL = '/api/v1/tenant/documents/sales'
const DOCUMENTS_URL = '/api/v1/tenant/documents'

export async function createDocumentDraft(payload: SaleDraft): Promise<DocumentModel> {
    const { data } = await tenantApi.post<DocumentModel>(`${DOCUMENTS_SALES_URL}/draft`, payload, { headers: authHeaders() })
    return data
}

export async function issueDocument(payload: SaleDraft): Promise<DocumentModel> {
    const { data } = await tenantApi.post<DocumentModel>(`${DOCUMENTS_SALES_URL}/issue`, payload, { headers: authHeaders() })
    return data
}

export async function renderDocument(documentId: string): Promise<string> {
    const { data } = await tenantApi.get<string>(`${DOCUMENTS_URL}/${documentId}/render`, {
        headers: authHeaders(),
    })
    return data
}

export async function renderDocumentWithFormat(documentId: string, format: 'THERMAL_80MM' | 'A4_PDF'): Promise<string> {
    const { data } = await tenantApi.get<string>(`${DOCUMENTS_URL}/${documentId}/render`, {
        params: { format },
        headers: authHeaders(),
    })
    return data
}

export async function printDocument(documentId: string, format?: 'THERMAL_80MM' | 'A4_PDF'): Promise<string> {
    const { data } = await tenantApi.get<string>(`${DOCUMENTS_URL}/${documentId}/print`, {
        params: format ? { format } : undefined,
        headers: authHeaders(),
    })
    return data
}

// ============================================================================
// Store Credits
// ============================================================================

export async function listStoreCredits(): Promise<StoreCredit[]> {
    const { data } = await tenantApi.get<StoreCredit[] | { items?: StoreCredit[] }>(`${BASE_URL}/store_credits`, { headers: authHeaders() })
    if (Array.isArray(data)) return data
    const items = (data as any)?.items
    return Array.isArray(items) ? items : []
}

export async function getStoreCreditByCode(code: string): Promise<StoreCredit> {
    const { data } = await tenantApi.get<StoreCredit>(`${BASE_URL}/store_credits/code/${code}`, { headers: authHeaders() })
    return data
}

export async function redeemStoreCredit(code: string, amount: number): Promise<StoreCredit> {
    const { data } = await tenantApi.post<StoreCredit>(`${BASE_URL}/store_credits/redeem`, { code, amount }, { headers: authHeaders() })
    return data
}

// ============================================================================
// Products (para POS)
// ============================================================================

const PRODUCTS_BASE = '/api/v1/tenant/products'

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
    const { data } = await tenantApi.get(`${BASE_URL}/daily_counts`, { params, headers: authHeaders() })
    return data || []
}

export async function getLastDailyCount(registerId: string): Promise<any | null> {
    const counts = await listDailyCounts({ register_id: registerId, limit: 1 })
    return counts.length > 0 ? counts[0] : null
}

export async function addToOutbox(payload: any): Promise<string> {
    const id = createOfflineTempId('receipt')
    const normalized = payload?.type === 'receipt' ? payload.data : payload

    await storeEntity('receipt', id, {
        ...(normalized || {}),
        _op: 'create',
        _pending: true,
        _createdAt: new Date().toISOString(),
        _source: 'pos',
    }, 'pending')

    return id
}
