/**
 * POS TypeScript Types
 * Definiciones de tipos para el módulo POS
 */

export interface POSRegister {
  id: string
  tenant_id: string
  store_id?: string
  name: string
  active: boolean
  created_at: string
}

export interface POSShift {
  id: string
  register_id: string
  opened_by: string
  opened_at: string
  closed_at?: string
  opening_float: number
  closing_total?: number
  status: 'open' | 'closed'
}

export interface POSReceiptLine {
  id?: string
  receipt_id?: string
  product_id: string
  product_name?: string
  product_code?: string
  qty: number
  uom: string
  unit_price: number
  tax_rate: number
  discount_pct: number
  line_total: number
}

export interface POSReceipt {
  id?: string
  tenant_id?: string
  register_id: string
  shift_id: string
  number?: string
  status: 'draft' | 'paid' | 'voided' | 'invoiced'
  customer_id?: string
  invoice_id?: string
  gross_total: number
  tax_total: number
  currency: string
  paid_at?: string
  created_at?: string
  lines: POSReceiptLine[]
  payments?: POSPayment[]
}

export interface POSPayment {
  id?: string
  receipt_id: string
  method: 'cash' | 'card' | 'store_credit' | 'link'
  amount: number
  ref?: string
  paid_at?: string
}

export interface StoreCredit {
  id: string
  tenant_id: string
  code: string
  customer_id?: string
  currency: string
  amount_initial: number
  amount_remaining: number
  expires_at?: string
  status: 'active' | 'redeemed' | 'expired' | 'void'
  created_at: string
}

export interface Product {
  id: string
  code?: string
  name: string
  price: number
  tax_rate: number
  stock_qty?: number
  image_url?: string
  category?: string
}

export interface ShiftOpenRequest {
  register_id: string
  opening_float: number
}

export interface ShiftCloseRequest {
  shift_id: string
  closing_total: number
}

export interface ReceiptCreateRequest {
  register_id: string
  shift_id: string
  customer_id?: string
  currency?: string
  lines: POSReceiptLine[]
}

export interface ReceiptToInvoiceRequest {
  customer: {
    name: string
    tax_id: string
    country: string
    address?: string
    email?: string
  }
  series?: string
}

export interface RefundRequest {
  reason: string
  refund_method: 'cash' | 'card' | 'store_credit' | 'original'
  store_credit_expiry_months?: number
}

export interface PaymentLinkRequest {
  invoice_id: string
  provider: 'stripe' | 'kushki' | 'payphone'
  success_url?: string
  cancel_url?: string
}

export interface CartItem extends POSReceiptLine {
  product?: Product
}
