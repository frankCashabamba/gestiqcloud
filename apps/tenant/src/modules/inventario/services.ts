/**
 * Inventario Services
 */
import tenantApi from '../../shared/api/client'

export type StockItem = {
  id: string
  product_id: string
  warehouse_id: string
  qty_on_hand: number
  lot?: string
  expires_at?: string
}

export type StockMove = {
  id: string
  kind: string
  product_id: string
  warehouse_id: string
  qty: number
  ref_doc_type?: string
  posted_at?: string
  created_at: string
}

const BASE = '/api/v1/inventory'

export async function listStock(params?: any): Promise<StockItem[]> {
  const { data } = await tenantApi.get<StockItem[]>(`${BASE}/stock`, { params })
  return Array.isArray(data) ? data : (data as any)?.items || []
}

export async function listStockMoves(params?: any): Promise<StockMove[]> {
  const { data } = await tenantApi.get<StockMove[]>(`${BASE}/moves`, { params })
  return Array.isArray(data) ? data : (data as any)?.items || []
}

export async function createAdjustment(payload: any) {
  const { data} = await tenantApi.post(`${BASE}/adjustments`, payload)
  return data
}
