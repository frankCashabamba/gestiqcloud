import tenantApi from '../../shared/api/client'
import { TENANT_PROVEEDORES } from '@shared/endpoints'

export type ProveedorContacto = {
  id?: number
  tipo: 'facturacion' | 'entrega' | 'administracion' | 'comercial' | 'soporte'
  nombre?: string | null
  email?: string | null
  telefono?: string | null
  notas?: string | null
}

export type ProveedorDireccion = {
  id?: number
  tipo: 'facturacion' | 'entrega' | 'administracion' | 'otros'
  linea1: string
  linea2?: string | null
  ciudad?: string | null
  region?: string | null
  codigo_postal?: string | null
  pais?: string | null
  notas?: string | null
}

export type Proveedor = {
  id: number
  empresa_id: number
  nombre: string
  nombre_comercial?: string | null
  nif?: string | null
  pais?: string | null
  idioma?: string | null
  email?: string | null
  telefono?: string | null
  tipo_impuesto?: string | null
  retencion_irpf?: number | null
  exento_impuestos: boolean
  regimen_especial?: string | null
  condiciones_pago?: string | null
  plazo_pago_dias?: number | null
  descuento_pronto_pago?: number | null
  divisa?: string | null
  metodo_pago?: string | null
  iban?: string | null
  iban_actualizado_por?: string | null
  iban_actualizado_at?: string | null
  contactos: ProveedorContacto[]
  direcciones: ProveedorDireccion[]
}

export type ProveedorPayload = {
  nombre: string
  nombre_comercial?: string | null
  nif?: string | null
  pais?: string | null
  idioma?: string | null
  email?: string | null
  telefono?: string | null
  tipo_impuesto?: string | null
  retencion_irpf?: number | null
  exento_impuestos?: boolean
  regimen_especial?: string | null
  condiciones_pago?: string | null
  plazo_pago_dias?: number | null
  descuento_pronto_pago?: number | null
  divisa?: string | null
  metodo_pago?: string | null
  iban?: string | null
  iban_confirmacion?: string | null
  contactos: ProveedorContacto[]
  direcciones: ProveedorDireccion[]
}

export async function listProveedores(): Promise<Proveedor[]> {
  const { data } = await tenantApi.get<Proveedor[] | { items?: Proveedor[] }>(TENANT_PROVEEDORES.base)
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function getProveedor(id: number | string): Promise<Proveedor> {
  const { data } = await tenantApi.get<Proveedor>(TENANT_PROVEEDORES.byId(id))
  return data
}

export async function createProveedor(payload: ProveedorPayload): Promise<Proveedor> {
  const { data } = await tenantApi.post<Proveedor>(TENANT_PROVEEDORES.base, payload)
  return data
}

export async function updateProveedor(id: number | string, payload: ProveedorPayload): Promise<Proveedor> {
  const { data } = await tenantApi.put<Proveedor>(TENANT_PROVEEDORES.byId(id), payload)
  return data
}

export async function removeProveedor(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_PROVEEDORES.byId(id))
}
