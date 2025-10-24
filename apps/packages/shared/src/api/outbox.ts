import { set, del, entries } from 'idb-keyval'

export type OutboxItem = {
  id: string
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  url: string
  body?: any
  headers?: Record<string, string>
  ts: number
}

const STORE = 'http-outbox'

export async function queueRequest(item: OutboxItem) {
  await set(`${STORE}:${item.id}`, item)
}

export async function removeRequest(id: string) {
  await del(`${STORE}:${id}`)
}

export async function listRequests(): Promise<OutboxItem[]> {
  const all = (await entries()) as any[]
  return all
    .filter(([k]: [any, any]) => String(k).startsWith(`${STORE}:`))
    .map(([, v]: [any, any]) => v as OutboxItem)
    .sort((a: OutboxItem, b: OutboxItem) => a.ts - b.ts)
}

export async function syncOutbox(fetcher: (i: OutboxItem) => Promise<Response>) {
  const items = await listRequests()
  for (const it of items) {
    try {
      const r = await fetcher(it)
      if (r.ok) await removeRequest(it.id)
    } catch {
      // keep for next round
      return false
    }
  }
  return true
}
