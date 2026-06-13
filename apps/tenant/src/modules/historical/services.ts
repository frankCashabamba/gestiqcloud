import tenantApi from '../../shared/api/client'
import { TENANT_HISTORICAL } from '@shared/endpoints'

const BASE = TENANT_HISTORICAL.base

export type HistImport = {
  id: string
  filename: string
  file_type: string | null
  file_size_bytes: number | null
  import_type: string
  total_rows: number
  imported_rows: number
  failed_rows: number
  status: string
  error_detail: string | null
  imported_by: string | null
  created_at: string
  updated_at: string
}

export type HistSale = {
  id: string
  import_id: string | null
  date: string
  number: string | null
  customer_code: string | null
  customer_name: string | null
  product_code: string | null
  product_name: string | null
  quantity: number
  unit_price: number
  subtotal: number
  tax: number
  total: number
  currency: string
  created_at: string
}

export type HistPurchase = {
  id: string
  import_id: string | null
  date: string
  number: string | null
  supplier_code: string | null
  supplier_name: string | null
  product_code: string | null
  product_name: string | null
  quantity: number
  unit_price: number
  subtotal: number
  tax: number
  total: number
  currency: string
  created_at: string
}

export type HistStock = {
  id: string
  import_id: string | null
  date: string
  product_code: string | null
  product_name: string | null
  quantity: number
  unit_cost: number
  total_value: number
  warehouse: string | null
  created_at: string
}

export type HistDailySales = {
  id: string
  import_id: string | null
  date: string
  sales_total: number
  total_items: number
  avg_ticket: number
  created_at: string
}

export type HistDashboard = {
  total_imports: number
  total_sales_records: number
  total_purchase_records: number
  total_stock_records: number
  sales_total: number
  purchases_total: number
  date_range_from: string | null
  date_range_to: string | null
}

export type PaginatedResponse<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}

export async function listImports(): Promise<HistImport[]> {
  const { data } = await tenantApi.get<HistImport[]>(`${BASE}/imports`)
  return data
}

export async function getImport(id: string): Promise<HistImport> {
  const { data } = await tenantApi.get<HistImport>(`${BASE}/imports/${id}`)
  return data
}

export async function deleteImport(id: string): Promise<void> {
  await tenantApi.delete(`${BASE}/imports/${id}`)
}

export async function uploadFile(
  file: File,
  importType: string,
  onUploadProgress?: (percent: number) => void,
): Promise<HistImport> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('import_type', importType)
  const { data } = await tenantApi.post<HistImport>(`${BASE}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (!event.total || !onUploadProgress) return
      onUploadProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)))
    },
  })
  return data
}

export async function listSales(params?: {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
}): Promise<PaginatedResponse<HistSale>> {
  const { data } = await tenantApi.get<PaginatedResponse<HistSale>>(`${BASE}/sales`, { params })
  return data
}

export async function listPurchases(params?: {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
}): Promise<PaginatedResponse<HistPurchase>> {
  const { data } = await tenantApi.get<PaginatedResponse<HistPurchase>>(`${BASE}/purchases`, { params })
  return data
}

export async function listStock(params?: {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
}): Promise<PaginatedResponse<HistStock>> {
  const { data } = await tenantApi.get<PaginatedResponse<HistStock>>(`${BASE}/stock`, { params })
  return data
}

export async function listDailySales(params?: {
  date_from?: string
  date_to?: string
}): Promise<HistDailySales[]> {
  const { data } = await tenantApi.get<HistDailySales[]>(`${BASE}/daily-sales`, { params })
  return data
}

export async function getDashboard(): Promise<HistDashboard> {
  const { data } = await tenantApi.get<HistDashboard>(`${BASE}/dashboard`)
  return data
}
