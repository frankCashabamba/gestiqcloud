/**
 * E-Invoicing Services - API calls for electronic invoicing
 */

import tenantApi from '../../shared/api/client'
import { TENANT_EINVOICING } from '@shared/endpoints'

export interface EInvoice {
  id: string
  invoice_id: string
  invoice_number?: string
  country: string
  status: 'pending' | 'sent' | 'accepted' | 'rejected' | 'error'
  submitted_at?: string
  response_code?: string
  response_message?: string
  xml_url?: string
  error_detail?: string
}

export interface SendSiiRequest {
  invoice_id: string
  period?: string
}

export interface EInvoiceStatusResponse {
  id: string
  status: string
  submitted_at?: string
  response_code?: string
  response_message?: string
  retries: number
}

export async function sendToSii(data: SendSiiRequest): Promise<EInvoice> {
  const res = await tenantApi.post(TENANT_EINVOICING.sendSii, data)
  return res.data
}

export async function getEInvoiceStatus(id: string): Promise<EInvoiceStatusResponse> {
  const res = await tenantApi.get(TENANT_EINVOICING.status(id))
  return res.data
}

export async function retryEInvoice(id: string): Promise<EInvoice> {
  const res = await tenantApi.post(TENANT_EINVOICING.retry(id))
  return res.data
}
