export interface Venta {
  id: string
  tenant_id: string
  numero: string
  cliente_id?: string
  fecha: string
  subtotal: number
  impuestos: number
  total: number
  estado: 'draft' | 'confirmed' | 'invoiced' | 'cancelled'
  notas?: string
  usuario_id: string
  created_at: string
  updated_at: string
}

export interface VentaLinea {
  id: string
  venta_id: string
  producto_id: string
  descripcion?: string
  cantidad: number
  precio_unitario: number
  descuento: number
  impuesto_tasa: number
  subtotal: number
  total: number
  created_at: string
}

export interface VentaCreate {
  numero: string
  cliente_id?: string
  fecha?: string
  subtotal?: number
  impuestos?: number
  total?: number
  estado?: 'draft' | 'confirmed' | 'invoiced' | 'cancelled'
  notas?: string
}

export interface VentaUpdate extends Partial<VentaCreate> {}

export interface VentaStats {
  total_ventas: number
  total_importe: number
  por_estado: Record<string, number>
  top_clientes: Array<{
    cliente_id: string
    cliente_nombre: string
    total: number
  }>
  ventas_por_mes: Array<{
    mes: string
    total: number
    cantidad: number
  }>
}

export interface VentaFilters {
  fecha_desde?: string
  fecha_hasta?: string
  cliente_id?: string
  estado?: string
  search?: string
}
