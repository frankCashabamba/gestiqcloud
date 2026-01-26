import tenantApi from '../../shared/api/client'
import { TENANT_CASHBOX, TENANT_BANKS } from '@shared/endpoints'
import type { Movimiento, MovimientoBanco, SaldosResumen } from './types'

// Re-export types
export type { Movimiento, MovimientoBanco, SaldosResumen }

export async function listCaja(): Promise<Movimiento[]> {
  try {
    const { data } = await tenantApi.get<any>(TENANT_CASHBOX.base)
    const items: any[] = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
    return items.map((m) => {
      const tipoRaw = (m.tipo || m.type || '').toString().toLowerCase()
      const tipo: 'ingreso' | 'egreso' =
        tipoRaw === 'expense' || tipoRaw === 'egreso' || Number(m.amount || 0) < 0
          ? 'egreso'
          : 'ingreso'
      const monto = typeof m.importe !== 'undefined' ? m.importe : m.amount
      return {
        id: m.id,
        fecha: m.fecha || m.date || m.created_at || '',
        concepto: m.concepto || m.descripcion || m.description || '',
        tipo,
        monto: Number(monto || 0),
        referencia: m.ref_doc_id,
        cuenta: m.caja_id || m.cash_box_id,
        conciliado: m.conciliado ?? true,
        created_at: m.created_at,
      } as Movimiento
    })
  } catch (error) {
    console.error('Error loading caja:', error)
    return []
  }
}

export async function listBancos(): Promise<MovimientoBanco[]> {
  try {
    const { data } = await tenantApi.get<any>(TENANT_BANKS.base)
    const items: any[] = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
    return items.map((m) => {
      const tipoRaw = (m.tipo || m.type || '').toString().toLowerCase()
      const tipo: 'ingreso' | 'egreso' =
        tipoRaw === 'expense' || tipoRaw === 'egreso' || Number(m.amount || 0) < 0
          ? 'egreso'
          : 'ingreso'
      return {
        id: m.id,
        fecha: m.fecha || m.date || m.created_at || '',
        concepto: m.concepto || m.descripcion || m.description || '',
        tipo,
        monto: Number(m.monto ?? m.amount ?? 0),
        referencia: m.ref_doc_id || m.reference,
        cuenta: m.account_id,
        banco: m.banco || m.bank || '',
        numero_cuenta: m.numero_cuenta || m.account_number || '',
        conciliado: m.conciliado ?? m.status === 'RECONCILED',
        created_at: m.created_at,
      } as MovimientoBanco
    })
  } catch (error) {
    console.error('Error loading bancos:', error)
    return []
  }
}

export async function getSaldos(): Promise<SaldosResumen> {
  try {
    const { data } = await tenantApi.get<SaldosResumen>(TENANT_BANKS.balances)
    return data
  } catch (error) {
    console.error('Error loading saldos:', error)
    return {
      caja_total: 0,
      bancos_total: 0,
      total_disponible: 0,
      pendiente_conciliar: 0,
      ultimo_update: new Date().toISOString(),
    }
  }
}

export async function conciliarMovimiento(id: number | string): Promise<MovimientoBanco> {
  const { data } = await tenantApi.post<MovimientoBanco>(`${TENANT_BANKS.base}/${id}/conciliar`)
  return data
}

export async function createMovimientoCaja(payload: Omit<Movimiento, 'id'>): Promise<Movimiento> {
  const { data } = await tenantApi.post<Movimiento>(TENANT_CASHBOX.base, payload)
  return data
}

export async function createMovimientoBanco(
  payload: Omit<MovimientoBanco, 'id'>,
): Promise<MovimientoBanco> {
  const { data } = await tenantApi.post<MovimientoBanco>(TENANT_BANKS.base, payload)
  return data
}
