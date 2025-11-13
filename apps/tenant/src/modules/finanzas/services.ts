import tenantApi from '../../shared/api/client'
import { TENANT_CAJA, TENANT_BANCOS } from '@shared/endpoints'
import type { Movimiento, MovimientoBanco, SaldosResumen } from './types'

// Re-export types
export type { Movimiento, MovimientoBanco, SaldosResumen }

export async function listCaja(): Promise<Movimiento[]> {
  try {
    const { data } = await tenantApi.get<Movimiento[] | { items?: Movimiento[] }>(TENANT_CAJA.base)
    if (Array.isArray(data)) return data
    return (data as any)?.items || []
  } catch (error) {
    console.error('Error loading caja:', error)
    return []
  }
}

export async function listBancos(): Promise<MovimientoBanco[]> {
  try {
    const { data } = await tenantApi.get<MovimientoBanco[] | { items?: MovimientoBanco[] }>(TENANT_BANCOS.base)
    if (Array.isArray(data)) return data
    return (data as any)?.items || []
  } catch (error) {
    console.error('Error loading bancos:', error)
    return []
  }
}

export async function getSaldos(): Promise<SaldosResumen> {
  try {
    const { data } = await tenantApi.get<SaldosResumen>(TENANT_BANCOS.saldos)
    return data
  } catch (error) {
    console.error('Error loading saldos:', error)
    return {
      caja_total: 0,
      bancos_total: 0,
      total_disponible: 0,
      pendiente_conciliar: 0,
      ultimo_update: new Date().toISOString()
    }
  }
}

export async function conciliarMovimiento(id: number | string): Promise<MovimientoBanco> {
  const { data } = await tenantApi.post<MovimientoBanco>(`${TENANT_BANCOS.base}/${id}/conciliar`)
  return data
}

export async function createMovimientoCaja(payload: Omit<Movimiento, 'id'>): Promise<Movimiento> {
  const { data } = await tenantApi.post<Movimiento>(TENANT_CAJA.base, payload)
  return data
}

export async function createMovimientoBanco(payload: Omit<MovimientoBanco, 'id'>): Promise<MovimientoBanco> {
  const { data } = await tenantApi.post<MovimientoBanco>(TENANT_BANCOS.base, payload)
  return data
}
