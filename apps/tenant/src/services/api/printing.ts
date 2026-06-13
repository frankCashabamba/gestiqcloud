import api from '../../shared/api/client'
import { TENANT_PRINTING } from '@shared/endpoints'

const BASE = TENANT_PRINTING.base

export interface ReceiptConfig {
  footer_message: string
  show_tax_breakdown: boolean
  show_cashier: boolean
  show_customer: boolean
  custom_header: string
  custom_footer: string
}

export interface ReceiptPreviewResponse {
  preview: string
}

export async function getReceiptSettings(): Promise<ReceiptConfig> {
  const { data } = await api.get<ReceiptConfig>(`${BASE}/receipt-settings`)
  return data
}

export async function saveReceiptSettings(payload: ReceiptConfig): Promise<void> {
  await api.post(`${BASE}/receipt-settings`, payload)
}

export async function getReceiptPreview(): Promise<ReceiptPreviewResponse> {
  const { data } = await api.get<ReceiptPreviewResponse>(`${BASE}/receipt-preview`)
  return data
}
