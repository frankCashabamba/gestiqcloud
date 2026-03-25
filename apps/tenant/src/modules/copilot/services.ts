import api from "../../services/api/client"
import { TENANT_AI } from '@shared/endpoints'

export type Topic =
  | 'ventas_mes'
  | 'ventas_por_almacen'
  | 'top_productos'
  | 'stock_bajo'
  | 'pendientes_sri_sii'
  | 'cobros_pagos'
  | 'pos_hoy'
  | 'gastos_mes'
  | 'produccion_activa'
  | 'compras_pendientes'
  | 'prediccion_reorden'
  | 'anomalias_ventas'
  | 'clasificar_gasto'

export type Action =
  | 'create_invoice_draft'
  | 'create_order_draft'
  | 'create_transfer_draft'
  | 'suggest_overlay_fields'

export interface AskPayload {
  topic: Topic
  params?: Record<string, any>
  with_ai_insights?: boolean
}

export interface ActPayload {
  action: Action
  payload?: Record<string, any>
}

export interface AIInsights {
  findings?: string[]
  trends?: string[]
  recommendations?: string[]
  alerts?: Array<{ message: string; severity?: string }>
  raw?: string
}

export interface QueryResult {
  cards: Array<{
    title: string
    series?: any[]
    data?: any[]
  }>
  sql?: string | null
  note?: string
  ai_insights?: AIInsights
  ai_model?: string
}

export interface CopilotCatalogEntry {
  id: string
  label?: string
  name?: string
  description?: string
  icon?: string | null
  category?: string | null
  module_ids?: string[]
  supports_ai_insights?: boolean
  write?: boolean
}

export interface CopilotCatalog {
  modules: CopilotCatalogEntry[]
  topics: CopilotCatalogEntry[]
  actions: CopilotCatalogEntry[]
}

export interface Suggestion {
  type: 'inventory' | 'sales' | 'finance'
  priority: 'high' | 'medium' | 'low'
  content: string
  action: string
  count?: number
}

export interface SuggestionsResult {
  suggestions: Suggestion[]
  generated_at: string
  ai_enabled: boolean
}

export interface ActionResult {
  id?: number | string
  status?: string
  [key: string]: any
}

export async function askCopilot(payload: AskPayload): Promise<QueryResult> {
  return api.post(TENANT_AI.ask, payload).then(r => r.data)
}

export async function actCopilot(payload: ActPayload): Promise<ActionResult> {
  return api.post(TENANT_AI.act, payload).then(r => r.data)
}

export async function getCopilotCatalog(): Promise<CopilotCatalog> {
  return api.get(TENANT_AI.catalog).then(r => r.data)
}

export async function createInvoiceDraft(data: {
  proveedor: string
  cliente_id?: number
  subtotal: number
  iva: number
  total: number
}): Promise<ActionResult> {
  return actCopilot({
    action: 'create_invoice_draft',
    payload: data
  })
}

export async function createOrderDraft(data: {
  customer_id: number
  items?: Array<{
    product_id: number
    qty: number
    unit_price: number
  }>
}): Promise<ActionResult> {
  return actCopilot({
    action: 'create_order_draft',
    payload: data
  })
}

export async function createTransferDraft(data: {
  from_warehouse_id: number
  to_warehouse_id: number
  product_id: number
  qty: number
}): Promise<ActionResult> {
  return actCopilot({
    action: 'create_transfer_draft',
    payload: data
  })
}

export async function suggestOverlayFields(): Promise<ActionResult> {
  return actCopilot({
    action: 'suggest_overlay_fields'
  })
}

export async function querySalesByMonth(): Promise<QueryResult> {
  return askCopilot({ topic: 'ventas_mes' })
}

export async function querySalesByWarehouse(): Promise<QueryResult> {
  return askCopilot({ topic: 'ventas_por_almacen' })
}

export async function queryTopProducts(): Promise<QueryResult> {
  return askCopilot({ topic: 'top_productos' })
}

export async function queryLowStock(threshold: number = 5): Promise<QueryResult> {
  return askCopilot({
    topic: 'stock_bajo',
    params: { threshold }
  })
}

export async function queryPendingSubmissions(): Promise<QueryResult> {
  return askCopilot({ topic: 'pendientes_sri_sii' })
}

export async function queryPaymentMovements(): Promise<QueryResult> {
  return askCopilot({ topic: 'cobros_pagos' })
}

export async function getSuggestions(): Promise<SuggestionsResult> {
  return api.get(TENANT_AI.suggestions).then(r => r.data)
}

// Variantes con insights de IA
export async function querySalesByMonthWithInsights(): Promise<QueryResult> {
  return askCopilot({ topic: 'ventas_mes', params: {} }).catch(() => ({
    cards: [{ title: 'Ventas por Mes', series: [] }]
  }))
}

export async function queryTopProductsWithInsights(): Promise<QueryResult> {
  return askCopilot({ topic: 'top_productos' }).catch(() => ({
    cards: [{ title: 'Top Productos', data: [] }]
  }))
}

export async function queryLowStockWithInsights(threshold: number = 5): Promise<QueryResult> {
  return askCopilot({
    topic: 'stock_bajo',
    params: { threshold }
  }).catch(() => ({
    cards: [{ title: 'Stock Bajo', data: [] }]
  }))
}
