import tenantApi from '../../shared/api/client'
import { TENANT_CAJA, TENANT_BANCOS } from '@shared/endpoints'
import type { Movimiento } from './types'
import { mockCaja, mockBancos } from './mock'

export async function listCaja(): Promise<Movimiento[]> {
  // TODO: reemplazar por llamada real a tenantApi cuando exista backend
  // const { data } = await tenantApi.get<Movimiento[]>(TENANT_CAJA.base)
  // return data || []
  return new Promise((r) => setTimeout(() => r(mockCaja), 120))
}

export async function listBancos(): Promise<Movimiento[]> {
  // TODO: llamada real a tenantApi
  // const { data } = await tenantApi.get<Movimiento[]>(TENANT_BANCOS.base)
  // return data || []
  return new Promise((r) => setTimeout(() => r(mockBancos), 120))
}

