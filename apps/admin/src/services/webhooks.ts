/**
 * Webhooks Service
 * Handles webhook management API calls
 */

import apiClient from './api';

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  retry_count: number;
  timeout: number;
  created_at: string;
  updated_at?: string;
  last_triggered?: string;
}

export interface WebhookLog {
  id: string;
  webhook_id: string;
  event: string;
  payload: Record<string, any>;
  response_status: number;
  response_body?: string;
  success: boolean;
  created_at: string;
}

export interface WebhookResponse {
  webhooks: Webhook[];
  total: number;
}

export async function getWebhooks(params?: {
  limit?: number;
  offset?: number;
}): Promise<WebhookResponse> {
  return apiClient.webhooks.list(params);
}

export async function getWebhook(webhookId: string): Promise<Webhook> {
  return apiClient.webhooks.get(webhookId);
}

export async function createWebhook(data: Partial<Webhook>): Promise<Webhook> {
  return apiClient.webhooks.create(data);
}

export async function updateWebhook(
  webhookId: string,
  data: Partial<Webhook>
): Promise<Webhook> {
  return apiClient.webhooks.update(webhookId, data);
}

export async function deleteWebhook(webhookId: string): Promise<void> {
  return apiClient.webhooks.delete(webhookId);
}

export async function testWebhook(webhookId: string): Promise<{
  success: boolean;
  status: number;
  response: string;
}> {
  return apiClient.webhooks.test(webhookId);
}

export async function getWebhookLogs(
  webhookId: string,
  params?: { limit?: number; offset?: number }
): Promise<{ logs: WebhookLog[]; total: number }> {
  const logs = await apiClient.webhooks.getLogs(webhookId, params);
  return logs;
}
