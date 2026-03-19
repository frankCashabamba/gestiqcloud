import { apiFetch } from '../lib/http'
import { env } from '../env'

export type ThemeResponse = { brand?: { name?: string; logoUrl?: string | null } } & Record<string, any>

type CacheEntry = { ts: number; data: ThemeResponse; inflight?: Promise<ThemeResponse> }

const CACHE_TTL_MS = 60 * 1000
const LS_PREFIX = 'theme_cache:'
const cache = new Map<string, CacheEntry>()

function isFresh(entry?: CacheEntry) {
  return !!entry && Date.now() - entry.ts < CACHE_TTL_MS
}

function cacheKey(empresa?: string | null) {
  return empresa ? `empresa:${empresa}` : 'default'
}

function readLocalStorage(key: string): CacheEntry | undefined {
  try {
    const raw = localStorage.getItem(LS_PREFIX + key)
    if (!raw) return undefined
    const parsed = JSON.parse(raw) as { ts: number; data: ThemeResponse }
    if (parsed?.data && parsed.ts) return { ts: parsed.ts, data: parsed.data }
  } catch { /* ignore */ }
  return undefined
}

function writeLocalStorage(key: string, entry: { ts: number; data: ThemeResponse }) {
  try {
    localStorage.setItem(LS_PREFIX + key, JSON.stringify({ ts: entry.ts, data: entry.data }))
  } catch { /* quota exceeded – ignore */ }
}

function removeLocalStorage(key: string) {
  try { localStorage.removeItem(LS_PREFIX + key) } catch { /* ignore */ }
}

export function invalidateCompanyThemeCache(empresa?: string | null) {
  if (empresa) {
    const k = cacheKey(empresa)
    cache.delete(k)
    removeLocalStorage(k)
    return
  }
  cache.clear()
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(LS_PREFIX))
      .forEach((k) => localStorage.removeItem(k))
  } catch { /* ignore */ }
}

function toAbsoluteAssetUrl(url?: string | null) {
  if (!url) return url ?? null
  if (/^(https?:)?\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) return url
  const apiRoot = (env.apiUrl || '').replace(/\/+$/g, '').replace(/\/api(?:\/v1)?$/i, '')
  if (!apiRoot) return url
  return `${apiRoot}${url.startsWith('/') ? '' : '/'}${url}`
}

export async function fetchCompanyTheme(empresa?: string | null): Promise<ThemeResponse> {
  const key = cacheKey(empresa)
  const cached = cache.get(key)
  if (isFresh(cached)) return cached!.data
  if (cached?.inflight) return cached.inflight

  const lsCached = readLocalStorage(key)

  const inflight = apiFetch<ThemeResponse>(
    empresa
      ? `/api/v1/company/settings/theme?empresa=${encodeURIComponent(empresa)}`
      : '/api/v1/company/settings/theme'
  )
    .then((data) => {
      const normalized = {
        ...data,
        brand: data?.brand
          ? {
              ...data.brand,
              logoUrl: toAbsoluteAssetUrl(data.brand.logoUrl),
            }
          : data?.brand,
      }
      cache.set(key, { ts: Date.now(), data: normalized })
      writeLocalStorage(key, { ts: Date.now(), data: normalized })
      return normalized
    })
    .catch((err) => {
      cache.delete(key)
      throw err
    })

  if (lsCached?.data && Object.keys(lsCached.data).length > 0 && isFresh(lsCached)) {
    cache.set(key, { ts: lsCached.ts, data: lsCached.data, inflight })
    return lsCached.data
  }

  cache.set(key, { ts: cached?.ts ?? 0, data: cached?.data ?? {}, inflight })
  return inflight
}
