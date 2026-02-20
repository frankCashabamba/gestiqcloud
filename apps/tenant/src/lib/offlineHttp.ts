/**
 * Shared helpers for HTTP + offline queue integration.
 * Keep this module framework-agnostic so any service can reuse it.
 */
export function isOfflineQueuedResponse(response: any): boolean {
  if (!response) return false
  const queuedByBody = response?.data?.queued === true
  const queuedByHeader = String(response?.headers?.['x-offline-queued'] || '').trim() === '1'
  return response?.status === 202 && (queuedByBody || queuedByHeader)
}

export function createOfflineTempId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function isNetworkIssue(error: any): boolean {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return true
  const code = String(error?.code || '').toUpperCase()
  const msg = String(error?.message || '').toLowerCase()
  return code === 'ERR_NETWORK' || msg.includes('network') || msg.includes('failed to fetch') || msg.includes('timeout') || msg.includes('offline')
}

export function stripOfflineMeta<T extends Record<string, any>>(payload: T): T {
  const clean: Record<string, any> = {}
  for (const [key, value] of Object.entries(payload || {})) {
    if (!key.startsWith('_')) {
      clean[key] = value
    }
  }
  return clean as T
}
