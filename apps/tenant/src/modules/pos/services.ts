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
  ReceiptCreateRequest,
  ReceiptToInvoiceRequest,
  RefundRequest,
  PaymentLinkRequest
} from '../../types/pos'

const BASE_URL = '/v1/pos'
const PAYMENTS_URL = '/v1/payments'

// ============================================================================
// Registers
// ============================================================================

export async function listRegisters(): Promise<POSRegister[]> {
  const { data } = await tenantApi.get<POSRegister[] | { items?: POSRegister[] }>(`${BASE_URL}/registers`)
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function getRegister(id: string): Promise<POSRegister> {
  const { data } = await tenantApi.get<POSRegister>(`${BASE_URL}/registers/${id}`)
  return data
}

// ============================================================================
// Shifts
// ============================================================================

export async function openShift(payload: ShiftOpenRequest): Promise<POSShift> {
  const { data } = await tenantApi.post<POSShift>(`${BASE_URL}/shifts`, payload)
  return data
}

export async function closeShift(payload: ShiftCloseRequest): Promise<POSShift> {
  const { data } = await tenantApi.post<POSShift>(`${BASE_URL}/shifts/close`, payload)
  return data
}

export async function getCurrentShift(registerId: string): Promise<POSShift | null> {
  try {
    const { data } = await tenantApi.get<POSShift>(`${BASE_URL}/shifts/current/${registerId}`)
    return data
  } catch (error: any) {
    if (error.response?.status === 404) return null
    throw error
  }
}

// ============================================================================
// Receipts
// ============================================================================

export async function createReceipt(payload: ReceiptCreateRequest): Promise<POSReceipt> {
  const { data } = await tenantApi.post<POSReceipt>(`${BASE_URL}/receipts`, payload)
  return data
}

export async function getReceipt(id: string): Promise<POSReceipt> {
  const { data } = await tenantApi.get<POSReceipt>(`${BASE_URL}/receipts/${id}`)
  return data
}

export async function listReceipts(params?: { shift_id?: string; status?: string }): Promise<POSReceipt[]> {
  const { data } = await tenantApi.get<POSReceipt[] | { items?: POSReceipt[] }>(`${BASE_URL}/receipts`, { params })
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function payReceipt(receiptId: string, payments: any[]): Promise<POSReceipt> {
  const { data } = await tenantApi.post<POSReceipt>(`${BASE_URL}/receipts/${receiptId}/pay`, { payments })
  return data
}

export async function convertToInvoice(receiptId: string, payload: ReceiptToInvoiceRequest): Promise<any> {
  const { data } = await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/to_invoice`, payload)
  return data
}

export async function refundReceipt(receiptId: string, payload: RefundRequest): Promise<any> {
  const { data } = await tenantApi.post(`${BASE_URL}/receipts/${receiptId}/refund`, payload)
  return data
}

export async function printReceipt(receiptId: string, width: '58mm' | '80mm' = '58mm'): Promise<string> {
  const { data } = await tenantApi.get<string>(`${BASE_URL}/receipts/${receiptId}/print`, {
    params: { width }
  })
  return data
}

// ============================================================================
// Store Credits
// ============================================================================

export async function listStoreCredits(): Promise<StoreCredit[]> {
  const { data } = await tenantApi.get<StoreCredit[] | { items?: StoreCredit[] }>(`${BASE_URL}/store_credits`)
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function getStoreCreditByCode(code: string): Promise<StoreCredit> {
  const { data } = await tenantApi.get<StoreCredit>(`${BASE_URL}/store_credits/code/${code}`)
  return data
}

export async function redeemStoreCredit(code: string, amount: number): Promise<StoreCredit> {
  const { data } = await tenantApi.post<StoreCredit>(`${BASE_URL}/store_credits/redeem`, { code, amount })
  return data
}

// ============================================================================
// Products (para POS)
// ============================================================================

export async function searchProducts(query: string): Promise<Product[]> {
  const { data } = await tenantApi.get<Product[]>(`/api/v1/products/search`, {
    params: { q: query, limit: 20 }
  })
  return data || []
}

export async function getProductByCode(code: string): Promise<Product> {
  const { data } = await tenantApi.get<Product>(`/api/v1/products/by_code/${code}`)
  return data
}

// ============================================================================
// Payments
// ============================================================================

export async function createPaymentLink(payload: PaymentLinkRequest): Promise<{ url: string; session_id: string }> {
  const { data } = await tenantApi.post(`${PAYMENTS_URL}/link`, payload)
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

export function addToOutbox(payload: any): void {
  const outbox = JSON.parse(localStorage.getItem('pos_outbox') || '[]')
  outbox.push({
    id: `temp_${Date.now()}`,
    timestamp: new Date().toISOString(),
    payload
  })
  localStorage.setItem('pos_outbox', JSON.stringify(outbox))
}

