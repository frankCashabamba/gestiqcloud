import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type IrpfBracket = {
  min: number
  max: number
  rate: number
}

export type PayrollParams = {
  country: string
  year: number
  smi: number | null
  ss_employee_rate: number | null
  ss_employer_rate: number | null
  mutual_insurance_rate: number | null
  irpf_brackets: IrpfBracket[]
  updated_at: string | null
}

export type PayrollParamsPayload = Omit<PayrollParams, 'updated_at'>

export async function listPayrollParams(
  country?: string,
  year?: number,
): Promise<PayrollParams[]> {
  const params = new URLSearchParams()
  if (country) params.set('country', country)
  if (year) params.set('year', String(year))
  const query = params.toString() ? `?${params}` : ''
  const { data } = await api.get<PayrollParams[]>(`${ADMIN_CONFIG.payrollParams.base}${query}`)
  return data || []
}

export async function upsertPayrollParams(payload: PayrollParamsPayload): Promise<PayrollParams> {
  const { data } = await api.post<PayrollParams>(ADMIN_CONFIG.payrollParams.base, payload)
  return data
}

export async function deletePayrollParams(country: string, year: number): Promise<void> {
  await api.delete(ADMIN_CONFIG.payrollParams.byCountryYear(country, year))
}
