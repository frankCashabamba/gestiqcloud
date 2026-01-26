import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_SUPPLIERS } from '@shared/endpoints'

export type ProveedorContacto = {
  id?: number
  tipo: 'facturacion' | 'entrega' | 'administracion' | 'comercial' | 'soporte'
  name?: string | null
  nombre?: string | null
  email?: string | null
  phone?: string | null
  telefono?: string | null
  notas?: string | null
}

export type ProveedorDireccion = {
  id?: number
  tipo: 'facturacion' | 'entrega' | 'administracion' | 'otros'
  linea1: string
  linea2?: string | null
  address?: string | null
  city?: string | null
  ciudad?: string | null
  state?: string | null
  region?: string | null
  codigo_postal?: string | null
  pais?: string | null
  notas?: string | null
}

export type Proveedor = {
  id: number
  tenant_id: number
  name: string
  nombre_comercial?: string | null
  nif?: string | null
  tax_id?: string | null
  pais?: string | null
  idioma?: string | null
  email?: string | null
  phone?: string | null
  telefono?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  web?: string | null
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
  active?: boolean
  activo?: boolean
  contactos: ProveedorContacto[]
  direcciones: ProveedorDireccion[]
}

export type ProveedorPayload = {
  name: string
  nombre_comercial?: string | null
  nif?: string | null
  tax_id?: string | null
  pais?: string | null
  idioma?: string | null
  email?: string | null
  phone?: string | null
  telefono?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  web?: string | null
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
  active?: boolean
  activo?: boolean
  contactos: ProveedorContacto[]
  direcciones: ProveedorDireccion[]
}

export async function listProveedores(): Promise<Proveedor[]> {
  const { data } = await tenantApi.get<Proveedor[] | { items?: Proveedor[] }>(TENANT_SUPPLIERS.base)
  return ensureArray<Proveedor>(data)
}

export async function getProveedor(id: number | string): Promise<Proveedor> {
  const { data } = await tenantApi.get<Proveedor>(TENANT_SUPPLIERS.byId(id))
  return data
}

export async function createProveedor(payload: ProveedorPayload): Promise<Proveedor> {
  const { data } = await tenantApi.post<Proveedor>(TENANT_SUPPLIERS.base, payload)
  return data
}

export async function updateProveedor(id: number | string, payload: ProveedorPayload): Promise<Proveedor> {
  const { data } = await tenantApi.put<Proveedor>(TENANT_SUPPLIERS.byId(id), payload)
  return data
}

export async function removeProveedor(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_SUPPLIERS.byId(id))
}
