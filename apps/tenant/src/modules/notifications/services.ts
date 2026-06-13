import api from '../../services/api/client'
import { TENANT_NOTIFICATIONS } from '@shared/endpoints'

export interface Notification {
  id: string
  channel: string
  subject: string
  body: string
  priority: string
  status: string
  read_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  skip: number
  limit: number
}

export interface UnreadCount {
  count: number
}

export async function listNotifications(skip = 0, limit = 200): Promise<NotificationListResponse> {
  return api.get(TENANT_NOTIFICATIONS.base, { params: { skip, limit } }).then(r => r.data)
}

export async function getUnreadCount(): Promise<UnreadCount> {
  return api.get(TENANT_NOTIFICATIONS.unreadCount).then(r => r.data)
}

export async function markAsRead(ids: string[]): Promise<{ updated: number }> {
  return api
    .post(TENANT_NOTIFICATIONS.markRead, { notification_ids: ids })
    .then(r => r.data)
}

export async function archiveNotification(id: string): Promise<Notification> {
  return api.post(TENANT_NOTIFICATIONS.archive(id)).then(r => r.data)
}
