import tenantApi from '../../shared/api/client'
import { TENANT_PURCHASES } from '@shared/endpoints'
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { listCompras, getCompra } from './services'
import { isOfflineQueuedResponse, stripOfflineMeta } from '@/lib/offlineHttp'

export const PurchasesAdapter: SyncAdapter = {
  entity: 'purchase',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      return await listCompras()
    } catch {
      return []
    }
  },

  async create(data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const response = await tenantApi.post<any>(TENANT_PURCHASES.base, payload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Purchase still queued')
    return response.data
  },

  async update(id: string, data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const response = await tenantApi.put<any>(TENANT_PURCHASES.byId(id), payload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Purchase still queued')
    return response.data
  },

  async delete(id: string): Promise<void> {
    const response = await tenantApi.delete(TENANT_PURCHASES.byId(id), { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Purchase deletion still queued')
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const purchase = await getCompra(id)
      const ts = (purchase as any)?.updated_at ?? (purchase as any)?.created_at
      return ts ? new Date(ts as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.total !== remote.total || local.estado !== remote.estado
  }
}

let registered = false
export function registerPurchasesSyncAdapter() {
  if (registered) return
  getSyncManager().registerAdapter(PurchasesAdapter)
  registered = true
}
