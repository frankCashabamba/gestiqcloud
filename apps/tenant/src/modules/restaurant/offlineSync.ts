import api from '../../shared/api/client'
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { listOrders, getOrder } from './services'
import { isOfflineQueuedResponse, stripOfflineMeta } from '@/lib/offlineHttp'

const BASE = '/api/v1/tenant/restaurant/orders'

export const RestaurantAdapter: SyncAdapter = {
  entity: 'order',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      return await listOrders()
    } catch {
      return []
    }
  },

  async create(data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const response = await api.post<any>(BASE, payload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Order still queued')
    return response.data
  },

  async update(id: string, data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const response = await api.put<any>(`${BASE}/${id}`, payload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Order still queued')
    return response.data
  },

  async delete(id: string): Promise<void> {
    const response = await api.delete(`${BASE}/${id}`, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Order deletion still queued')
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const order = await getOrder(id)
      const ts = (order as any)?.updated_at ?? (order as any)?.created_at
      return ts ? new Date(ts as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.status !== remote.status || local.total !== remote.total
  }
}

let registered = false
export function registerRestaurantSyncAdapter() {
  if (registered) return
  getSyncManager().registerAdapter(RestaurantAdapter)
  registered = true
}
