export type Movimiento = {
  id: number | string
  fecha: string
  concepto: string
  tipo: 'ingreso' | 'egreso'
  monto: number
  referencia?: string
  cuenta?: string
  conciliado?: boolean
  created_at?: string
}

export type MovimientoBanco = Movimiento & {
  banco: string
  numero_cuenta: string
  conciliado: boolean
}

export type SaldosResumen = {
  caja_total: number
  bancos_total: number
  total_disponible: number
  pendiente_conciliar: number
  ultimo_update: string
}
