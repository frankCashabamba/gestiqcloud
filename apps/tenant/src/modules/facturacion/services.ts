/**
 * Facturación Services - Extendido con E-factura
 */
import tenantApi from '../../shared/api/client'

export type Invoice = {
  id: string
  numero?: string
  fecha: string
  cliente_id?: number
  subtotal: number
  impuesto: number
  total: number
  estado: string
  created_at: string
}

export type EInvoiceStatus = {
  invoice_id: string
  country: string
  status: string
  clave_acceso?: string
  error_message?: string
  submitted_at?: string
}

export type Credentials = {
  country: string
  has_certificate: boolean
  sandbox: boolean
  last_updated?: string
}

const BASE = '/api/v1/invoices'
const EINV = '/api/v1/einvoicing'

// Facturas básicas
export async function listInvoices(params?: any): Promise<Invoice[]> {
  const { data } = await tenantApi.get<Invoice[]>(BASE, { params })
  return Array.isArray(data) ? data : (data as any)?.items || []
}

export async function getInvoice(id: string): Promise<Invoice> {
  const { data } = await tenantApi.get<Invoice>(`${BASE}/${id}`)
  return data
}

// E-factura
export async function sendEInvoice(invoiceId: string, country: string) {
  const { data } = await tenantApi.post(`${EINV}/send`, { invoice_id: invoiceId, country })
  return data
}

export async function getEInvoiceStatus(invoiceId: string, country: string = 'EC'): Promise<EInvoiceStatus> {
  const { data } = await tenantApi.get<EInvoiceStatus>(`${EINV}/status/${invoiceId}?country=${country}`)
  return data
}

export async function retrySRI(invoiceId: string) {
  const { data } = await tenantApi.post(`${EINV}/sri/retry`, { invoice_id: invoiceId })
  return data
}

export async function exportFacturae(invoiceId: string): Promise<Blob> {
  const response = await fetch(`/api/v1/einvoicing/facturae/${invoiceId}/export`, {
    credentials: 'include',
  })
  return response.blob()
}

export async function getCredentials(country: string = 'EC'): Promise<Credentials> {
  const { data } = await tenantApi.get<Credentials>(`${EINV}/credentials?country=${country}`)
  return data
}

export async function updateCredentials(country: string, sandbox: boolean, certFile?: File) {
  const formData = new FormData()
  formData.append('country', country)
  formData.append('sandbox', String(sandbox))
  if (certFile) {
    formData.append('cert_file', certFile)
  }
  
  const { data } = await tenantApi.put(`${EINV}/credentials`, formData)
  return data
}
