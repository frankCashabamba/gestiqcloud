import { apiFetch } from '../lib/http'

type ThemeResponse = { brand?: { name?: string; logoUrl?: string | null } } & Record<string, any>

type CacheEntry = { ts: number; data: ThemeResponse; inflight?: Promise<ThemeResponse> }

const CACHE_TTL_MS = 60 * 1000
const cache = new Map<string, CacheEntry>()

function isFresh(entry?: CacheEntry) {
  return !!entry && Date.now() - entry.ts < CACHE_TTL_MS
}

function cacheKey(empresa?: string | null) {
  return empresa ? `empresa:${empresa}` : 'default'
}

export async function fetchTenantTheme(empresa?: string | null): Promise<ThemeResponse> {
  const key = cacheKey(empresa)
  const cached = cache.get(key)
  if (isFresh(cached)) return cached!.data
  if (cached?.inflight) return cached.inflight

  const inflight = apiFetch<ThemeResponse>(
    empresa ? `/api/v1/tenant/settings/theme?empresa=${encodeURIComponent(empresa)}` : '/api/v1/tenant/settings/theme'
  )
    .then((data) => {
      cache.set(key, { ts: Date.now(), data })
      return data
    })
    .catch((err) => {
      cache.delete(key)
      throw err
    })

  cache.set(key, { ts: cached?.ts ?? 0, data: cached?.data ?? {}, inflight })
  return inflight
}
