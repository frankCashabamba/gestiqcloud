import tenantApi from '../../shared/api/client'
import { TENANT_RRHH } from '@shared/endpoints'

export type Vacacion = { id: number | string; usuario_id: number | string; inicio: string; fin: string; estado?: string }

export async function listVacaciones(): Promise<Vacacion[]> {
  const { data } = await tenantApi.get<Vacacion[]>(TENANT_RRHH.vacaciones.base)
  return data || []
}

