/**
 * HR Offline Sync Adapter
 *
 * Caches HR data (vacaciones) for offline access.
 * - Read-only offline (limited CRUD in HR module)
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities } from '@/lib/offlineStore'
import { listVacaciones } from './services'

export const HRAdapter: SyncAdapter = {
  entity: 'hr',
  canSyncOffline: false,

  async fetchAll(): Promise<any[]> {
    try {
      return await listVacaciones()
    } catch (error) {
      console.error('Failed to fetch HR data:', error)
      return []
    }
  },

  async create(_data: any): Promise<any> {
    throw new Error('HR create is not available offline')
  },

  async update(_id: string, _data: any): Promise<any> {
    throw new Error('HR update is not available offline')
  },

  async delete(_id: string): Promise<void> {
    throw new Error('HR delete is not available offline')
  },

  async getRemoteVersion(_id: string): Promise<number> {
    return 0
  },

  detectConflict(_local: any, _remote: any): boolean {
    return false
  }
}

export function registerHRSyncAdapter() {
  getSyncManager().registerAdapter(HRAdapter)
}

export async function cacheHRDataOffline(data: any[]): Promise<void> {
  for (const item of data) {
    await storeEntity('hr', String(item.id), item, 'synced', Date.now())
  }
}

export async function getOfflineHRData(): Promise<any[]> {
  const items = await listEntities('hr')
  return items.map(i => i.data)
}
