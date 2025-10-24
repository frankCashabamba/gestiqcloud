import type { Asiento } from '../types/movimiento'
import { mockMovimientos } from '../mock/mockMovimientos'

export async function fetchMovimientos(): Promise<Asiento[]> {
  // TODO: Reemplazar por llamada real a tenantApi cuando el backend esté disponible
  return new Promise((resolve) => setTimeout(() => resolve(mockMovimientos), 200))
}

