// Shared HTTP client with auth handlers and CSRF support
export const buildApiUrl = (base: string, path: string): string => {
  const b = (base || '').replace(/\/+$/g, '')
  let p = path || ''
  p = p.startsWith('/') ? p : `/${p}`

  let basePathname = b
  try {
    basePathname = new URL(b, typeof window !== 'undefined' ? window.location.origin : 'http://localhost').pathname.replace(/\/+$/g, '')
  } catch {
    /* base relativa */
  }
  const baseHasApi = /^\/api(\/|$)/.test(basePathname)
  if (baseHasApi) p = p.replace(/^\/api(\/|$)/, '/')

  const joined = (b + p).replace(/([^:])\/{2,}/g, '$1/')
  return joined
}

export async function safeJson(res: Response) {
  const txt = await res.text()
  try {
    return txt ? JSON.parse(txt) : null
  } catch {
    return null
  }
}

export function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return m ? decodeURIComponent(m[1]) : null
}

export function needsCsrf(path: string, method: string, exemptSuffixes: string[] = []): boolean {
  const isSafe = ['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())
  if (isSafe) return false
  return !exemptSuffixes.some((s) => path.endsWith(s))
}

export class HttpError extends Error {
  status?: number
  retryAfter?: string | null
  data?: any
}

export type HttpOptions = RequestInit & { authToken?: string; retryOn401?: boolean }

export type AuthHandlers = {
  getToken?: () => string | null
  setToken?: (t: string | null) => void
  refresh?: () => Promise<string | null>
}

export type HttpClientConfig = {
  apiUrl: string
  csrfExemptSuffixes?: string[]
  noAuthHeaderSuffixes?: string[]
  authHandlers?: AuthHandlers
}

export class HttpClient {
  private apiUrl: string
  private csrfExemptSuffixes: string[]
  private noAuthHeaderSuffixes: string[]
  private getTokenHandler: (() => string | null) | null = null
  private setTokenHandler: ((t: string | null) => void) | null = null
  private refreshHandler: (() => Promise<string | null>) | null = null
  private inflightRefresh: Promise<string | null> | null = null

  constructor(config: HttpClientConfig) {
    this.apiUrl = config.apiUrl
    this.csrfExemptSuffixes = config.csrfExemptSuffixes || ['/auth/login', '/auth/refresh', '/auth/logout']
    this.noAuthHeaderSuffixes = config.noAuthHeaderSuffixes || ['/auth/login', '/auth/refresh', '/auth/logout']
    
    if (config.authHandlers) {
      if (config.authHandlers.getToken) this.getTokenHandler = config.authHandlers.getToken
      if (config.authHandlers.setToken) this.setTokenHandler = config.authHandlers.setToken
      if (config.authHandlers.refresh) this.refreshHandler = config.authHandlers.refresh
    }
  }

  registerAuthHandlers(handlers: AuthHandlers) {
    if (handlers.getToken) this.getTokenHandler = handlers.getToken
    if (handlers.setToken) this.setTokenHandler = handlers.setToken
    if (handlers.refresh) this.refreshHandler = handlers.refresh
  }

  async fetch<T = unknown>(
    path: string,
    { authToken, retryOn401 = true, headers, credentials, ...init }: HttpOptions = {}
  ): Promise<T> {
    const url = buildApiUrl(this.apiUrl, path)
    const method = (init.method ?? 'GET').toUpperCase()

    const h = new Headers(headers || {})

    if (!h.has('Accept')) h.set('Accept', 'application/json')
    const isFormData = typeof FormData !== 'undefined' && (init as any)?.body instanceof FormData
    if (method !== 'GET' && !isFormData && !h.has('Content-Type')) {
      h.set('Content-Type', 'application/json')
    }

    const skipAuthHeader = this.noAuthHeaderSuffixes.some((s) => path.endsWith(s))
    const tokenToUse = skipAuthHeader
      ? null
      : authToken ?? (this.getTokenHandler ? this.getTokenHandler() : null)

    if (tokenToUse && !h.has('Authorization')) {
      h.set('Authorization', `Bearer ${tokenToUse}`)
    }

    if (needsCsrf(path, method, this.csrfExemptSuffixes)) {
      const csrf = getCookie('csrf_token') || getCookie('csrftoken') || getCookie('XSRF-TOKEN')
      if (csrf && !h.has('X-CSRF-Token') && !h.has('X-CSRF') && !h.has('X-XSRF-TOKEN')) {
        h.set('X-CSRF-Token', csrf)
        h.set('X-CSRF', csrf)
      }
    }

    async function doFetch() {
      return fetch(url, { credentials: credentials ?? 'include', headers: h, ...init })
    }

    let res = await doFetch()

    if (res.status === 401 && retryOn401 && this.refreshHandler) {
      try {
        this.inflightRefresh = this.inflightRefresh || this.refreshHandler()
        const newTok = await this.inflightRefresh
        if (newTok) {
          if (this.setTokenHandler) this.setTokenHandler(newTok)
          h.set('Authorization', `Bearer ${newTok}`)
          res = await doFetch()
        }
      } catch {
        // silencioso: 401 se gestionará abajo
      } finally {
        this.inflightRefresh = null
      }
    }

    if (res.status === 401) {
      const err = new HttpError('Unauthorized')
      err.status = 401
      throw err
    }

    if (!res.ok) {
      const retryAfter = res.headers.get('Retry-After')
      const detail = await safeJson(res)
      const error = new HttpError((detail as any)?.detail || res.statusText)
      error.status = res.status
      error.retryAfter = retryAfter
      error.data = detail
      throw error
    }

    return (await safeJson(res)) as T
  }
}

// Simple standalone apiFetch for backward compatibility
export async function createApiFetch(apiUrl: string) {
  const client = new HttpClient({ apiUrl })
  return <T = unknown>(path: string, options?: HttpOptions) => client.fetch<T>(path, options)
}
