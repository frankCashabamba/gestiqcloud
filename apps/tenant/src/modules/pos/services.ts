/**
 * POS Services - API calls
 */
import tenantApi from '../../shared/api/client'
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

const BASE_URL = '/api/v1/tenant/pos'
const PAYMENTS_URL = '/api/v1/payments'

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

export async function getShiftSummary(shiftId: string): Promise<ShiftSummary> {
    const { data } = await tenantApi.get<ShiftSummary>(`${BASE_URL}/shifts/${shiftId}/summary`, { headers: authHeaders() })
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

export async function listReceipts(params?: { shift_id?: string; status?: string }): Promise<POSReceipt[]> {
    const { data } = await tenantApi.get<POSReceipt[] | { items?: POSReceipt[] }>(`${BASE_URL}/receipts`, { params, headers: authHeaders() })
    if (Array.isArray(data)) return data
    const items = (data as any)?.items
    return Array.isArray(items) ? items : []
}

export async function payReceipt(
    receiptId: string,
    payments: any[],
    opts?: { warehouse_id?: string }
): Promise<POSReceipt> {
    // Checkout unificado: pagos + descuento de stock por backend
    const payload: any = { payments }
    if (opts?.warehouse_id) payload.warehouse_id = opts.warehouse_id
    try {
        await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/checkout`, payload, { headers: authHeaders() })
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
    return data
}

export async function convertToInvoice(receiptId: string, payload: ReceiptToInvoiceRequest): Promise<any> {
    const { data } = await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/to_invoice`, payload, { headers: authHeaders() })
    return data
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
    const outbox = JSON.parse(localStorage.getItem('pos_outbox') || '[]')

    for (const item of outbox) {
        try {
            await tenantApi.post(`${BASE_URL}/receipts`, item.payload)
            // Remove from outbox on success
            const updated = outbox.filter((i: any) => i.id !== item.id)
            localStorage.setItem('pos_outbox', JSON.stringify(updated))
        } catch (error) {
            console.error('Sync failed for item:', item.id, error)
        }
    }
}

export async function listDailyCounts(params?: { register_id?: string; since?: string; until?: string; limit?: number }): Promise<any[]> {
    const { data } = await tenantApi.get(`${BASE_URL}/daily_counts`, { params, headers: authHeaders() })
    return data || []
}

export async function getLastDailyCount(registerId: string): Promise<any | null> {
    const counts = await listDailyCounts({ register_id: registerId, limit: 1 })
    return counts.length > 0 ? counts[0] : null
}

export function addToOutbox(payload: any): void {
    const outbox = JSON.parse(localStorage.getItem('pos_outbox') || '[]')
    outbox.push({
        id: `temp_${Date.now()}`,
        timestamp: new Date().toISOString(),
        payload
    })
    localStorage.setItem('pos_outbox', JSON.stringify(outbox))
}
