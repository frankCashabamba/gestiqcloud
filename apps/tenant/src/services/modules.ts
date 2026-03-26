import { apiFetch } from '../lib/http'
import { isNetworkIssue } from '../lib/offlineHttp'
import { getOfflineCacheScope, readCachedResource, writeCachedResource } from '../lib/offlineResourceCache'

export type Modulo = { id: string; name: string; url?: string; slug?: string; icono?: string; categoria?: string; active: boolean };

// Cache sencillo para evitar múltiples llamadas concurrentes (previene 429)
type CacheEntry = { ts: number; data: Modulo[]; inflight?: Promise<Modulo[]> }
const CACHE_TTL_MS = 60 * 1000 // 1 minuto de cache suave
const cache = new Map<string, CacheEntry>()

function normalize(data: any): Modulo[] {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  if (data == null) return []
  throw new Error("Invalid modules response")
}

function isFresh(entry?: CacheEntry) {
  return !!entry && Date.now() - entry.ts < CACHE_TTL_MS
}

function canUseCachedFallback(err: any) {
  return isNetworkIssue(err) || Number(err?.status || 0) >= 500
}

async function fetchWithCache(key: string, fn: () => Promise<any>): Promise<Modulo[]> {
  const cached = cache.get(key)
  const persisted = readCachedResource<Modulo[]>(key)
  if (isFresh(cached)) return cached!.data
  if (cached?.inflight) return cached.inflight
  if (!cached && persisted) {
    cache.set(key, { ts: Date.now(), data: persisted })
  }

  const inflight = fn()
    .then((res) => {
      const data = normalize(res)
      cache.set(key, { ts: Date.now(), data })
      writeCachedResource(key, data)
      return data
    })
    .catch((err) => {
      const fallback = cached?.data?.length ? cached.data : persisted
      if (fallback?.length && canUseCachedFallback(err)) {
        cache.set(key, { ts: Date.now(), data: fallback })
        return fallback
      }
      cache.delete(key)
      throw err
    })

  cache.set(key, { ts: cached?.ts ?? 0, data: cached?.data ?? [], inflight })
  return inflight
}

function authModulesCacheKey(authToken?: string) {
  const tokenScope = authToken ? authToken.slice(-16) : getOfflineCacheScope()
  return `modules:mine:${tokenScope}`
}

// Endpoint oficial: GET /api/v1/modules (lista asignada al usuario actual)
export const listMisModulos = (authToken?: string) =>
  fetchWithCache(authModulesCacheKey(authToken), () => apiFetch<Modulo[]>('/api/v1/modules', { authToken }))

export const listModulosSeleccionablesPorEmpresa = (empresaSlug: string) => {
  const key = `modules:company:${getOfflineCacheScope(empresaSlug)}`
  return fetchWithCache(
    key,
    () => apiFetch<Modulo[]>(`/api/v1/modules/company/${encodeURIComponent(empresaSlug)}/selectable`)
  )
}
