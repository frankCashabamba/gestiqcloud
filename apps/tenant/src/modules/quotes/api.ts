import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'

export type QuoteStatus = 'DRAFT' | 'APPROVED' | 'CONVERTED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED'

export interface QuoteLine {
  product_id?: string | null
  name?: string | null
  qty: number
  unit_price: number
  tax_rate?: number
  discount_percent?: number
  line_total?: number
}

export interface Quote {
  id: string
  number?: string | null
  customer_id?: string | null
  status: QuoteStatus | string
  currency?: string | null
  subtotal: number
  tax: number
  total: number
  quote_date?: string | null
  valid_until?: string | null
  notes?: string | null
  converted_to_order_id?: string | null
  lines: QuoteLine[]
  created_at?: string
  updated_at?: string
}

export interface QuoteCreate {
  customer_id?: string | null
  currency?: string | null
  valid_until?: string | null
  notes?: string | null
  lines: QuoteLine[]
}

const BASE = '/api/v1/tenant/quotes'

export async function listQuotes(params?: {
  status?: string
  customer_id?: string
  q?: string
  limit?: number
  offset?: number
}): Promise<Quote[]> {
  const { data } = await tenantApi.get(BASE, { params })
  return ensureArray<Quote>(data)
}

export async function getQuote(id: string): Promise<Quote> {
  const { data } = await tenantApi.get(`${BASE}/${id}`)
  return data
}

export async function createQuote(payload: QuoteCreate): Promise<Quote> {
  const { data } = await tenantApi.post(BASE, payload)
  return data
}

export async function updateQuote(id: string, payload: Partial<QuoteCreate>): Promise<Quote> {
  const { data } = await tenantApi.put(`${BASE}/${id}`, payload)
  return data
}

export async function approveQuote(id: string): Promise<Quote> {
  const { data } = await tenantApi.post(`${BASE}/${id}/approve`)
  return data
}

export async function convertQuote(id: string): Promise<{ quote_id: string; sales_order_id: string }> {
  const { data } = await tenantApi.post(`${BASE}/${id}/convert`)
  return data
}

export async function deleteQuote(id: string): Promise<void> {
  await tenantApi.delete(`${BASE}/${id}`)
}
