export interface Purchase {
  id: string
  tenant_id: string
  number: string
  supplier_id: string
  date: string
  delivery_date?: string
  subtotal: number
  taxes: number
  total: number
  status: 'draft' | 'confirmed' | 'received' | 'invoiced' | 'cancelled'
  notes?: string
  user_id: string
  created_at: string
  updated_at: string
}

export interface PurchaseLine {
  id: string
  purchase_id: string
  product_id: string
  description?: string
  quantity: number
  quantity_received: number
  unit_price: number
  discount: number
  tax_rate: number
  subtotal: number
  total: number
  created_at: string
}

export interface PurchaseCreate {
  number: string
  supplier_id: string
  date?: string
  delivery_date?: string
  subtotal?: number
  taxes?: number
  total?: number
  status?: 'draft' | 'confirmed' | 'received' | 'invoiced' | 'cancelled'
  notes?: string
}

export interface PurchaseUpdate extends Partial<PurchaseCreate> {}

export interface PurchaseReception {
  purchase_id: string
  lines: Array<{
    line_id: string
    quantity_received: number
    lot?: string
    expiration_date?: string
  }>
  notes?: string
}

export interface PurchaseStats {
  total_purchases: number
  total_amount: number
  by_status: Record<string, number>
  by_supplier: Array<{
    supplier_id: string
    supplier_name: string
    total: number
  }>
  purchases_by_month: Array<{
    month: string
    total: number
    quantity: number
  }>
}

export interface PurchaseFilters {
  date_from?: string
  date_to?: string
  supplier_id?: string
  status?: string
  search?: string
}
