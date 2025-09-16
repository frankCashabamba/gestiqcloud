import type { Asiento } from '../types/movimiento'

export const mockMovimientos: Asiento[] = [
  {
    id: 1,
    fecha: '2025-01-01',
    concepto: 'Apertura',
    apuntes: [
      { cuenta: '1001', descripcion: 'Caja', debe: 1000, haber: 0 },
      { cuenta: '2001', descripcion: 'Capital', debe: 0, haber: 1000 },
    ],
  },
]

