import { apiFetch } from '../lib/http'
import { env } from '../env'

export type ThemeResponse = { brand?: { name?: string; logoUrl?: string | null } } & Record<string, any>

type CacheEntry = { ts: number; data: ThemeResponse; inflight?: Promise<ThemeResponse> }

const CACHE_TTL_MS = 60 * 1000
const cache = new Map<string, CacheEntry>()

function isFresh(entry?: CacheEntry) {
  return !!entry && Date.now() - entry.ts < CACHE_TTL_MS
}

function cacheKey(empresa?: string | null) {
  return empresa ? `empresa:${empresa}` : 'default'
}

export function invalidateCompanyThemeCache(empresa?: string | null) {
  if (empresa) {
    cache.delete(cacheKey(empresa))
    return
  }
  cache.clear()
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
      return normalized
    })
    .catch((err) => {
      cache.delete(key)
      throw err
    })

  cache.set(key, { ts: cached?.ts ?? 0, data: cached?.data ?? {}, inflight })
  return inflight
}
