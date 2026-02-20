import api from '../../services/api/client'

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
  return api.get('/api/v1/tenant/notifications', { params: { skip, limit } }).then(r => r.data)
}

export async function getUnreadCount(): Promise<UnreadCount> {
  return api.get('/api/v1/tenant/notifications/unread-count').then(r => r.data)
}

export async function markAsRead(ids: string[]): Promise<{ updated: number }> {
  return api
    .post('/api/v1/tenant/notifications/mark-read', { notification_ids: ids })
    .then(r => r.data)
}

export async function archiveNotification(id: string): Promise<Notification> {
  return api.post(`/api/v1/tenant/notifications/${id}/archive`).then(r => r.data)
}
