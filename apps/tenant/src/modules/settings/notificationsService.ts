import tenantApi from '../../shared/api/client'
import { ADMIN_INCIDENT_CHANNELS, TENANT_TELEGRAM } from '@shared/endpoints'
import type {
  NotificationChannel,
  NotificationChannelCreate,
  NotificationChannelUpdate,
} from './types'

type ApiNotificationChannel = {
  id: string
  tenant_id?: string
  channel_type: NotificationChannel['tipo']
  name: string
  config: Record<string, unknown>
  is_active: boolean
}

function fromApiChannel(channel: ApiNotificationChannel): NotificationChannel {
  return {
    id: channel.id,
    tenant_id: channel.tenant_id,
    tipo: channel.channel_type,
    name: channel.name,
    config: channel.config || {},
    active: Boolean(channel.is_active),
  }
}

export async function listNotificationChannels(): Promise<NotificationChannel[]> {
  const { data } = await tenantApi.get<ApiNotificationChannel[]>(
    ADMIN_INCIDENT_CHANNELS.base
  )
  return (data || []).map(fromApiChannel)
}

export async function createNotificationChannel(
  payload: NotificationChannelCreate
): Promise<NotificationChannel> {
  const { data } = await tenantApi.post<ApiNotificationChannel>(
    ADMIN_INCIDENT_CHANNELS.base,
    {
      channel_type: payload.tipo,
      name: payload.name,
      config: payload.config,
      is_active: payload.active ?? true,
    }
  )
  return fromApiChannel(data)
}

export async function updateNotificationChannel(
  id: string,
  payload: NotificationChannelUpdate
): Promise<NotificationChannel> {
  const { data } = await tenantApi.put<ApiNotificationChannel>(
    ADMIN_INCIDENT_CHANNELS.byId(id),
    {
      name: payload.name,
      config: payload.config,
      is_active: payload.active,
    }
  )
  return fromApiChannel(data)
}

export async function generateTelegramSecret(): Promise<string> {
  const { data } = await tenantApi.post<{ secret: string }>(TENANT_TELEGRAM.generateSecret, {})
  return data.secret
}

export async function registerTelegramWebhook(customBaseUrl?: string): Promise<string> {
  const body: Record<string, string> = {}
  if (customBaseUrl) body.custom_base_url = customBaseUrl
  const { data } = await tenantApi.post<{ webhook_url: string }>(TENANT_TELEGRAM.registerWebhook, body)
  return data.webhook_url
}
