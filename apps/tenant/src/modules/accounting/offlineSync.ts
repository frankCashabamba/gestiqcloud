/**
 * Accounting Offline Sync Adapter
 *
 * Synchronizes chart of accounts (plan de cuentas) with offline support.
 * - Full CRUD with conflict detection
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listCuentas, getCuenta, createCuenta, updateCuenta, removeCuenta } from './services'
import type { PlanCuenta } from './services'

export const AccountingAdapter: SyncAdapter = {
  entity: 'account',
  canSyncOffline: true,

  async fetchAll(): Promise<PlanCuenta[]> {
    try {
      return await listCuentas()
    } catch (error) {
      console.error('Failed to fetch accounts:', error)
      return []
    }
  },

  async create(data: any): Promise<PlanCuenta> {
    const cuenta = await createCuenta(data)
    const remoteVersion = cuenta.updated_at ? new Date(cuenta.updated_at).getTime() : Date.now()
    await storeEntity('account', String(cuenta.id), cuenta, 'synced', remoteVersion)
    return cuenta
  },

  async update(id: string, data: any): Promise<PlanCuenta> {
    const cuenta = await updateCuenta(id, data)
    const remoteVersion = cuenta.updated_at ? new Date(cuenta.updated_at).getTime() : Date.now()
    await storeEntity('account', String(id), cuenta, 'synced', remoteVersion)
    return cuenta
  },

  async delete(id: string): Promise<void> {
    try {
      await removeCuenta(id)
      await storeEntity('account', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('account', id)
      console.warn('[offline] Queued account deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const cuenta = await getCuenta(id)
      const timestamp = cuenta.updated_at ?? cuenta.created_at
      return timestamp ? new Date(timestamp).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.nombre !== remote.nombre ||
           local.codigo !== remote.codigo ||
           local.tipo !== remote.tipo ||
           local.saldo !== remote.saldo
  }
}

export function registerAccountingSyncAdapter() {
  getSyncManager().registerAdapter(AccountingAdapter)
}

export async function getAccountsWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('account')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
