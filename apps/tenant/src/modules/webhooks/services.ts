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
  return api.get('/webhooks/subscriptions').then(r => r.data)
}

export async function createSubscription(payload: WebhookSubscriptionCreate): Promise<{ id: string }> {
  return api.post('/webhooks/subscriptions', payload).then(r => r.data)
}

export async function deleteSubscription(id: string): Promise<void> {
  return api.delete(`/webhooks/subscriptions/${id}`).then(r => r.data)
}

export async function updateSubscription(id: string, payload: Partial<WebhookSubscriptionCreate>): Promise<WebhookSubscription> {
  return api.patch(`/webhooks/subscriptions/${id}`, payload).then(r => r.data)
}

export async function enqueueDelivery(payload: DeliveryPayload): Promise<{ enqueued: number }> {
  return api.post('/webhooks/deliveries', payload).then(r => r.data)
}

export async function testSubscription(id: string): Promise<{ enqueued: number }> {
  return api.post(`/webhooks/subscriptions/${id}/test`).then(r => r.data)
}
