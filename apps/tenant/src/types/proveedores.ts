export interface Proveedor {
  id: string
  tenant_id: string
  codigo?: string
  name: string
  nombre_comercial?: string
  tipo_documento: 'NIF' | 'CIF' | 'Foreigner ID' | 'RUC' | 'CEDULA' | 'PASAPORTE'
  numero_documento: string
  tax_id?: string
  email?: string
  phone?: string
  telefono?: string
  address?: string
  city?: string
  state?: string
  web?: string
  notas?: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface ProveedorContacto {
  id: string
  proveedor_id: string
  name: string
  cargo?: string
  email?: string
  phone?: string
  telefono?: string
  principal: boolean
  created_at: string
}

export interface ProveedorDireccion {
  id: string
  proveedor_id: string
  tipo: 'fiscal' | 'envio' | 'facturacion'
  address: string
  city?: string
  ciudad?: string
  state?: string
  provincia?: string
  codigo_postal?: string
  pais: string
  principal: boolean
  created_at: string
}

export interface ProveedorCreate {
  codigo?: string
  name: string
  nombre_comercial?: string
  tipo_documento: 'NIF' | 'CIF' | 'Foreigner ID' | 'RUC' | 'CEDULA' | 'PASAPORTE'
  numero_documento: string
  tax_id?: string
  email?: string
  phone?: string
  telefono?: string
  address?: string
  city?: string
  state?: string
  web?: string
  notas?: string
  active?: boolean
  activo?: boolean
}

export interface ProveedorUpdate extends Partial<ProveedorCreate> {}

export interface ProveedorStats {
  total_proveedores: number
  proveedores_activos: number
  total_compras: number
  total_importe_compras: number
  top_proveedores: Array<{
    proveedor_id: string
    proveedor_nombre: string
    total_compras: number
    total_importe: number
  }>
}

export interface ProveedorFilters {
  activo?: boolean
  tipo_documento?: string
  search?: string
}
