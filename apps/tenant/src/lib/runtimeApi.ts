function isLocalHostname(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'
}

function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/g, '')
}

export function resolveRuntimeApiBase(rawApiUrl?: string | null): string {
  const fallback = '/api'
  if (!rawApiUrl) return fallback

  const normalized = trimTrailingSlashes(String(rawApiUrl).trim())
  if (!normalized) return fallback

  if (typeof window === 'undefined') {
    return normalized
  }

  try {
    const current = new URL(window.location.origin)
    const api = new URL(normalized, window.location.origin)

    if (api.origin === current.origin) {
      return fallback
    }

    if (isLocalHostname(api.hostname) && isLocalHostname(current.hostname)) {
      return fallback
    }
  } catch {
    return normalized
  }

  return normalized
}

export function resolveRuntimeAssetRoot(rawApiUrl?: string | null): string {
  const apiBase = resolveRuntimeApiBase(rawApiUrl)
  if (!/^https?:\/\//i.test(apiBase)) return ''
  return trimTrailingSlashes(apiBase).replace(/\/api(?:\/v1)?$/i, '')
}

