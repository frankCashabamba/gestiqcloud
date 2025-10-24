/**
 * Pagos Services
 */
import tenantApi from '../../shared/api/client'

export type PaymentLink = {
  id: string
  invoice_id?: string
  amount: number
  currency: string
  provider: string
  url: string
  status: string
  created_at: string
}

const BASE = '/api/v1/payments'

export async function createPaymentLink(payload: {
  amount: number
  currency: string
  description: string
  invoice_id?: string
}): Promise<PaymentLink> {
  const { data } = await tenantApi.post<PaymentLink>(`${BASE}/link`, payload)
  return data
}

export async function listPaymentLinks(): Promise<PaymentLink[]> {
  const { data } = await tenantApi.get<PaymentLink[]>(`${BASE}/links`)
  return Array.isArray(data) ? data : (data as any)?.items || []
}
