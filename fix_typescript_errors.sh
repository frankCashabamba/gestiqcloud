#!/bin/bash
# Script para corregir todos los errores de TypeScript del build

echo "🔧 Corrigiendo errores de TypeScript en frontend tenant..."

# 1. Exportar tipos necesarios desde pos/services.ts
echo "1️⃣ Exportando tipos POSShift y POSReceipt desde pos/services.ts..."
cat > apps/tenant/src/modules/pos/services.ts << 'EOF'
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

// Re-export types for convenience
export type { POSRegister, POSShift, POSReceipt, StoreCredit, Product }

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
    const { data} = await tenantApi.get<POSShift>(`${BASE_URL}/shifts/current/${registerId}`)
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

export async function listReceipts(params?: { shift_id?: string; status?: string; limit?: number }): Promise<POSReceipt[]> {
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
EOF

# 2. Añadir exportaciones a facturacion/services.ts
echo "2️⃣ Añadiendo exportaciones faltantes en facturacion/services.ts..."
cat >> apps/tenant/src/modules/facturacion/services.ts << 'EOF'

// Alias de compatibilidad (por si se usa camelCase en imports)
export async function createFactura(invoice: Partial<Invoice>): Promise<Invoice> {
  const { data } = await tenantApi.post<Invoice>(BASE, invoice)
  return data
}

export async function updateFactura(id: string, invoice: Partial<Invoice>): Promise<Invoice> {
  const { data } = await tenantApi.put<Invoice>(`${BASE}/${id}`, invoice)
  return data
}

export async function removeFactura(id: string): Promise<void> {
  await tenantApi.delete(`${BASE}/${id}`)
}

// Alias adicionales
export const listFacturas = listInvoices
export const getFactura = getInvoice
export type Factura = Invoice
EOF

# 3. Corregir clientes/Form.tsx - remover nif del payload
echo "3️⃣ Corrigiendo clientes/Form.tsx..."
sed -i 's/await createCliente({ nombre, nif, email, telefono, direccion })/await createCliente({ nombre, email, telefono })/' apps/tenant/src/modules/clientes/Form.tsx

# 4. Corregir compras/Form.tsx - cambiar proveedor a proveedor_id y concepto/importe a total
echo "4️⃣ Corrigiendo compras/Form.tsx..."
sed -i 's/await createCompra({ fecha, proveedor, concepto, importe: parseFloat(importe) })/await createCompra({ fecha, proveedor_id: proveedor, total: parseFloat(importe) })/' apps/tenant/src/modules/compras/Form.tsx

# 5. Corregir gastos/Form.tsx - cambiar importe a monto
echo "5️⃣ Corrigiendo gastos/Form.tsx..."
sed -i 's/await createGasto({ fecha, concepto, importe: parseFloat(importe), categoria })/await createGasto({ fecha, concepto, monto: parseFloat(importe) })/' apps/tenant/src/modules/gastos/Form.tsx

# 6. Corregir proveedores/Form.tsx - usar contactos/direcciones arrays
echo "6️⃣ Corrigiendo proveedores/Form.tsx..."
sed -i 's/await createProveedor({ nombre, nif, email, telefono, direccion })/await createProveedor({ nombre, nif, email, telefono, contactos: [], direcciones: direccion ? [{ tipo: "facturacion", linea1: direccion }] : [] })/' apps/tenant/src/modules/proveedores/Form.tsx

# 7. Corregir POS Dashboard - tipos string/number
echo "7️⃣ Corrigiendo pos/Dashboard.tsx..."
# Este archivo necesita ediciones más complejas, se hará manualmente después

# 8. Corregir POS TicketCreator - uom y line_total
echo "8️⃣ Corrigiendo pos/TicketCreator.tsx..."
# Este archivo necesita ediciones más complejas, se hará manualmente después

# 9. Corregir panaderia/ExcelImporter.tsx - remover referencias a stock_items_initialized
echo "9️⃣ Corrigiendo panaderia/ExcelImporter.tsx..."
# Este archivo necesita ediciones más complejas, se hará manualmente después

echo "✅ Script de corrección completado. Ahora se aplicarán correcciones manuales..."
