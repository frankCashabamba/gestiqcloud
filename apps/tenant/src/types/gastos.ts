export interface Gasto {
  id: string
  tenant_id: string
  numero?: string
  categoria_id?: string
  proveedor_id?: string
  description: string
  fecha: string
  importe: number
  impuesto_tasa: number
  impuesto_importe: number
  total: number
  forma_pago: 'efectivo' | 'tarjeta' | 'transferencia' | 'cheque' | 'otro'
  referencia?: string
  estado: 'draft' | 'approved' | 'paid' | 'rejected'
  notas?: string
  factura_url?: string
  usuario_id: string
  created_at: string
  updated_at: string
}

export interface GastoCategoria {
  id: string
  tenant_id: string
  name: string
  descripcion?: string
  cuenta_contable?: string
  active: boolean
  created_at: string
}

export interface GastoCreate {
  numero?: string
  categoria_id?: string
  proveedor_id?: string
  description: string
  fecha?: string
  importe: number
  impuesto_tasa?: number
  impuesto_importe?: number
  total?: number
  forma_pago: 'efectivo' | 'tarjeta' | 'transferencia' | 'cheque' | 'otro'
  referencia?: string
  estado?: 'draft' | 'approved' | 'paid' | 'rejected'
  notas?: string
  factura_url?: string
}

export interface GastoUpdate extends Partial<GastoCreate> {}

export interface GastoStats {
  total_gastos: number
  total_importe: number
  por_categoria: Array<{
    categoria_id: string
    categoria_nombre: string
    total: number
  }>
  por_estado: Record<string, number>
  gastos_por_mes: Array<{
    mes: string
    total: number
    cantidad: number
  }>
  por_forma_pago: Record<string, number>
}

export interface GastoFilters {
  fecha_desde?: string
  fecha_hasta?: string
  categoria_id?: string
  proveedor_id?: string
  estado?: string
  forma_pago?: string
  search?: string
}
