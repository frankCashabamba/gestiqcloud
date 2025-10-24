/**
 * API Service - Comunicación con backend
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const TENANT_ID = import.meta.env.VITE_TENANT_ID || ''

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': TENANT_ID,
    ...options.headers,
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}

// Products
export async function fetchProducts() {
  const data = await apiFetch<any>('/products?limit=500')
  return Array.isArray(data) ? data : data?.items || []
}

// POS
export async function getCurrentShift(registerId: number) {
  return apiFetch(`/pos/shifts/current/${registerId}`)
}

export async function createReceipt(payload: any) {
  return apiFetch('/pos/receipts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function payReceipt(receiptId: string, payments: any[]) {
  return apiFetch(`/pos/receipts/${receiptId}/pay`, {
    method: 'POST',
    body: JSON.stringify({ payments }),
  })
}

// Helper: Process payment (crea receipt + paga)
export async function processPayment(payload: {
  items: any[]
  total: number
  method: string
  amount_received: number
}) {
  // 1. Crear receipt
  const receipt = await createReceipt({
    shift_id: 1, // TODO: obtener dinámicamente
    lines: payload.items.map((item) => ({
      product_id: item.product_id,
      qty: item.qty,
      unit_price: item.price,
      tax_rate: item.tax_rate,
      discount_pct: 0,
    })),
  })

  // 2. Pagar
  await payReceipt((receipt as any).id, [
    {
      method: payload.method,
      amount: payload.amount_received,
      ref: null,
    },
  ])

  return receipt
}
