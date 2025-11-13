import tenantApi from '../../../shared/api/client'
import { ensureArray } from '../../../shared/utils/array'

export type Nomina = {
    id: string
    numero?: string
    empleado_id: string
    periodo_mes: number
    periodo_ano: number
    tipo?: string
    salario_base: number
    complementos?: number
    horas_extra?: number
    otros_devengos?: number
    seg_social?: number
    irpf?: number
    otras_deducciones?: number
    total_devengado?: number
    total_deducido?: number
    liquido_total?: number
    status?: 'draft' | 'calculated' | 'approved' | 'paid' | 'cancelled'
    fecha_pago?: string
    metodo_pago?: string
    created_at?: string
    updated_at?: string
}

export async function listNominas(): Promise<Nomina[]> {
    const { data } = await tenantApi.get<Nomina[] | { items?: Nomina[] }>('/api/v1/rrhh/nominas')
    return ensureArray<Nomina>(data)
}

export async function getNomina(id: string): Promise<Nomina> {
    const { data } = await tenantApi.get<Nomina>(`/api/v1/rrhh/nominas/${id}`)
    return data
}

export async function createNomina(payload: Omit<Nomina, 'id'>): Promise<Nomina> {
    const { data } = await tenantApi.post<Nomina>('/api/v1/rrhh/nominas', payload)
    return data
}

export async function updateNomina(id: string, payload: Partial<Nomina>): Promise<Nomina> {
    const { data } = await tenantApi.put<Nomina>(`/api/v1/rrhh/nominas/${id}`, payload)
    return data
}

export async function removeNomina(id: string): Promise<void> {
    await tenantApi.delete(`/api/v1/rrhh/nominas/${id}`)
}

export async function calculateNomina(id: string): Promise<Nomina> {
    const { data } = await tenantApi.post<Nomina>(`/api/v1/rrhh/nominas/${id}/calculate`, {})
    return data
}

export async function approveNomina(id: string): Promise<Nomina> {
    const { data } = await tenantApi.post<Nomina>(`/api/v1/rrhh/nominas/${id}/approve`, {})
    return data
}

export async function payNomina(id: string, payload: { metodo_pago: string; fecha_pago: string }): Promise<Nomina> {
    const { data } = await tenantApi.post<Nomina>(`/api/v1/rrhh/nominas/${id}/pay`, payload)
    return data
}
