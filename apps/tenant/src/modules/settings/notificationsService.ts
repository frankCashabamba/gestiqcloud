import tenantApi from '../../shared/api/client'
import type {
  NotificationChannel,
  NotificationChannelCreate,
  NotificationChannelUpdate,
} from './types'

export async function listNotificationChannels(): Promise<NotificationChannel[]> {
  const { data } = await tenantApi.get<NotificationChannel[]>('/api/v1/notifications/channels')
  return data || []
}

export async function createNotificationChannel(
  payload: NotificationChannelCreate
): Promise<NotificationChannel> {
  const { data } = await tenantApi.post<NotificationChannel>('/api/v1/notifications/channels', payload)
  return data
}

export async function updateNotificationChannel(
  id: string,
  payload: NotificationChannelUpdate
): Promise<NotificationChannel> {
  const { data } = await tenantApi.put<NotificationChannel>(
    `/api/v1/notifications/channels/${id}`,
    payload
  )
  return data
}
