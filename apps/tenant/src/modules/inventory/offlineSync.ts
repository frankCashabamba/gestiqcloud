import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { apiFetch } from '@/lib/http'
import { stripOfflineMeta } from '@/lib/offlineHttp'
import { listWarehouses } from './services'

const INVENTORY_BASE = '/api/v1/tenant/inventory'

function parsePrefixedId(id: string): { resource: string; targetId: string } {
  const idx = id.indexOf(':')
  if (idx <= 0) return { resource: 'unknown', targetId: id }
  return { resource: id.slice(0, idx), targetId: id.slice(idx + 1) }
}

export const InventoryAdapter: SyncAdapter = {
  entity: 'inventory',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      return await listWarehouses()
    } catch {
      return []
    }
  },

  async create(data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const resource = payload._resource

    if (resource === 'warehouse') {
      return apiFetch<any>(`${INVENTORY_BASE}/warehouses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
        body: JSON.stringify(payload),
      })
    }

    if (resource === 'stock_move') {
      return apiFetch<any>(`${INVENTORY_BASE}/stock/adjust`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
        body: JSON.stringify(payload),
      })
    }

    if (resource === 'alert_config') {
      return apiFetch<any>(`${INVENTORY_BASE}/alerts/configs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
        body: JSON.stringify(payload),
      })
    }

    throw new Error(`Unsupported inventory create resource: ${resource}`)
  },

  async update(id: string, data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const resource = payload._resource
    const targetId = String(payload._target_id || id)

    if (resource === 'warehouse') {
      return apiFetch<any>(`${INVENTORY_BASE}/warehouses/${targetId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
        body: JSON.stringify(payload),
      })
    }

    if (resource === 'alert_config') {
      return apiFetch<any>(`${INVENTORY_BASE}/alerts/configs/${targetId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
        body: JSON.stringify(payload),
      })
    }

    throw new Error(`Unsupported inventory update resource: ${resource}`)
  },

  async delete(id: string): Promise<void> {
    const { resource, targetId } = parsePrefixedId(id)
    if (resource === 'alert_config') {
      await apiFetch(`${INVENTORY_BASE}/alerts/configs/${targetId}`, {
        method: 'DELETE',
        headers: { 'X-Offline-Managed': '1' },
      })
      return
    }
    throw new Error(`Unsupported inventory delete resource: ${resource}`)
  },

  async getRemoteVersion(id: string): Promise<number> {
    const { resource, targetId } = parsePrefixedId(id)
    try {
      if (resource === 'alert_config') {
        const cfg = await apiFetch<any>(`${INVENTORY_BASE}/alerts/configs/${targetId}`)
        const ts = cfg?.updated_at || cfg?.created_at
        return ts ? new Date(ts).getTime() : 1
      }
      return 1
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return JSON.stringify(stripOfflineMeta(local || {})) !== JSON.stringify(stripOfflineMeta(remote || {}))
  },
}

let registered = false
export function registerInventorySyncAdapter() {
  if (registered) return
  getSyncManager().registerAdapter(InventoryAdapter)
  registered = true
}
