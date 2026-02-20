import tenantApi from '../../shared/api/client'
import { TENANT_EXPENSES } from '@shared/endpoints'
import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { getGasto, listGastos } from './services'
import { isOfflineQueuedResponse, stripOfflineMeta } from '@/lib/offlineHttp'

export const ExpensesAdapter: SyncAdapter = {
  entity: 'expense',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      return await listGastos()
    } catch {
      return []
    }
  },

  async create(data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const response = await tenantApi.post<any>(TENANT_EXPENSES.base, payload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Expense still queued')
    return response.data
  },

  async update(id: string, data: any): Promise<any> {
    const payload = stripOfflineMeta(data || {})
    const response = await tenantApi.put<any>(TENANT_EXPENSES.byId(id), payload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Expense still queued')
    return response.data
  },

  async delete(id: string): Promise<void> {
    const response = await tenantApi.delete(TENANT_EXPENSES.byId(id), { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) throw new Error('Expense deletion still queued')
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const expense = await getGasto(id)
      const ts = (expense as any)?.updated_at ?? (expense as any)?.created_at
      return ts ? new Date(ts as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.amount !== remote.amount || local.status !== remote.status
  }
}

let registered = false
export function registerExpensesSyncAdapter() {
  if (registered) return
  getSyncManager().registerAdapter(ExpensesAdapter)
  registered = true
}
