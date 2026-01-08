import api from '../../shared/api/client'

export type ProductMargin = {
  product_id: string
  sales_net: number
  cogs: number
  gross_profit: number
  margin_pct: number
}

export type CustomerMargin = {
  customer_id: string | null
  sales_net: number
  cogs: number
  gross_profit: number
  margin_pct: number
}

export type ProductLineMargin = {
  line_id: string
  receipt_id: string
  qty: number
  unit_price: number
  net_total: number
  cogs_unit: number
  cogs_total: number
  gross_profit: number
  gross_margin_pct: number
  created_at: string | null
}

type MarginParams = {
  from: string
  to: string
  warehouse_id?: string
  limit?: number
}

const BASE = '/api/v1/tenant/pos/analytics/margins'

export async function listProductMargins(params: MarginParams) {
  const { data } = await api.get<ProductMargin[]>(`${BASE}/products`, { params })
  return Array.isArray(data) ? data : []
}

export async function listCustomerMargins(params: MarginParams) {
  const { data } = await api.get<CustomerMargin[]>(`${BASE}/customers`, { params })
  return Array.isArray(data) ? data : []
}

export async function listProductLines(productId: string, params: MarginParams) {
  const { data } = await api.get<ProductLineMargin[]>(
    `${BASE}/product/${productId}/lines`,
    { params }
  )
  return Array.isArray(data) ? data : []
}
