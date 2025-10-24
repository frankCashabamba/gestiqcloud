import type { Movimiento } from './types'

export const mockCaja: Movimiento[] = [
  { id: 1, fecha: '2025-01-01', concepto: 'Apertura de caja', monto: 100 },
  { id: 2, fecha: '2025-01-02', concepto: 'Venta contado', monto: 50 },
]

export const mockBancos: Movimiento[] = [
  { id: 1, fecha: '2025-01-03', concepto: 'Depósito', monto: 500 },
  { id: 2, fecha: '2025-01-05', concepto: 'Pago proveedor', monto: -200 },
]

