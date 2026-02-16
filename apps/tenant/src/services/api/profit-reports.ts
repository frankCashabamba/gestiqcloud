/**
 * Profit Reports API Service
 * Connects to Blueprint V2 /api/v1/reports endpoints
 */

import { apiClient } from './client'

export interface DailySummary {
  date: string
  sales: number
  cogs: number
  gross_profit: number
  expenses: number
  net_profit: number
  orders: number
}

export interface ProfitReportSummary {
  total_sales: number
  total_cogs: number
  gross_profit: number
  gross_margin_pct: number
  total_expenses: number
  net_profit: number
  net_margin_pct: number
  total_orders: number
}

export interface ProfitReport {
  date_from: string
  date_to: string
  summary: ProfitReportSummary
  daily: DailySummary[]
}

export interface ProductMarginRow {
  product_id: string
  revenue: number
  cogs: number
  gross_profit: number
  margin_pct: number
  sold_qty: number
  waste_qty: number
}

export interface ProductMarginsReport {
  date_from: string
  date_to: string
  products: ProductMarginRow[]
}

/**
 * Get profit report for date range
 */
export async function getProfitReport(
  dateFrom: string,
  dateTo: string
): Promise<ProfitReport> {
  const response = await apiClient.get<ProfitReport>('/reports/profit', {
    params: {
      date_from: dateFrom,
      date_to: dateTo,
    },
  })

  return response.data
}

/**
 * Get product margins for date range
 */
export async function getProductMargins(
  dateFrom: string,
  dateTo: string,
  options?: {
    limit?: number
    sort_by?: 'revenue' | 'margin_pct' | 'cogs' | 'sold_qty'
  }
): Promise<ProductMarginsReport> {
  const response = await apiClient.get<ProductMarginsReport>(
    '/reports/product-margins',
    {
      params: {
        date_from: dateFrom,
        date_to: dateTo,
        limit: options?.limit || 50,
        sort_by: options?.sort_by || 'revenue',
      },
    }
  )

  return response.data
}

/**
 * Trigger manual profit snapshot recalculation
 */
export async function triggerRecalculation(
  dateFrom: string,
  dateTo: string
): Promise<{ status: string; days_recalculated: number }> {
  const response = await apiClient.post<{
    status: string
    days_recalculated: number
  }>('/reports/recalculate', null, {
    params: {
      date_from: dateFrom,
      date_to: dateTo,
    },
  })

  return response.data
}
