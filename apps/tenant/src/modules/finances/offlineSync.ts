/**
 * Finances/Cashflow Offline Sync Adapter
 *
 * Synchronizes cash flow movements with offline support.
 * - Create and update only (financial records are immutable)
 * - Conflict detection on amount/type/status
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities } from '@/lib/offlineStore'
import { listCaja, getMovimientoCaja, createMovimientoCaja, updateMovimientoCaja } from './services'
import type { Movimiento } from './services'

export const CashflowAdapter: SyncAdapter = {
  entity: 'cashflow',
  canSyncOffline: true,

  async fetchAll(): Promise<Movimiento[]> {
    try {
      return await listCaja()
    } catch (error) {
      console.error('Failed to fetch cashflow:', error)
      return []
    }
  },

  async create(data: any): Promise<Movimiento> {
    const mov = await createMovimientoCaja(data)
    const remoteVersion = (mov as any)?.updated_at ? new Date((mov as any).updated_at as string).getTime() : Date.now()
    await storeEntity('cashflow', String(mov.id), mov, 'synced', remoteVersion)
    return mov
  },

  async update(id: string, data: any): Promise<Movimiento> {
    const mov = await updateMovimientoCaja(id, data)
    const remoteVersion = (mov as any)?.updated_at ? new Date((mov as any).updated_at as string).getTime() : Date.now()
    await storeEntity('cashflow', String(id), mov, 'synced', remoteVersion)
    return mov
  },

  async delete(_id: string): Promise<void> {
    throw new Error('Cash flow movements cannot be deleted')
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const mov = await getMovimientoCaja(id)
      const timestamp = (mov as any)?.updated_at ?? (mov as any)?.fecha ?? (mov as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.monto !== remote.monto ||
           local.tipo !== remote.tipo ||
           local.concepto !== remote.concepto ||
           local.estado !== remote.estado
  }
}

export function registerCashflowSyncAdapter() {
  getSyncManager().registerAdapter(CashflowAdapter)
}

export async function getCashflowWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('cashflow')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
