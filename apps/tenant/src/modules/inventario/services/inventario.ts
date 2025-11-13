import tenantApi from '../../../shared/api/client'
import type { Producto, Bodega, KardexEntry } from '../types/producto'
import type { StockAlert, NotificationChannel } from '../types/alertas'

const PRODUCTS_BASE = '/api/v1/tenant/products'
const INVENTORY_BASE = '/api/v1/tenant/inventory'

export async function fetchProductos(): Promise<Producto[]> {
  const { data } = await tenantApi.get<any>(`${PRODUCTS_BASE}`, { params: { limit: 200 } })
  const arr = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return (arr || []).map((p: any) => ({
    id: String(p.id),
    sku: p.sku || p?.product_metadata?.sku || String(p.id),
    name: p.name,
    stock: Number(p.stock ?? 0),
    price: Number(p.price ?? 0),
    categoria: p.category || p.categoria || '',
  }))
}

export async function updateProducto(id: string, data: Partial<Producto>): Promise<void> {
  await tenantApi.put(`${PRODUCTS_BASE}/${id}`, {
    name: data.name,
    price: data.price,
    stock: data.stock,
    category: data.categoria,
    sku: data.sku,
  })
}

export async function fetchBodegas(): Promise<Bodega[]> {
  const { data } = await tenantApi.get<any[]>(`${INVENTORY_BASE}/warehouses`)
  return (data || []).map((w: any) => ({ id: String(w.id), name: w.name, ubicacion: w?.metadata?.location }))
}

export async function fetchKardex(_productoId?: string | number): Promise<KardexEntry[]> {
  // Backend actual no expone historial (moves) en router de inventario
  // Devolvemos vacío hasta disponer de /stock/moves
  return []
}

// ========== Alertas de Stock ==========

export async function updateReorderPoint(productId: string, stockMinimo: number): Promise<void> {
  if (stockMinimo < 0) throw new Error('Stock mínimo debe ser mayor o igual a 0')
  await tenantApi.post(`${INVENTORY_BASE}/products/${productId}/reorder-point`, { stock_minimo: stockMinimo })
}

export async function listStockAlerts(): Promise<StockAlert[]> {
  const { data } = await tenantApi.get<any[]>(`/api/v1/notifications/alerts`, { params: { estado: 'active', limit: 100 } })
  return (data || []).map((a: any) => ({
    id: String(a.id),
    producto_id: String(a.product_id),
    producto_nombre: '',
    producto_sku: '',
    stock_actual: Number(a.nivel_actual ?? 0),
    stock_minimo: Number(a.nivel_minimo ?? 0),
    estado: a.estado === 'active' ? 'pending' : a.estado === 'resolved' ? 'resolved' : 'ignored',
    ultima_notificacion: a.notified_at || undefined,
    created_at: a.created_at,
  }))
}

export async function resolveAlert(alertId: string): Promise<void> {
  await tenantApi.post(`/api/v1/notifications/alerts/${alertId}/resolve`)
}

export async function configureNotificationChannel(
  tipo: NotificationChannel,
  config: { enabled: boolean; config: any }
): Promise<void> {
  await tenantApi.post(`/api/v1/notifications/channels`, {
    tipo,
    name: tipo.toUpperCase(),
    description: `Canal ${tipo}`,
    config: config.config,
    active: !!config.enabled,
    use_for_alerts: true,
    use_for_invoices: false,
    use_for_marketing: false,
  })
}

export async function testNotification(tipo: NotificationChannel, details?: any): Promise<void> {
  const destinatario = tipo === 'email' ? details?.email : tipo === 'whatsapp' ? details?.phone : details?.chat_id
  if (!destinatario) throw new Error('Falta destinatario de prueba')
  await tenantApi.post(`/api/v1/notifications/send`, {
    tipo,
    destinatario,
    asunto: 'Prueba de Notificación',
    mensaje: '<b>Prueba</b> desde GestiQCloud',
    config_override: details || {},
    ref_type: 'stock_alert',
  })
}
