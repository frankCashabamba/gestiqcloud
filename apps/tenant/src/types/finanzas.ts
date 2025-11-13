export interface CajaMovimiento {
  id: string
  tenant_id: string
  caja_id: string
  tipo: 'entrada' | 'salida' | 'apertura' | 'cierre' | 'ajuste'
  concepto: string
  importe: number
  saldo_anterior: number
  saldo_posterior: number
  forma_pago: 'efectivo' | 'tarjeta' | 'transferencia' | 'cheque' | 'otro'
  referencia?: string
  ref_doc_type?: string
  ref_doc_id?: string
  notas?: string
  usuario_id: string
  fecha: string
  created_at: string
}

export interface Caja {
  id: string
  tenant_id: string
  name: string
  descripcion?: string
  saldo_actual: number
  active: boolean
  created_at: string
  updated_at: string
}

export interface BancoMovimiento {
  id: string
  tenant_id: string
  cuenta_id: string
  tipo: 'entrada' | 'salida' | 'apertura' | 'cierre' | 'ajuste'
  concepto: string
  importe: number
  saldo_anterior: number
  saldo_posterior: number
  fecha_valor: string
  referencia?: string
  ref_doc_type?: string
  ref_doc_id?: string
  conciliado: boolean
  fecha_conciliacion?: string
  notas?: string
  usuario_id: string
  created_at: string
}

export interface CuentaBancaria {
  id: string
  tenant_id: string
  banco: string
  numero_cuenta: string
  iban?: string
  swift?: string
  moneda: string
  saldo_actual: number
  active: boolean
  created_at: string
  updated_at: string
}

export interface CajaMovimientoCreate {
  caja_id: string
  tipo: 'entrada' | 'salida' | 'apertura' | 'cierre' | 'ajuste'
  concepto: string
  importe: number
  forma_pago: 'efectivo' | 'tarjeta' | 'transferencia' | 'cheque' | 'otro'
  referencia?: string
  ref_doc_type?: string
  ref_doc_id?: string
  notas?: string
  fecha?: string
}

export interface BancoMovimientoCreate {
  cuenta_id: string
  tipo: 'entrada' | 'salida' | 'apertura' | 'cierre' | 'ajuste'
  concepto: string
  importe: number
  fecha_valor?: string
  referencia?: string
  ref_doc_type?: string
  ref_doc_id?: string
  notas?: string
}

export interface FinanzasStats {
  saldo_total_cajas: number
  saldo_total_bancos: number
  liquidez_total: number
  movimientos_hoy: number
  ingresos_mes: number
  egresos_mes: number
  flujo_caja_mes: Array<{
    fecha: string
    ingresos: number
    egresos: number
    saldo: number
  }>
}

export interface FinanzasFilters {
  fecha_desde?: string
  fecha_hasta?: string
  caja_id?: string
  cuenta_id?: string
  tipo?: string
  conciliado?: boolean
  search?: string
}
