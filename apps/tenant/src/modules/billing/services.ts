/**
 * Facturación Services - API calls para facturas y e-invoicing
 */

import tenantApi from '../../shared/api/client'
import { TENANT_INVOICING } from '@shared/endpoints'
import { ensureArray } from '../../shared/utils/array'
import { queueInvoiceForSync } from './offlineQueue'

// ============================================================================
// Cache para evitar rate limiting
// ============================================================================

const CACHE_TTL = 30000 // 30 segundos
let invoicesCache: {
    data: Invoice[]
    timestamp: number
} | null = null

// ============================================================================
// Facturas
// ============================================================================

export interface Invoice {
    id: number | string
    numero?: string
    fecha: string
    subtotal?: number
    iva?: number
    total: number
    estado?: string
    cliente_id?: number
    cliente_nombre?: string
    descripcion?: string
    lineas?: InvoiceLine[]
    tenant_id?: string
}

/**
 * Normalize status values to consistent format
 */
function normalizeEstado(raw: any): string | undefined {
    const s = String(raw || '').trim().toLowerCase()
    if (!s) return undefined
    // Normalize common status values
    if (s === 'draft' || s === 'borrador') return 'borrador'
    if (s === 'issued' || s === 'emitida' || s === 'confirmed' || s === 'posted') return 'emitida'
    if (s === 'voided' || s === 'anulada' || s === 'cancelled') return 'anulada'
    return s
}

/**
 * Normalize invoice data from API to consistent format
 */
function normalizeInvoice(raw: any): Invoice {
    const id = raw?.id ?? raw?.invoice_id
    const numero = raw?.numero ?? raw?.number ?? raw?.invoice_number ?? raw?.sequential
    const fecha = raw?.fecha ?? raw?.date ?? raw?.invoice_date ?? raw?.created_at ?? raw?.fecha_emision
    const total = raw?.total ?? raw?.grand_total ?? raw?.amount_total
    const subtotal = raw?.subtotal ?? raw?.sub_total ?? raw?.amount_subtotal
    const iva = raw?.iva ?? raw?.tax ?? raw?.impuesto ?? raw?.tax_total
    const rawEstado = raw?.estado ?? raw?.status ?? raw?.state ?? raw?.estado
    const lineas =
      raw?.lineas ??
      raw?.lines ??
      raw?.invoice_lines ??
      raw?.items ??
      raw?.order_lines ??
      raw?.orderLines ??
      raw?.sale_lines ??
      raw?.products ??
      []

    console.log('Available keys in raw:', Object.keys(raw))
    console.log('raw.lineas:', raw?.lineas)
    console.log('raw.lines:', raw?.lines)

    // Normalize lineas - handle both InvoiceLine format and LineaFactura format
    // Also handle POS lines from invoices created via POS receipts
    const normalizedLineas = Array.isArray(lineas)
      ? lineas.map((l: any) => {
          const cantidad = Number(l?.cantidad ?? l?.quantity ?? 1)
          const precio_unitario = Number(l?.precio_unitario ?? l?.unit_price ?? l?.price ?? 0)
          const total_linea = Number(l?.total ?? cantidad * precio_unitario)
          const description = l?.description ?? l?.descripcion ?? l?.product_name ?? l?.name ?? ''

          console.log('Normalizing line:', l)

          return {
            cantidad,
            precio_unitario,
            total: total_linea,
            description,
            sku: l?.sku,
          }
        })
      : []

    console.log('Raw invoice data:', raw)
    console.log('Normalized lineas:', normalizedLineas)

    return {
        id,
        numero: numero ? String(numero) : undefined,
        fecha: String(fecha || ''),
        subtotal: subtotal !== undefined ? Number(subtotal) : undefined,
        iva: iva !== undefined ? Number(iva) : undefined,
        total: Number(total || 0),
        estado: normalizeEstado(rawEstado),
        cliente_id: raw?.cliente_id ?? raw?.customer_id ?? raw?.customerId,
        cliente_nombre: raw?.cliente_nombre ?? raw?.customer_name ?? raw?.cliente?.name,
        descripcion: raw?.descripcion ?? raw?.description,
        lineas: normalizedLineas,
        tenant_id: raw?.tenant_id ?? raw?.tenantId,
    }
}

export interface InvoiceCreate {
    numero?: string
    fecha: string
    subtotal?: number
    iva?: number
    total: number
    estado?: string
    cliente_id?: number
    lineas?: Array<InvoiceLine | Record<string, any>>
}

export interface InvoiceLine {
    cantidad?: number
    precio_unitario?: number
    total?: number
    description?: string
    sku?: string
    quantity?: number
    unit_price?: number
}

export async function listInvoices(params?: {
    estado?: string
    cliente_id?: number
    desde?: string
    hasta?: string
}): Promise<Invoice[]> {
    // Si no hay filtros y hay cache válido, retornar del cache
    if (!params && invoicesCache && Date.now() - invoicesCache.timestamp < CACHE_TTL) {
        return invoicesCache.data
    }

    try {
        const { data } = await tenantApi.get(TENANT_INVOICING.base, { params })
        const rawInvoices = ensureArray<any>(data)
        const invoices = rawInvoices.map(normalizeInvoice)

        // Cachear si no hay filtros
        if (!params) {
            invoicesCache = {
                data: invoices,
                timestamp: Date.now(),
            }
        }

        return invoices
    } catch (error) {
        console.error('Error fetching invoices:', error)
        throw error
    }
}

/**
 * Limpia el cache de facturas (llamar después de crear/editar)
 */
export function clearInvoicesCache() {
    invoicesCache = null
}

export async function getInvoice(id: number | string): Promise<Invoice> {
    const { data } = await tenantApi.get(TENANT_INVOICING.byId(String(id)))
    return normalizeInvoice(data)
}

function isNetworkIssue(error: any): boolean {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return true
    const msg = (error?.message || '').toLowerCase()
    return msg.includes('network') || msg.includes('failed to fetch') || msg.includes('timeout') || msg.includes('offline')
}

export async function createInvoice(invoice: InvoiceCreate | Partial<InvoiceCreate>): Promise<Invoice> {
    const payload = {
        ...invoice,
        lineas: (invoice.lineas || []).map((l) => ({
            description: l.description,
            quantity: l.cantidad ?? l.quantity,
            unit_price: l.precio_unitario ?? l.unit_price,
            total: l.total ?? (l.cantidad ?? l.quantity ?? 0) * (l.precio_unitario ?? l.unit_price ?? 0),
            sku: l.sku,
        })),
        date: (invoice as any)?.fecha || (invoice as any)?.date,
    }

    try {
        const { data } = await tenantApi.post(TENANT_INVOICING.base, payload)
        return normalizeInvoice(data)
    } catch (error) {
        if (isNetworkIssue(error)) {
            const tempId = await queueInvoiceForSync(payload, 'create')
            console.warn('[offline] Invoice queued for sync (create):', tempId)
            return normalizeInvoice({ ...payload, id: tempId })
        }
        throw error
    }
}

export async function updateInvoice(id: number | string, invoice: Partial<Invoice>): Promise<Invoice> {
    const payload = {
        ...invoice,
        lineas: (invoice.lineas || []).map((l) => ({
            description: l.description,
            quantity: l.cantidad ?? l.quantity,
            unit_price: l.precio_unitario ?? l.unit_price,
            total: l.total ?? (l.cantidad ?? l.quantity ?? 0) * (l.precio_unitario ?? l.unit_price ?? 0),
            sku: l.sku,
        })),
        date: (invoice as any)?.fecha || (invoice as any)?.date,
    }

    try {
        const { data } = await tenantApi.put(TENANT_INVOICING.byId(String(id)), payload)
        return normalizeInvoice(data)
    } catch (error) {
        if (isNetworkIssue(error)) {
            const tempId = await queueInvoiceForSync({ ...payload, id }, 'update')
            console.warn('[offline] Invoice queued for sync (update):', tempId)
            return normalizeInvoice({ ...payload, id: tempId })
        }
        throw error
    }
}

export async function deleteInvoice(id: number | string): Promise<void> {
    await tenantApi.delete(TENANT_INVOICING.byId(String(id)))
}

// ============================================================================
// E-invoicing
// ============================================================================

export interface EinvoiceSendRequest {
    invoice_id: string
    country: 'ES' | 'EC'
}

export interface EinvoiceStatus {
    invoice_id: string
    status: string
    clave_acceso?: string
    error_message?: string
    submitted_at?: string
    created_at: string
}

export async function sendEinvoice(request: EinvoiceSendRequest): Promise<{ task_id: string }> {
    const { data } = await tenantApi.post('/api/v1/tenant/einvoicing/send', request)
    return data
}

export async function getEinvoiceStatus(invoiceId: string): Promise<EinvoiceStatus> {
    try {
        const { data } = await tenantApi.get(`/api/v1/tenant/einvoicing/status/${invoiceId}`)
        return data
    } catch (err: any) {
        if (err?.response?.status === 404) {
            // No hay estado aún -> tratar como no enviado
            return null as any
        }
        throw err
    }
}

// ============================================================================
// Re-export Spanish aliases expected by UI components
// ============================================================================

export type Factura = Invoice
export type FacturaCreate = InvoiceCreate

export async function listFacturas(params?: {
    estado?: string
    cliente_id?: number
    desde?: string
    hasta?: string
}): Promise<Factura[]> {
    return listInvoices(params)
}

export async function getFactura(id: number | string): Promise<Factura> {
    return getInvoice(id)
}

export async function createFactura(invoice: FacturaCreate | Partial<FacturaCreate>): Promise<Factura> {
    return createInvoice(invoice)
}

export async function updateFactura(id: number | string, invoice: Partial<Factura>): Promise<Factura> {
    return updateInvoice(id, invoice)
}

export async function removeFactura(id: number | string): Promise<void> {
    return deleteInvoice(id)
}

// Stub for Facturae export (downloads XML); adjust endpoint when backend is ready
export async function exportarFacturae(id: string | number): Promise<Blob> {
    const res = await tenantApi.get(`/einvoicing/facturae/${id}/export`, {
        responseType: 'blob'
    })
    return res.data as Blob
}

// ============================================================================
// Utilidades
// ============================================================================

export function formatInvoiceNumber(invoice: Invoice): string {
    return invoice.numero || `INV-${invoice.id}`
}

export function getInvoiceStatusColor(status: string): string {
    const colors = {
        'draft': 'gray',
        'sent': 'blue',
        'paid': 'green',
        'overdue': 'red',
        'cancelled': 'red'
    }
    return colors[status as keyof typeof colors] || 'gray'
}

export function getEinvoiceStatusColor(status: string): string {
    const colors = {
        'PENDING': 'yellow',
        'SENT': 'blue',
        'RECEIVED': 'blue',
        'AUTHORIZED': 'green',
        'ACCEPTED': 'green',
        'REJECTED': 'red',
        'ERROR': 'red'
    }
    return colors[status as keyof typeof colors] || 'gray'
}
