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
  const { data } = await tenantApi.get<any[]>(`/api/v1/incidents/stock-alerts`, {
    params: { status: 'active', limit: 100 },
  })
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
  await tenantApi.post(`/api/v1/incidents/stock-alerts/${alertId}/resolve`)
}

export async function configureNotificationChannel(
  _tipo: NotificationChannel,
  _config: { enabled: boolean; config: any }
): Promise<void> {
  throw new Error(
    'Configura las credenciales del canal en Ajustes > Notificaciones. Las alertas de inventario usan sus propios destinatarios en cada configuración de alerta.'
  )
}

export async function testNotification(tipo: NotificationChannel, details?: any): Promise<void> {
  const destinatario = tipo === 'email' ? details?.email : tipo === 'whatsapp' ? details?.phone : details?.chat_id
  if (!destinatario) throw new Error('Falta destinatario de prueba')
  await tenantApi.post(`/api/v1/tenant/notifications/send`, {
    channel: tipo,
    recipient: destinatario,
    subject: 'Prueba de Notificacion',
    body: '<b>Prueba</b> desde GestiQCloud',
    metadata: details || {},
    priority: 'normal',
  })
}
