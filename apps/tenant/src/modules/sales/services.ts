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
    delivery_date?: string
    cliente_id?: number | string
    cliente_nombre?: string
    total?: number | null
    subtotal?: number
    impuesto?: number
    estado?: string
    notas?: string
    deposit_amount?: number
    deposit_paid?: boolean
    payment_method?: string
    lineas?: VentaLinea[]
    pos_receipt_id?: string
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
        cantidad: Number(l?.cantidad ?? l?.qty ?? l?.quantity ?? 1),
        precio_unitario: Number(l?.precio_unitario ?? l?.unit_price ?? l?.price ?? 0),
        descuento: Number(l?.descuento ?? l?.discount ?? 0) || undefined,
        impuesto_tasa: Number(l?.impuesto_tasa ?? l?.tax_rate ?? l?.tax ?? 0) || undefined,
      }))
    : []

  return {
    id,
    numero: numero ? String(numero) : undefined,
    fecha: fecha || toISODate(new Date().toISOString()),
    delivery_date: row?.delivery_date ?? row?.required_date ?? undefined,
    cliente_id: row?.cliente_id ?? row?.customer_id ?? row?.customerId,
    cliente_nombre: row?.cliente_nombre ?? row?.customer_name ?? row?.customerName ?? row?.buyer_name,
    total: Number.isFinite(total as number) ? (total as number) : null,
    subtotal: subtotalNum !== undefined ? Number(subtotalNum) : undefined,
    impuesto: impuestoNum !== undefined ? Number(impuestoNum) : undefined,
    estado: normalizeEstado(row?.estado ?? row?.status),
    notas: row?.notas ?? row?.notes,
    deposit_amount: row?.deposit_amount !== undefined ? Number(row.deposit_amount) : undefined,
    deposit_paid: row?.deposit_paid ?? false,
    payment_method: row?.payment_method ?? undefined,
    lineas,
    pos_receipt_id: row?.pos_receipt_id ?? undefined,
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

const STATUS_TO_BACKEND: Record<string, string> = {
    borrador: 'draft',
    emitida: 'confirmed',
    anulada: 'cancelled',
    facturada: 'invoiced',
}

function buildBackendCreatePayload(payload: Omit<Venta, 'id'>) {
    const items = (payload.lineas || []).map(l => ({
        product_id: String(l.producto_id),
        qty: l.cantidad,
        unit_price: l.precio_unitario,
        discount_pct: l.descuento || 0,
        tax_rate: l.impuesto_tasa ?? null,
    }))
    return {
        customer_id: payload.cliente_id ? String(payload.cliente_id) : null,
        currency: null,
        notes: payload.notas || null,
        required_date: (payload as any).delivery_date || null,
        deposit_amount: (payload as any).deposit_amount || 0,
        deposit_paid: (payload as any).deposit_paid || false,
        payment_method: (payload as any).payment_method || null,
        items,
    }
}

function buildBackendUpdatePayload(payload: Omit<Venta, 'id'>) {
    const items = (payload.lineas || []).map(l => ({
        product_id: String(l.producto_id),
        qty: l.cantidad,
        unit_price: l.precio_unitario,
        discount_pct: l.descuento || 0,
        tax_rate: l.impuesto_tasa ?? null,
    }))
    return {
        customer_id: payload.cliente_id ? String(payload.cliente_id) : null,
        currency: null,
        notes: payload.notas ?? null,
        required_date: (payload as any).delivery_date || null,
        deposit_amount: (payload as any).deposit_amount ?? null,
        deposit_paid: (payload as any).deposit_paid ?? null,
        payment_method: (payload as any).payment_method ?? null,
        status: payload.estado ? (STATUS_TO_BACKEND[payload.estado] ?? payload.estado) : null,
        items: items.length > 0 ? items : undefined,
    }
}

export async function createVenta(payload: Omit<Venta, 'id'>): Promise<Venta> {
    const cleanPayload = stripOfflineMeta(payload as any)
    const backendPayload = buildBackendCreatePayload(cleanPayload)
    try {
        const response = await tenantApi.post<any>(TENANT_SALES.base, backendPayload, { headers: { 'X-Offline-Managed': '1' } })
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
    const backendPayload = buildBackendUpdatePayload(cleanPayload)
    try {
        const response = await tenantApi.put<any>(TENANT_SALES.byId(id), backendPayload, { headers: { 'X-Offline-Managed': '1' } })
        if (isOfflineQueuedResponse(response)) {
            await storeEntity('sale', String(id), { ...backendPayload, _op: 'update' }, 'pending')
            return mapToVenta({ ...cleanPayload, id, updated_at: new Date().toISOString() })
        }
        return mapToVenta(response.data)
    } catch (error) {
        if (isNetworkIssue(error)) {
            await storeEntity('sale', String(id), { ...backendPayload, _op: 'update' }, 'pending')
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

/**
 * Ventas del POS (pos_receipt_id != null) NO son editables,
 * EXCEPTO si están en borrador (pendiente de cobro - mayoristas).
 */
export function isPosReadOnly(venta: Pick<Venta, 'pos_receipt_id' | 'estado'>): boolean {
    if (!venta.pos_receipt_id) return false          // no es POS → editable
    return venta.estado !== 'borrador'               // POS borrador → editable; resto → bloqueado
}

export async function convertToInvoice(id: number | string): Promise<{ invoice_id: string }> {
    const { data } = await tenantApi.post<{ invoice_id: string }>(`${TENANT_SALES.byId(id)}/invoice`)
    return data
}

export type CheckoutResult = {
    invoice_id: string
    invoice_number: string
    order_id: string
    expenses_created: number
    expense_total: number
    status: string
    message: string
    expense_note?: string | null
}

export async function checkoutOrder(
    id: string,
    opts?: { payment_method?: string; notes?: string }
): Promise<CheckoutResult> {
    const { data } = await tenantApi.post<CheckoutResult>(
        `${TENANT_SALES.byId(id)}/checkout`,
        opts ?? {}
    )
    return data
}

export async function cobrarVenta(venta: Venta): Promise<{ id: string; numero: string }> {
    const lineas = (venta.lineas || []).map(l => ({
        description: l.producto_nombre || String(l.producto_id),
        cantidad: l.cantidad,
        precio_unitario: l.precio_unitario,
        iva: l.impuesto_tasa ?? 0,
    }))
    const payload = {
        fecha_emision: venta.fecha,
        estado: 'emitida',
        subtotal: Number(venta.subtotal ?? 0),
        iva: Number(venta.impuesto ?? 0),
        total: Number(venta.total ?? 0),
        cliente_id: venta.cliente_id ? String(venta.cliente_id) : null,
        lineas,
    }
    const { data } = await tenantApi.post<any>('/invoicing', payload)
    return { id: String(data?.id ?? ''), numero: String(data?.numero ?? data?.number ?? '') }
}
