export type HttpOptions = RequestInit & {
  authToken?: string | null
  retryOn401?: boolean
}

const EXEMPT_CSRF_SUFFIXES = [
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
  '/tenant/auth/login',
  '/tenant/auth/refresh',
  '/tenant/auth/logout',
]

const NO_AUTH_HEADER_SUFFIXES = [
  ...EXEMPT_CSRF_SUFFIXES,
  '/tenant/auth/csrf',
]

export class HttpError extends Error {
  status?: number
  retryAfter?: string | null
  data?: unknown
}

let API_URL = '/api'

export function setApiUrl(url: string | undefined | null) {
  if (!url) {
    API_URL = '/api'
    return
  }
  API_URL = url.replace(/\/+$/g, '')
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function getStoredToken(): string | null {
  try {
    const sess = sessionStorage.getItem('access_token_tenant')
    if (sess) return sess
  } catch {}
  try {
    return localStorage.getItem('authToken')
  } catch {
    return null
  }
}

function persistToken(token: string | null) {
  try {
    if (token) {
      sessionStorage.setItem('access_token_tenant', token)
      localStorage.setItem('authToken', token)
    } else {
      sessionStorage.removeItem('access_token_tenant')
      localStorage.removeItem('authToken')
    }
  } catch {}
}

function notifyAuthExpired() {
  persistToken(null)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('tenant-auth-expired'))
  }
}

function needsCsrf(path: string, method: string) {
  const isSafe = ['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())
  if (isSafe) return false
  return !EXEMPT_CSRF_SUFFIXES.some((suffix) => path.endsWith(suffix))
}

function buildUrl(base: string, path: string) {
  const trimmedBase = (base || '').replace(/\/+$/g, '')
  let normalizedPath = path || ''
  normalizedPath = normalizedPath.startsWith('/') ? normalizedPath : `/${normalizedPath}`

  // Avoid duplicating /api if the base already contains it
  let basePathname = trimmedBase
  try {
    basePathname = new URL(trimmedBase, window.location.origin).pathname.replace(/\/+$/g, '')
  } catch {
    // relative base, ignore
  }
  const baseHasApi = /^\/api(\/|$)/.test(basePathname)
  if (baseHasApi) {
    normalizedPath = normalizedPath.replace(/^\/api(\/|$)/, '/')
  }

  return (trimmedBase + normalizedPath).replace(/([^:])\/{2,}/g, '$1/')
}

async function safeJson(res: Response) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

let inflightRefresh: Promise<string | null> | null = null
async function refreshToken(): Promise<string | null> {
  try {
    const response = await fetch(buildUrl(API_URL, '/api/v1/tenant/auth/refresh'), {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) return null
    const data = await safeJson(response)
    const token = (data as any)?.access_token as string | undefined
    if (token) {
      persistToken(token)
      return token
    }
    return null
  } catch {
    return null
  }
}

export async function apiFetch<T = unknown>(path: string, options: HttpOptions = {}): Promise<T> {
  const { authToken, retryOn401 = true, headers, credentials, ...init } = options
  const url = buildUrl(API_URL, path)
  const method = (init.method ?? 'GET').toUpperCase()
  const requestHeaders = new Headers(headers || {})

  if (!requestHeaders.has('Accept')) requestHeaders.set('Accept', 'application/json')
  const isFormData = typeof FormData !== 'undefined' && (init as any)?.body instanceof FormData
  if (method !== 'GET' && !isFormData && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  const skipAuth = NO_AUTH_HEADER_SUFFIXES.some((suffix) => path.endsWith(suffix))
  const tokenToUse = skipAuth ? null : authToken ?? getStoredToken()
  if (tokenToUse && !requestHeaders.has('Authorization')) {
    requestHeaders.set('Authorization', `Bearer ${tokenToUse}`)
  }

  if (needsCsrf(path, method)) {
    const csrf = getCookie('csrf_token') || getCookie('csrftoken') || getCookie('XSRF-TOKEN')
    if (csrf && !requestHeaders.has('X-CSRF-Token')) {
      requestHeaders.set('X-CSRF-Token', csrf)
    }
  }

  const doFetch = () =>
    fetch(url, {
      credentials: credentials ?? 'include',
      headers: requestHeaders,
      ...init,
    })

  let response = await doFetch()

  if (response.status === 401 && retryOn401) {
    try {
      inflightRefresh = inflightRefresh || refreshToken()
      const newToken = await inflightRefresh
      inflightRefresh = null
      if (newToken) {
        requestHeaders.set('Authorization', `Bearer ${newToken}`)
        response = await doFetch()
      }
    } catch {
      inflightRefresh = null
    }
  }

  if (response.status === 401) {
    notifyAuthExpired()
    const error = new HttpError('Unauthorized')
    error.status = 401
    throw error
  }

  if (!response.ok) {
    const error = new HttpError(response.statusText)
    error.status = response.status
    error.retryAfter = response.headers.get('Retry-After')
    error.data = await safeJson(response)
    throw error
  }

  return (await safeJson(response)) as T
}

export { API_URL }
