export interface Compra {
  id: string
  tenant_id: string
  numero: string
  proveedor_id: string
  fecha: string
  fecha_entrega?: string
  subtotal: number
  impuestos: number
  total: number
  estado: 'draft' | 'confirmed' | 'received' | 'invoiced' | 'cancelled'
  notas?: string
  usuario_id: string
  created_at: string
  updated_at: string
}

export interface CompraLinea {
  id: string
  compra_id: string
  producto_id: string
  descripcion?: string
  cantidad: number
  cantidad_recibida: number
  precio_unitario: number
  descuento: number
  impuesto_tasa: number
  subtotal: number
  total: number
  created_at: string
}

export interface CompraCreate {
  numero: string
  proveedor_id: string
  fecha?: string
  fecha_entrega?: string
  subtotal?: number
  impuestos?: number
  total?: number
  estado?: 'draft' | 'confirmed' | 'received' | 'invoiced' | 'cancelled'
  notas?: string
}

export interface CompraUpdate extends Partial<CompraCreate> {}

export interface CompraRecepcion {
  compra_id: string
  lineas: Array<{
    linea_id: string
    cantidad_recibida: number
    lote?: string
    fecha_caducidad?: string
  }>
  notas?: string
}

export interface CompraStats {
  total_compras: number
  total_importe: number
  por_estado: Record<string, number>
  por_proveedor: Array<{
    proveedor_id: string
    proveedor_nombre: string
    total: number
  }>
  compras_por_mes: Array<{
    mes: string
    total: number
    cantidad: number
  }>
}

export interface CompraFilters {
  fecha_desde?: string
  fecha_hasta?: string
  proveedor_id?: string
  estado?: string
  search?: string
}
