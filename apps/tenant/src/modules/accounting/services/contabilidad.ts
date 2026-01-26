import type { Asiento, Apunte } from '../types/movimiento'
import api from '../../../shared/api/client'

/**
 * Adapta la respuesta del backend (AsientoContableResponse) al tipo liviano usado en el dashboard.
 */
export async function fetchMovimientos(): Promise<Asiento[]> {
  try {
    const { data } = await api.get<any>(`/api/v1/tenant/accounting/transactions`)
    const items: any[] = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []

    return items.map((a: any) => {
      const apuntes: Apunte[] = Array.isArray(a.lineas)
        ? a.lineas.map((l: any) => ({
            cuenta: l.cuenta_codigo || l.cuenta_id || '',
            description: l.descripcion || l.description || '',
            debe: Number(l.debe || 0),
            haber: Number(l.haber || 0),
          }))
        : []

      return {
        id: a.id || a.numero,
        fecha: a.fecha || a.created_at || '',
        concepto: a.descripcion || a.description || '',
        apuntes,
      } as Asiento
    })
  } catch {
    return []
  }
}
