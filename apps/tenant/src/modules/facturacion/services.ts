/**
 * Facturación Services - API calls para facturas y e-invoicing
 */

import tenantApi from '../../shared/api/client'

// ============================================================================
// Facturas
// ============================================================================

export interface Invoice {
  id: number
  numero: string
  fecha: string
  subtotal: number
  iva: number
  total: number
  estado: string
  cliente_id: number
  tenant_id: string
}

export interface InvoiceCreate {
  numero: string
  fecha: string
  subtotal: number
  iva: number
  total: number
  cliente_id: number
  lineas: InvoiceLine[]
}

export interface InvoiceLine {
  cantidad: number
  precio_unitario: number
  total: number
  descripcion: string
  sku?: string
}

export async function listInvoices(params?: {
  estado?: string
  cliente_id?: number
  desde?: string
  hasta?: string
}): Promise<Invoice[]> {
  const { data } = await tenantApi.get('/facturacion/', { params })
  return data?.items || data || []
}

export async function getInvoice(id: number): Promise<Invoice> {
  const { data } = await tenantApi.get(`/facturacion/${id}`)
  return data
}

export async function createInvoice(invoice: InvoiceCreate): Promise<Invoice> {
  const { data } = await tenantApi.post('/facturacion/', invoice)
  return data
}

export async function updateInvoice(id: number, invoice: Partial<Invoice>): Promise<Invoice> {
  const { data } = await tenantApi.put(`/facturacion/${id}`, invoice)
  return data
}

export async function deleteInvoice(id: number): Promise<void> {
  await tenantApi.delete(`/facturacion/${id}`)
}

// ============================================================================
// E-invoicing
// ============================================================================

export interface EinvoiceSendRequest {
  invoice_id: string
  country: 'ES' | 'EC'
}

export interface EinvoiceStatus {
  invoice_id: string
  status: string
  clave_acceso?: string
  error_message?: string
  submitted_at?: string
  created_at: string
}

export async function sendEinvoice(request: EinvoiceSendRequest): Promise<{ task_id: string }> {
  const { data } = await tenantApi.post('/einvoicing/send', request)
  return data
}

export async function getEinvoiceStatus(invoiceId: string): Promise<EinvoiceStatus> {
  const { data } = await tenantApi.get(`/einvoicing/status/${invoiceId}`)
  return data
}

// ============================================================================
// Utilidades
// ============================================================================

export function formatInvoiceNumber(invoice: Invoice): string {
  return invoice.numero || `INV-${invoice.id}`
}

export function getInvoiceStatusColor(status: string): string {
  const colors = {
    'draft': 'gray',
    'sent': 'blue',
    'paid': 'green',
    'overdue': 'red',
    'cancelled': 'red'
  }
  return colors[status as keyof typeof colors] || 'gray'
}

export function getEinvoiceStatusColor(status: string): string {
  const colors = {
    'PENDING': 'yellow',
    'SENT': 'blue',
    'RECEIVED': 'blue',
    'AUTHORIZED': 'green',
    'ACCEPTED': 'green',
    'REJECTED': 'red',
    'ERROR': 'red'
  }
  return colors[status as keyof typeof colors] || 'gray'
}
