import { createClient } from '@shared/http'
import { queueRequest, OutboxItem, syncOutbox } from './outbox'

export function createSharedClient(cfg: {
  baseURL?: string
  tokenKey: string
  refreshPath: string
  csrfPath: string
  authExemptSuffixes?: string[]
}) {
  const api = createClient({ baseURL: cfg.baseURL ?? '/api', ...cfg } as any)

  async function sendWithOutbox(method: 'POST' | 'PUT' | 'PATCH' | 'DELETE', url: string, data?: any, headers?: any) {
    try {
      const res = await (api as any)[method.toLowerCase()](url, data, { headers })
      return res
    } catch (e: any) {
      const offline = !navigator.onLine || e?.code === 'ERR_NETWORK' || e?.message?.includes('Network')
      if (offline) {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
        const item: OutboxItem = { id, method, url, body: data, headers, ts: Date.now() }
        await queueRequest(item)
        return { data: { queued: true }, status: 202 }
      }
      throw e
    }
  }

  async function trySync() {
    await syncOutbox(async (it) => {
      const h = { ...(it.headers || {}) }
      return fetch((api.defaults as any).baseURL + it.url, {
        method: it.method,
        headers: { 'Content-Type': 'application/json', ...h },
        body: it.body ? JSON.stringify(it.body) : undefined,
        credentials: 'include'
      })
    })
  }

  window.addEventListener('online', () => { trySync() })

  return Object.assign(api, {
    postOutbox: (url: string, data?: any, headers?: any) => sendWithOutbox('POST', url, data, headers),
    putOutbox: (url: string, data?: any, headers?: any) => sendWithOutbox('PUT', url, data, headers),
    patchOutbox: (url: string, data?: any, headers?: any) => sendWithOutbox('PATCH', url, data, headers),
    deleteOutbox: (url: string, data?: any, headers?: any) => sendWithOutbox('DELETE', url, data, headers),
    trySync,
  })
}
