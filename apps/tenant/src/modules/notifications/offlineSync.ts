import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { listNotifications } from './services'

export const NotificationsAdapter: SyncAdapter = {
  entity: 'notification',
  canSyncOffline: false,

  async fetchAll(): Promise<any[]> {
    try {
      const response = await listNotifications()
      return response.items
    } catch {
      return []
    }
  },

  async create(_data: any): Promise<any> {
    throw new Error('Notification create is not available offline')
  },

  async update(_id: string, _data: any): Promise<any> {
    throw new Error('Notification update is not available offline')
  },

  async delete(_id: string): Promise<void> {
    throw new Error('Notification delete is not available offline')
  },

  async getRemoteVersion(_id: string): Promise<number> {
    return 0
  },

  detectConflict(_local: any, _remote: any): boolean {
    return false
  }
}

let registered = false
export function registerNotificationsSyncAdapter() {
  if (registered) return
  getSyncManager().registerAdapter(NotificationsAdapter)
  registered = true
}
