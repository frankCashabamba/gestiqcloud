import type { Asiento } from '../types/movimiento'
import api from '../../../shared/api/client'

export async function fetchMovimientos(): Promise<Asiento[]> {
  try {
    const { data } = await api.get<Asiento[] | { items?: Asiento[] }>(
      `/api/v1/tenant/accounting/movimientos`
    )
    if (Array.isArray(data)) return data
    const items = (data as any)?.items
    return Array.isArray(items) ? items : []
  } catch {
    return []
  }
}
