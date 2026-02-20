import api from "../../services/api/client"

export interface WebhookSubscription {
  id: string
  event: string
  url: string
  secret?: string
  active: boolean
  created_at: string
}

export interface WebhookSubscriptionCreate {
  event: string
  url: string
  secret?: string
}

export interface WebhookDelivery {
  id: string
  event: string
  payload: Record<string, any>
  target_url: string
  status: 'PENDING' | 'SENT' | 'FAILED'
  attempts: number
  last_error?: string
  created_at: string
}

export interface DeliveryPayload {
  event: string
  payload: Record<string, any>
}

export async function listSubscriptions(): Promise<WebhookSubscription[]> {
  return api.get('/api/v1/tenant/webhooks').then(r => {
    const items = Array.isArray(r.data?.items) ? r.data.items : []
    return items.map((w: any) => ({
      id: String(w.id),
      event: String(w.event_type || ''),
      url: String(w.target_url || ''),
      active: Boolean(w.is_active),
      created_at: String(w.created_at || ''),
    })) as WebhookSubscription[]
  })
}

export async function createSubscription(payload: WebhookSubscriptionCreate): Promise<{ id: string }> {
  return api
    .post('/api/v1/tenant/webhooks', {
      event_type: payload.event,
      target_url: payload.url,
      secret: payload.secret || 'webhook-secret-123',
    })
    .then(r => ({ id: String(r.data?.id) }))
}

export async function deleteSubscription(id: string): Promise<void> {
  return api.delete(`/api/v1/tenant/webhooks/${id}`).then(() => undefined)
}

export async function updateSubscription(id: string, payload: Partial<WebhookSubscriptionCreate>): Promise<WebhookSubscription> {
  return api
    .put(`/api/v1/tenant/webhooks/${id}`, {
      target_url: payload.url,
      secret: payload.secret,
      is_active: true,
    })
    .then(r => ({
      id: String(r.data?.id),
      event: String(r.data?.event_type || ''),
      url: String(r.data?.target_url || ''),
      active: Boolean(r.data?.is_active),
      created_at: String(r.data?.created_at || ''),
    }))
}

export async function enqueueDelivery(payload: DeliveryPayload): Promise<{ enqueued: number }> {
  // Legacy helper: no direct public endpoint for arbitrary enqueue in current API.
  return { enqueued: 0 }
}

export async function testSubscription(id: string): Promise<{ enqueued: number }> {
  return api.post(`/api/v1/tenant/webhooks/${id}/test`).then(r => ({
    enqueued: r.data?.success ? 1 : 0,
  }))
}
