/**
 * Settings Offline Sync Adapter
 *
 * Caches tenant settings for offline access.
 * - Read-only offline (settings are fetched and cached)
 * - Updates are queued for sync when online
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities } from '@/lib/offlineStore'
import { getGeneral, saveGeneral } from './services'

export const SettingsAdapter: SyncAdapter = {
  entity: 'setting',
  canSyncOffline: true,

  async fetchAll(): Promise<any[]> {
    try {
      const general = await getGeneral()
      return [general]
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      return []
    }
  },

  async create(data: any): Promise<any> {
    const result = await saveGeneral(data)
    await storeEntity('setting', 'general', data, 'synced', Date.now())
    return result
  },

  async update(_id: string, data: any): Promise<any> {
    const result = await saveGeneral(data)
    await storeEntity('setting', 'general', data, 'synced', Date.now())
    return result
  },

  async delete(_id: string): Promise<void> {
    throw new Error('Settings cannot be deleted')
  },

  async getRemoteVersion(_id: string): Promise<number> {
    return 0
  },

  detectConflict(_local: any, _remote: any): boolean {
    return false
  }
}

export function registerSettingsSyncAdapter() {
  getSyncManager().registerAdapter(SettingsAdapter)
}

export async function cacheSettingsOffline(settings: any): Promise<void> {
  await storeEntity('setting', 'general', settings, 'synced', Date.now())
}

export async function getOfflineSettings(): Promise<any | null> {
  const items = await listEntities('setting')
  return items.length > 0 ? items[0].data : null
}
