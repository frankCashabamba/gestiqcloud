import type { Asiento } from '../types/movimiento'

export function agruparPorCuenta(asientos: Asiento[]) {
  const mapa: Record<string, { debe: number; haber: number }> = {}
  for (const a of asientos) {
    for (const ap of a.apuntes) {
      const key = ap.cuenta
      if (!mapa[key]) mapa[key] = { debe: 0, haber: 0 }
      mapa[key].debe += ap.debe || 0
      mapa[key].haber += ap.haber || 0
    }
  }
  return mapa
}

