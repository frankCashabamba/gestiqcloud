import axios, { AxiosInstance } from 'axios'

type CreateClientOpts = {
  baseURL: string
  tokenKey?: string
  refreshPath?: string
  csrfPath?: string
  authExemptSuffixes?: string[]
}

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return m ? decodeURIComponent(m[1]) : null
}

export function createClient(opts: CreateClientOpts): AxiosInstance {
  const {
    baseURL,
    tokenKey = 'access_token',
    refreshPath = '/v1/auth/refresh',
    csrfPath,
    authExemptSuffixes = ['/v1/auth/login', '/v1/auth/refresh', '/v1/auth/logout'],
  } = opts

  // Always include credentials for cross-site cookie flows (login/refresh/CSRF)
  const api: AxiosInstance = axios.create({ baseURL, withCredentials: true })

  // Request: Authorization + CSRF
  api.interceptors.request.use((config: any) => {
    const url = config.url || ''
    const isExempt = authExemptSuffixes.some((s) => url.endsWith(s))
    if (!isExempt) {
      const tok = sessionStorage.getItem(tokenKey)
      if (tok) {
        config.headers = (config.headers || {}) as any
        if (!config.headers['Authorization']) {
          config.headers['Authorization'] = `Bearer ${tok}`
        }
      }
    }
    const method = (config.method || 'get').toUpperCase()
    const isSafe = ['GET', 'HEAD', 'OPTIONS'].includes(method)
    if (!isSafe) {
      const csrf = getCookie('csrf_token') || getCookie('csrftoken') || getCookie('XSRF-TOKEN')
      if (csrf) {
        config.headers = (config.headers || {}) as any
        if (!config.headers['X-CSRFToken'] && !config.headers['X-CSRF-Token']) {
          config.headers['X-CSRFToken'] = csrf
        }
      }
    }
    return config
  })

  // Response: 401 -> intenta refresh una vez
  let inflight: Promise<string | null> | null = null
  api.interceptors.response.use(undefined, async (error: any) => {
    const status = error?.response?.status
    const original: any = error?.config || {}
    if (status === 401 && !original.__retried) {
      try {
        original.__retried = true
        inflight = inflight || (async () => {
          // precalienta CSRF si procede
          if (csrfPath) {
            try { await api.get(csrfPath, { withCredentials: true }) } catch {}
          }
          const r = await api.post(refreshPath, undefined, { withCredentials: true })
          const at = r?.data?.access_token as string | undefined
          if (at) sessionStorage.setItem(tokenKey, at)
          return at ?? null
        })()
        const tok = await inflight
        inflight = null
        if (tok) {
          original.headers = original.headers || {}
          original.headers['Authorization'] = `Bearer ${tok}`
          return api.request(original)
        }
      } catch {
        inflight = null
      }
    }
    throw error
  })

  return api
}

export type { AxiosInstance }
