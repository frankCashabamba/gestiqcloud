import { STORAGE_KEYS } from '../constants/storage'

type CachedResource<T> = {
  version: number
  savedAt: number
  data: T
}

const CACHE_PREFIX = 'gc:offline-resource:'
const CACHE_VERSION = 1

function getStorage() {
  if (typeof window === 'undefined') return null
  return window.localStorage
}

export function getOfflineCacheScope(scope?: string): string {
  try {
    const token =
      sessionStorage.getItem(STORAGE_KEYS.AUTH.TOKEN) ||
      localStorage.getItem(STORAGE_KEYS.AUTH.TOKEN) ||
      localStorage.getItem(STORAGE_KEYS.AUTH.FALLBACK_TOKEN) ||
      ''

    const tokenScope = token ? token.slice(-16) : 'anon'
    return scope ? `${scope}:${tokenScope}` : tokenScope
  } catch {
    return scope ? `${scope}:anon` : 'anon'
  }
}

export function readCachedResource<T>(key: string): T | null {
  const storage = getStorage()
  if (!storage) return null

  try {
    const raw = storage.getItem(`${CACHE_PREFIX}${key}`)
    if (!raw) return null

    const parsed = JSON.parse(raw) as CachedResource<T>
    if (parsed?.version !== CACHE_VERSION) return null
    return parsed.data ?? null
  } catch {
    return null
  }
}

export function writeCachedResource<T>(key: string, data: T) {
  const storage = getStorage()
  if (!storage) return

  try {
    const payload: CachedResource<T> = {
      version: CACHE_VERSION,
      savedAt: Date.now(),
      data,
    }
    storage.setItem(`${CACHE_PREFIX}${key}`, JSON.stringify(payload))
  } catch {}
}
