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
  difference?: number
  total_sales?: number
  cash_sales?: number
  expected_cash?: number
  counted_cash?: number
  loss_amount?: number
  loss_note?: string | null
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
  cashier_id?: string | null
  cashier_name?: string | null
  number?: string
  status: 'draft' | 'paid' | 'voided' | 'invoiced' | 'unpaid'
  customer_id?: string
  invoice_id?: string
  gross_total: number
  tax_total: number
  subtotal?: number
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
  sku?: string
  name: string
  price: number
  tax_rate: number
  stock_qty?: number
  stock?: number
  image_url?: string
  category?: string
  // POS extras
  uom?: string
  weight_required?: boolean
}

export interface ShiftOpenRequest {
  register_id: string
  opening_float: number
  cashier_id?: string
}

export interface ShiftCloseRequest {
  shift_id: string
  closing_cash: number
  loss_amount?: number
  loss_note?: string
}

export interface ShiftSummary {
  pending_receipts: number
  items_sold: Array<{
    product_id: string | null
    name: string
    code: string
    qty_sold: number
    subtotal: number
    stock: Array<{
      warehouse_id: string
      warehouse_name: string
      qty: number
    }>
  }>
  sales_total: number
  receipts_count: number
  payments?: Record<string, number>
}

export interface ReceiptCreateRequest {
  register_id: string
  shift_id: string
  cashier_id?: string
  customer_id?: string
  currency?: string
  lines: POSReceiptLine[]
  payment_method?: string
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
  refund_method: 'original' | 'cash' | 'store_credit'
  line_ids?: string[]
  restock?: boolean
  store_credit_expiry_months?: number
}

export interface PaymentLinkRequest {
  // Either invoice_id or receipt_id may be provided depending on flow
  invoice_id?: string
  receipt_id?: string
  provider?: 'stripe' | 'kushki' | 'payphone'
  amount?: number
  currency?: string
  description?: string
  metadata?: Record<string, any>
  success_url?: string
  cancel_url?: string
}

export interface CartItem extends POSReceiptLine {
  product?: Product
}

export interface DocSeries {
  id: string
  tenant_id: string
  register_id?: string
  doc_type: 'R' | 'F' | 'C'
  name: string
  current_no: number
  reset_policy: 'yearly' | 'never'
  active: boolean
  created_at: string
}

export interface EInvoiceStatus {
  kind: 'SRI' | 'SII'
  ref: string
  status: 'pending' | 'authorized' | 'rejected'
  clave_acceso?: string
  error_message?: string
  submitted_at?: string
  xml_content?: string
}

export interface PaymentLink {
  id: string
  invoice_id: string
  invoice_number: string
  provider: 'stripe' | 'kushki' | 'payphone'
  url: string
  amount: number
  currency: string
  status: 'pending' | 'completed' | 'expired'
  created_at: string
  expires_at?: string
}

export interface Transaction {
  id: string
  invoice_id: string
  invoice_number: string
  provider: string
  amount: number
  currency: string
  status: 'pending' | 'success' | 'failed'
  ref: string
  created_at: string
}
