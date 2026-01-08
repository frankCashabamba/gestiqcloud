import { apiFetch } from "../lib/http";

export type Modulo = { id: string; name: string; url?: string; slug?: string; icono?: string; categoria?: string; active: boolean };

// Cache sencillo para evitar múltiples llamadas concurrentes (previene 429)
type CacheEntry = { ts: number; data: Modulo[]; inflight?: Promise<Modulo[]> }
const CACHE_TTL_MS = 60 * 1000 // 1 minuto de cache suave
const cache = new Map<string, CacheEntry>()

function normalize(data: any): Modulo[] {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  return []
}

function isFresh(entry?: CacheEntry) {
  return !!entry && Date.now() - entry.ts < CACHE_TTL_MS
}

async function fetchWithCache(key: string, fn: () => Promise<any>): Promise<Modulo[]> {
  const cached = cache.get(key)
  if (isFresh(cached)) return cached!.data
  if (cached?.inflight) return cached.inflight

  const inflight = fn()
    .then((res) => {
      const data = normalize(res)
      cache.set(key, { ts: Date.now(), data })
      return data
    })
    .catch((err) => {
      cache.delete(key)
      throw err
    })

  cache.set(key, { ts: cached?.ts ?? 0, data: cached?.data ?? [], inflight })
  return inflight
}

// Endpoint oficial: GET /api/v1/modulos (lista asignada al usuario actual)
export const listMisModulos = (authToken?: string) =>
  fetchWithCache('auth-modulos', () => apiFetch<Modulo[]>("/api/v1/modulos", { authToken }))

export const listModulosSeleccionablesPorEmpresa = (empresaSlug: string) => {
  const key = `empresa-${empresaSlug}`
  return fetchWithCache(key, () => apiFetch<Modulo[]>(`/api/v1/modulos/empresa/${encodeURIComponent(empresaSlug)}/seleccionables`))
}
