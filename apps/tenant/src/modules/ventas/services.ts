import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_VENTAS } from '@shared/endpoints'

export type VentaLinea = {
    producto_id: number | string
    producto_nombre?: string
    cantidad: number
    precio_unitario: number
    impuesto_tasa?: number
    descuento?: number
}

export type Venta = {
    id: number | string
    numero?: string
    fecha: string
    cliente_id?: number | string
    cliente_nombre?: string
    total: number
    subtotal?: number
    impuesto?: number
    estado?: string
    notas?: string
    lineas?: VentaLinea[]
    created_at?: string
    updated_at?: string
}

export async function listVentas(): Promise<Venta[]> {
    const { data } = await tenantApi.get<Venta[] | { items?: Venta[] }>(TENANT_VENTAS.base)
    return ensureArray<Venta>(data)
}

export async function getVenta(id: number | string): Promise<Venta> {
    const { data } = await tenantApi.get<Venta>(TENANT_VENTAS.byId(id))
    return data
}

export async function createVenta(payload: Omit<Venta, 'id'>): Promise<Venta> {
    const { data } = await tenantApi.post<Venta>(TENANT_VENTAS.base, payload)
    return data
}

export async function updateVenta(id: number | string, payload: Omit<Venta, 'id'>): Promise<Venta> {
    const { data } = await tenantApi.put<Venta>(TENANT_VENTAS.byId(id), payload)
    return data
}

export async function removeVenta(id: number | string): Promise<void> {
    await tenantApi.delete(TENANT_VENTAS.byId(id))
}

export async function convertToInvoice(id: number | string): Promise<{ invoice_id: string }> {
    const { data } = await tenantApi.post<{ invoice_id: string }>(`${TENANT_VENTAS.byId(id)}/invoice`)
    return data
}
