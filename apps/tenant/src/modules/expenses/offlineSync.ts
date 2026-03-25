/**
 * Expenses Offline Sync Adapter
 *
 * Synchronizes expenses (gastos) with offline support.
 * - Create, update, soft-delete
 * - Conflict detection on amount/category/status
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listGastos, getGasto, createGasto, updateGasto, removeGasto } from './services'
import type { Gasto } from './services'

export const ExpensesAdapter: SyncAdapter = {
  entity: 'expense',
  canSyncOffline: true,

  async fetchAll(): Promise<Gasto[]> {
    try {
      return await listGastos()
    } catch (error) {
      console.error('Failed to fetch expenses:', error)
      return []
    }
  },

  async create(data: any): Promise<Gasto> {
    const gasto = await createGasto(data)
    const remoteVersion = (gasto as any)?.updated_at ? new Date((gasto as any).updated_at as string).getTime() : Date.now()
    await storeEntity('expense', String(gasto.id), gasto, 'synced', remoteVersion)
    return gasto
  },

  async update(id: string, data: any): Promise<Gasto> {
    const gasto = await updateGasto(id, data)
    const remoteVersion = (gasto as any)?.updated_at ? new Date((gasto as any).updated_at as string).getTime() : Date.now()
    await storeEntity('expense', String(id), gasto, 'synced', remoteVersion)
    return gasto
  },

  async delete(id: string): Promise<void> {
    try {
      await removeGasto(id)
      await storeEntity('expense', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('expense', id)
      console.warn('[offline] Queued expense deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const gasto = await getGasto(id)
      const timestamp = (gasto as any)?.updated_at ?? (gasto as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.monto !== remote.monto ||
           local.categoria !== remote.categoria ||
           local.estado !== remote.estado ||
           local.status !== remote.status
  }
}

export function registerExpensesSyncAdapter() {
  getSyncManager().registerAdapter(ExpensesAdapter)
}

export async function getExpensesWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('expense')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
