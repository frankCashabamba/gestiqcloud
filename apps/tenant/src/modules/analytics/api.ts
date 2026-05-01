/**
 * Analytics API client.
 * Consumes the canonical /api/v1/tenant/dashboard/kpis endpoint.
 */

import tenantApi from '../../shared/api/client'
import { TENANT_ANALYTICS } from '@shared/endpoints'

export interface KpiBlock {
  total?: number
  tickets?: number
  average_ticket?: number
  ticket_medio?: number
  count?: number
  currency?: string | null
}

export interface TopProduct {
  name: string
  units?: number
  unidades?: number
  revenue?: number
  ingresos?: number
}

export interface TenantKpis {
  // Sector-agnostic generic shape; concrete sectors enrich it.
  sales_today?: KpiBlock
  daily_sales?: KpiBlock
  ventas_dia?: KpiBlock
  new_customers?: { month?: number; week?: number; day?: number }
  monthly_revenue?: { current?: number; target?: number; progress?: number; currency?: string }
  top_products?: TopProduct[]
  top_productos?: TopProduct[]
  message?: string
  [key: string]: any
}

export interface GetTenantKpisParams {
  sector?: string
}

export async function getTenantKpis(params: GetTenantKpisParams = {}): Promise<TenantKpis> {
  const { data } = await tenantApi.get<TenantKpis>(TENANT_ANALYTICS.kpis, { params })
  return data || {}
}

export async function getTenantKpisBySector(sector: string): Promise<TenantKpis> {
  const { data } = await tenantApi.get<TenantKpis>(TENANT_ANALYTICS.kpisBySector(sector))
  return data || {}
}
