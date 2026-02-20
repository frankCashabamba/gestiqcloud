import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_SALES } from '@shared/endpoints'
import { queueDeletion, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue, isOfflineQueuedResponse, stripOfflineMeta } from '../../lib/offlineHttp'

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
    total?: number | null
    subtotal?: number
    impuesto?: number
    estado?: string
    notas?: string
    lineas?: VentaLinea[]
    created_at?: string
    updated_at?: string
}

function normalizeEstado(raw: any): string | undefined {
    const s = String(raw || '').trim().toLowerCase()
    if (!s) return undefined
    if (s === 'draft') return 'borrador'
    if (s === 'confirmed') return 'emitida'
    if (s === 'voided' || s === 'cancelled') return 'anulada'
    if (s === 'invoiced') return 'facturada'
    return s
}

function toISODate(value: any): string {
    if (!value) return ''
    const s = String(value)
    // already yyyy-mm-dd
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s
    // ISO datetime
    const d = new Date(s)
    if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 10)
    return s.slice(0, 10)
}

function mapToVenta(row: any): Venta {
  const id = row?.id ?? row?.sale_id ?? row?.order_id
  const numero = row?.numero ?? row?.number ?? row?.sequential ?? row?.invoice_number
  const fecha = toISODate(row?.fecha ?? row?.order_date ?? row?.orderDate ?? row?.created_at ?? row?.createdAt)
  const totalNum = row?.total ?? row?.grand_total ?? row?.amount_total
  const total = totalNum === null || totalNum === undefined ? null : Number(totalNum)
  const subtotalNum = row?.subtotal ?? row?.sub_total
  const impuestoNum = row?.impuesto ?? row?.tax ?? row?.iva ?? row?.tax_total
  const rawLineas =
    row?.lineas ||
    row?.lines ||
    row?.items ||
    row?.order_lines ||
    row?.orderLines ||
    row?.sale_lines ||
    row?.saleLines ||
    row?.products ||
    []
  const lineas = Array.isArray(rawLineas)
    ? rawLineas.map((l: any) => ({
        producto_id: l?.producto_id ?? l?.product_id ?? l?.id,
        producto_nombre: l?.producto_nombre ?? l?.product_name ?? l?.name,
        cantidad: Number(l?.cantidad ?? l?.quantity ?? 1),
        precio_unitario: Number(l?.precio_unitario ?? l?.unit_price ?? l?.price ?? 0),
        descuento: Number(l?.descuento ?? l?.discount ?? 0) || undefined,
        impuesto_tasa: Number(l?.impuesto_tasa ?? l?.tax_rate ?? l?.tax ?? 0) || undefined,
      }))
    : []

  return {
    id,
    numero: numero ? String(numero) : undefined,
    fecha: fecha || toISODate(new Date().toISOString()),
    cliente_id: row?.cliente_id ?? row?.customer_id ?? row?.customerId,
    cliente_nombre: row?.cliente_nombre ?? row?.customer_name ?? row?.customerName ?? row?.buyer_name,
    total: Number.isFinite(total as number) ? (total as number) : null,
    subtotal: subtotalNum !== undefined ? Number(subtotalNum) : undefined,
    impuesto: impuestoNum !== undefined ? Number(impuestoNum) : undefined,
    estado: normalizeEstado(row?.estado ?? row?.status),
    notas: row?.notas ?? row?.notes,
    lineas,
    created_at: row?.created_at ?? row?.createdAt,
    updated_at: row?.updated_at ?? row?.updatedAt,
  }
}

export async function listVentas(): Promise<Venta[]> {
    const { data } = await tenantApi.get<Venta[] | { items?: Venta[] }>(TENANT_SALES.base)
    const rows = ensureArray<any>(data)
    return rows.map(mapToVenta)
}

export async function getVenta(id: number | string): Promise<Venta> {
    const { data } = await tenantApi.get<any>(TENANT_SALES.byId(id))
    return mapToVenta(data)
}

export async function createVenta(payload: Omit<Venta, 'id'>): Promise<Venta> {
    const cleanPayload = stripOfflineMeta(payload as any)
    try {
        const response = await tenantApi.post<any>(TENANT_SALES.base, cleanPayload, { headers: { 'X-Offline-Managed': '1' } })
        if (isOfflineQueuedResponse(response)) {
            const tempId = createOfflineTempId('sale')
            await storeEntity('sale', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
            return mapToVenta({ ...cleanPayload, id: tempId, created_at: new Date().toISOString(), updated_at: new Date().toISOString() })
        }
        return mapToVenta(response.data)
    } catch (error) {
        if (isNetworkIssue(error)) {
            const tempId = createOfflineTempId('sale')
            await storeEntity('sale', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
            return mapToVenta({ ...cleanPayload, id: tempId, created_at: new Date().toISOString(), updated_at: new Date().toISOString() })
        }
        throw error
    }
}

export async function updateVenta(id: number | string, payload: Omit<Venta, 'id'>): Promise<Venta> {
    const cleanPayload = stripOfflineMeta(payload as any)
    try {
        const response = await tenantApi.put<any>(TENANT_SALES.byId(id), cleanPayload, { headers: { 'X-Offline-Managed': '1' } })
        if (isOfflineQueuedResponse(response)) {
            await storeEntity('sale', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
            return mapToVenta({ ...cleanPayload, id, updated_at: new Date().toISOString() })
        }
        return mapToVenta(response.data)
    } catch (error) {
        if (isNetworkIssue(error)) {
            await storeEntity('sale', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
            return mapToVenta({ ...cleanPayload, id, updated_at: new Date().toISOString() })
        }
        throw error
    }
}

export async function removeVenta(id: number | string): Promise<void> {
    try {
        const response = await tenantApi.delete(TENANT_SALES.byId(id), { headers: { 'X-Offline-Managed': '1' } })
        if (isOfflineQueuedResponse(response)) {
            await queueDeletion('sale', String(id))
        }
    } catch (error) {
        if (isNetworkIssue(error)) {
            await queueDeletion('sale', String(id))
            return
        }
        throw error
    }
}

export async function convertToInvoice(id: number | string): Promise<{ invoice_id: string }> {
    const { data } = await tenantApi.post<{ invoice_id: string }>(`${TENANT_SALES.byId(id)}/invoice`)
    return data
}
