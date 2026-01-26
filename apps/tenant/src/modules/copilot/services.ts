import api from "../../services/api/client"

export type Topic = 'ventas_mes' | 'ventas_por_almacen' | 'top_productos' | 'stock_bajo' | 'pendientes_sri_sii' | 'cobros_pagos'

export type Action = 'create_invoice_draft' | 'create_order_draft' | 'create_transfer_draft' | 'suggest_overlay_fields'

export interface AskPayload {
  topic: Topic
  params?: Record<string, any>
}

export interface ActPayload {
  action: Action
  payload?: Record<string, any>
}

export interface QueryResult {
  cards: Array<{
    title: string
    series?: any[]
    data?: any[]
  }>
  sql?: string | null
  note?: string
}

export interface ActionResult {
  id?: number | string
  status?: string
  [key: string]: any
}

export async function askCopilot(payload: AskPayload): Promise<QueryResult> {
  return api.post('/ai/ask', payload).then(r => r.data)
}

export async function actCopilot(payload: ActPayload): Promise<ActionResult> {
  return api.post('/ai/act', payload).then(r => r.data)
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
