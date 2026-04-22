/**
 * Invoice services for the tenant app.
 */

import tenantApi from '../../shared/api/client'
import { TENANT_INVOICING } from '@shared/endpoints'
import { ensureArray } from '../../shared/utils/array'
import { queueInvoiceDeletion, queueInvoiceForSync } from './offlineQueue'
import {
  createOfflineTempId,
  isNetworkIssue,
  isOfflineQueuedResponse,
  stripOfflineMeta,
} from '../../lib/offlineHttp'

const CACHE_TTL = 30000
let invoicesCache: {
  data: Invoice[]
  timestamp: number
} | null = null

export type InvoiceStatus = 'draft' | 'issued' | 'pending_payment' | 'voided' | string

export interface InvoiceLine {
  sector?: 'bakery' | 'workshop' | 'pos' | string
  description: string
  quantity: number
  unit_price: number
  tax_rate?: number
  amount?: number
  bread_type?: string
  grams?: number
  spare_part?: string
  labor_hours?: number
  rate?: number
  pos_receipt_line_id?: string
}

export interface Invoice {
  id: number | string
  number?: string
  issue_date?: string
  subtotal?: number
  tax?: number
  total: number
  status?: InvoiceStatus
  customer_id?: number | string
  customer_name?: string
  description?: string
  lines?: InvoiceLine[]
  tenant_id?: string
  notes?: string
  customer?: {
    id?: string
    name?: string
    email?: string
    tax_id?: string
  }
}

function normalizeStatus(raw: any): InvoiceStatus | undefined {
  const value = String(raw || '').trim().toLowerCase()
  if (!value) return undefined
  if (value === 'borrador') return 'draft'
  if (value === 'emitida') return 'issued'
  if (value === 'anulada' || value === 'cancelled') return 'voided'
  if (value === 'paid') return 'paid'
  if (value === 'pending_payment') return 'pending_payment'
  if (value === 'posted' || value === 'confirmed') return 'issued'
  return value
}

function normalizeLine(raw: any): InvoiceLine {
  return {
    sector: raw?.sector,
    description: String(raw?.description ?? raw?.descripcion ?? raw?.name ?? ''),
    quantity: Number(raw?.quantity ?? raw?.cantidad ?? raw?.qty ?? 1),
    unit_price: Number(raw?.unit_price ?? raw?.precio_unitario ?? raw?.price ?? 0),
    tax_rate: Number(raw?.tax_rate ?? raw?.iva ?? raw?.vat ?? 0),
    amount: Number(raw?.amount ?? raw?.total ?? 0),
    bread_type: raw?.bread_type,
    grams: raw?.grams !== undefined ? Number(raw.grams) : undefined,
    spare_part: raw?.spare_part,
    labor_hours: raw?.labor_hours !== undefined ? Number(raw.labor_hours) : undefined,
    rate: raw?.rate !== undefined ? Number(raw.rate) : undefined,
    pos_receipt_line_id: raw?.pos_receipt_line_id,
  }
}

function normalizeInvoice(raw: any): Invoice {
  const id = raw?.id ?? raw?.invoice_id
  const number = raw?.number ?? raw?.invoice_number ?? raw?.sequential ?? raw?.numero
  const rawDate = raw?.issue_date ?? raw?.date ?? raw?.invoice_date ?? raw?.created_at ?? raw?.fecha_emision
  const issueDate = rawDate ? String(rawDate).slice(0, 10) : undefined
  const status = normalizeStatus(raw?.status ?? raw?.state ?? raw?.estado)
  const total = raw?.total ?? raw?.grand_total ?? raw?.amount_total ?? raw?.amount ?? 0
  const subtotal = raw?.subtotal ?? raw?.sub_total ?? raw?.amount_subtotal
  const tax = raw?.tax ?? raw?.vat ?? raw?.iva ?? raw?.tax_total
  const lines = raw?.lines ?? raw?.lineas ?? raw?.invoice_lines ?? raw?.items ?? raw?.products ?? []
  const customer = raw?.customer ?? raw?.cliente ?? {}

  return {
    id,
    number: number ? String(number) : undefined,
    issue_date: issueDate,
    subtotal: subtotal !== undefined ? Number(subtotal) : undefined,
    tax: tax !== undefined ? Number(tax) : undefined,
    total: Number(total || 0),
    status,
    customer_id: raw?.customer_id ?? raw?.cliente_id ?? raw?.customerId,
    customer_name: raw?.customer_name ?? raw?.cliente_nombre ?? customer?.name ?? raw?.supplier,
    description: raw?.description ?? raw?.descripcion,
    lines: Array.isArray(lines) ? lines.map(normalizeLine) : [],
    tenant_id: raw?.tenant_id ?? raw?.tenantId,
    notes: raw?.notes ?? raw?.notas,
    customer: customer
      ? {
          id: customer.id ? String(customer.id) : undefined,
          name: customer.name,
          email: customer.email,
          tax_id: customer.tax_id ?? customer.identification ?? customer.identificacion,
        }
      : undefined,
  }
}

export interface InvoiceCreate {
  number?: string
  issue_date: string
  subtotal?: number
  tax?: number
  total: number
  status?: InvoiceStatus
  customer_id?: number | string
  customer_name?: string
  description?: string
  lines?: Array<InvoiceLine | Record<string, any>>
  notes?: string
}

function buildInvoicePayload(invoice: Partial<InvoiceCreate | Invoice>): Record<string, any> {
  const lines = (invoice.lines || []).map(serializeInvoiceLine)
  return stripOfflineMeta({
    number: invoice.number,
    issue_date: invoice.issue_date,
    subtotal: invoice.subtotal,
    tax: invoice.tax,
    total: invoice.total,
    status: invoice.status,
    customer_id: invoice.customer_id,
    lines,
  })
}

export async function listInvoices(params?: {
  status?: string
  customer_id?: number
  date_from?: string
  date_to?: string
  q?: string
}): Promise<Invoice[]> {
  if (!params && invoicesCache && Date.now() - invoicesCache.timestamp < CACHE_TTL) {
    return invoicesCache.data
  }

  const { data } = await tenantApi.get(TENANT_INVOICING.base, { params })
  const rawInvoices = ensureArray<any>(data)
  const invoices = rawInvoices.map(normalizeInvoice)

  if (!params) {
    invoicesCache = {
      data: invoices,
      timestamp: Date.now(),
    }
  }

  return invoices
}

export function clearInvoicesCache() {
  invoicesCache = null
}

export async function getInvoice(id: number | string): Promise<Invoice> {
  const { data } = await tenantApi.get(TENANT_INVOICING.byId(String(id)))
  return normalizeInvoice(data)
}

function serializeInvoiceLine(line: any): Record<string, any> {
  return {
    sector: line.sector ?? 'pos',
    description: line.description,
    quantity: line.quantity ?? line.cantidad ?? 1,
    unit_price: line.unit_price ?? line.precio_unitario ?? 0,
    tax_rate: line.tax_rate ?? line.iva ?? line.vat ?? 0,
    ...(line.bread_type ? { bread_type: line.bread_type } : {}),
    ...(line.grams !== undefined ? { grams: line.grams } : {}),
    ...(line.spare_part ? { spare_part: line.spare_part } : {}),
    ...(line.labor_hours !== undefined ? { labor_hours: line.labor_hours } : {}),
    ...(line.rate !== undefined ? { rate: line.rate } : {}),
    ...(line.pos_receipt_line_id ? { pos_receipt_line_id: line.pos_receipt_line_id } : {}),
    ...(line.amount !== undefined ? { amount: line.amount } : {}),
  }
}

export async function createInvoice(invoice: InvoiceCreate | Partial<InvoiceCreate>): Promise<Invoice> {
  const payload = buildInvoicePayload(invoice)

  try {
    const response = await tenantApi.post(TENANT_INVOICING.base, payload, {
      headers: { 'X-Offline-Managed': '1' },
    })
    if (isOfflineQueuedResponse(response)) {
      const tempId = createOfflineTempId('invoice')
      return normalizeInvoice({ ...payload, id: tempId })
    }
    return normalizeInvoice(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = await queueInvoiceForSync(payload, 'create')
      return normalizeInvoice({ ...payload, id: tempId })
    }
    throw error
  }
}

export async function updateInvoice(id: number | string, invoice: Partial<Invoice>): Promise<Invoice> {
  const payload = buildInvoicePayload(invoice)

  try {
    const response = await tenantApi.put(TENANT_INVOICING.byId(String(id)), payload, {
      headers: { 'X-Offline-Managed': '1' },
    })
    if (isOfflineQueuedResponse(response)) {
      return normalizeInvoice({ ...payload, id })
    }
    return normalizeInvoice(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = await queueInvoiceForSync({ ...payload, id }, 'update')
      return normalizeInvoice({ ...payload, id: tempId })
    }
    throw error
  }
}

export async function deleteInvoice(id: number | string): Promise<void> {
  try {
    const response = await tenantApi.delete(TENANT_INVOICING.byId(String(id)), {
      headers: { 'X-Offline-Managed': '1' },
    })
    if (isOfflineQueuedResponse(response)) {
      await queueInvoiceDeletion(String(id))
    }
  } catch (error) {
    if (isNetworkIssue(error)) {
      await queueInvoiceDeletion(String(id))
      return
    }
    throw error
  }
}

export interface EinvoiceSendRequest {
  invoice_id: string
  country: 'ES' | 'EC'
}

export interface EinvoiceStatus {
  invoice_id: string
  status: string
  access_key?: string
  error_message?: string
  submitted_at?: string
  created_at: string
}

export async function sendEinvoice(request: EinvoiceSendRequest): Promise<{ task_id: string }> {
  const { data } = await tenantApi.post('/api/v1/tenant/einvoicing/send', request)
  return data
}

export async function getEinvoiceStatus(invoiceId: string): Promise<EinvoiceStatus | null> {
  try {
    const { data } = await tenantApi.get(`/api/v1/tenant/einvoicing/status/${invoiceId}`)
    return data
  } catch (err: any) {
    if (err?.response?.status === 404) {
      return null
    }
    throw err
  }
}

export async function markInvoiceAsPaid(id: number | string): Promise<void> {
  await tenantApi.patch(TENANT_INVOICING.byId(String(id)) + '/mark-paid')
}

export async function exportInvoiceE(id: string | number): Promise<Blob> {
  const res = await tenantApi.get(`/einvoicing/facturae/${id}/export`, {
    responseType: 'blob',
  })
  return res.data as Blob
}

export function formatInvoiceNumber(invoice: Invoice): string {
  return invoice.number || `INV-${invoice.id}`
}

export function getInvoiceStatusColor(status: string): string {
  const colors = {
    draft: 'gray',
    issued: 'blue',
    pending_payment: 'amber',
    paid: 'green',
    voided: 'red',
  }
  return colors[status as keyof typeof colors] || 'gray'
}

export function getEinvoiceStatusColor(status: string): string {
  const colors = {
    PENDING: 'yellow',
    SENT: 'blue',
    RECEIVED: 'blue',
    AUTHORIZED: 'green',
    ACCEPTED: 'green',
    REJECTED: 'red',
    ERROR: 'red',
  }
  return colors[status as keyof typeof colors] || 'gray'
}
