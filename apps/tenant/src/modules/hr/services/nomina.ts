import { TENANT_HR } from '@shared/endpoints'
import tenantApi from '../../../shared/api/client'
import { ensureArray } from '../../../shared/utils/array'

export type PayrollSummary = {
  id: string
  payroll_month: string
  payroll_date: string
  status: 'DRAFT' | 'CONFIRMED' | 'PAID' | 'CANCELLED' | 'APPROVED' | string
  total_employees: number
  total_gross: string
  total_irpf: string
  total_social_security_employee: string
  total_social_security_employer: string
  total_deductions: string
  total_net: string
}

export type Nomina = PayrollSummary & {
  numero?: string
  empleado_id?: string
  periodo_mes?: number
  periodo_ano?: number
  tipo?: string
  salario_base?: number
  complementos?: number
  horas_extra?: number
  otros_devengos?: number
  seg_social?: number
  irpf?: number
  otras_deducciones?: number
  total_devengado?: number
  total_deducido?: number
  liquido_total?: number
  fecha_pago?: string
  metodo_pago?: string
  created_at?: string
  updated_at?: string
}

export type GeneratePayrollPayload = {
  payroll_month: string
  payroll_date: string
}

export async function listNominas(params?: {
  payrollMonth?: string
  status?: string
}): Promise<PayrollSummary[]> {
  const { data } = await tenantApi.get<PayrollSummary[] | { items?: PayrollSummary[] }>(
    TENANT_HR.payroll.base,
    { params }
  )
  return ensureArray<PayrollSummary>(data)
}

export async function getNomina(id: string): Promise<PayrollSummary> {
  const { data } = await tenantApi.get<PayrollSummary>(TENANT_HR.payroll.byId(id))
  return data
}

export async function createNomina(payload: GeneratePayrollPayload): Promise<PayrollSummary> {
  const { data } = await tenantApi.post<PayrollSummary>(TENANT_HR.payroll.generate, payload)
  return data
}

export async function approveNomina(id: string): Promise<PayrollSummary> {
  const { data } = await tenantApi.post<PayrollSummary>(TENANT_HR.payroll.confirm(id), {})
  return data
}

export async function payNomina(id: string): Promise<PayrollSummary> {
  const { data } = await tenantApi.post<PayrollSummary>(TENANT_HR.payroll.markPaid(id), {})
  return data
}

export async function removeNomina(id: string): Promise<void> {
  await tenantApi.delete(TENANT_HR.payroll.delete(id))
}

export async function updateNomina(id: string, payload: Partial<GeneratePayrollPayload>): Promise<PayrollSummary> {
  const { data } = await tenantApi.put<PayrollSummary>(TENANT_HR.payroll.byId(id), payload)
  return data
}

export async function calculateNomina(_id?: string): Promise<never> {
  throw new Error('Payroll calculation is handled by payroll generation in the current HR API')
}
