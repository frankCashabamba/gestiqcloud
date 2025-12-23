import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

export type ClientConfig = {
  baseURL?: string
  tokenKey: string
  refreshPath: string
  csrfPath: string
  authExemptSuffixes?: string[]
}

type Extra = { _retry?: boolean; _retryCsrf?: boolean; retryOn401?: boolean; skipAuth?: boolean }
type Cfg = InternalAxiosRequestConfig & Extra

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return m ? decodeURIComponent(m[1]) : null
}

export function createClient(cfg: ClientConfig): AxiosInstance {
  // Default API path exposed at the gateway is '/v1'
  const baseURL = (cfg.baseURL ?? '/v1').replace(/\/+$/g, '')
  const authExempt = cfg.authExemptSuffixes ?? []

  const api = axios.create({ baseURL, withCredentials: true })

  const getToken = () =>
    sessionStorage.getItem(cfg.tokenKey) || localStorage.getItem(cfg.tokenKey)
  const setToken = (t: string) => {
    sessionStorage.setItem(cfg.tokenKey, t)
  }
  const clearToken = () => {
    sessionStorage.removeItem(cfg.tokenKey)
    localStorage.removeItem(cfg.tokenKey)
  }

  const isExempt = (url?: string) => !!url && authExempt.some((s) => url.endsWith(s))

  api.interceptors.request.use((config) => {
    const cfgReq = config as Cfg
    const url = cfgReq.url || ''
    const exempt = cfgReq.skipAuth || isExempt(url)

    if (!exempt) {
      const tok = getToken()
      if (tok) {
        ;(cfgReq.headers as any).Authorization = `Bearer ${tok}`
        ;(cfgReq.headers as any).set?.('Authorization', `Bearer ${tok}`)
      }
      // CSRF on unsafe methods
      const m = (cfgReq.method || 'get').toUpperCase()
      if (m === 'POST' || m === 'PUT' || m === 'PATCH' || m === 'DELETE') {
        const csrf = getCookie('csrf_token') || getCookie('XSRF-TOKEN') || getCookie('csrftoken')
        if (csrf) {
          ;(cfgReq.headers as any)['X-CSRF-Token'] = csrf
          ;(cfgReq.headers as any).set?.('X-CSRF-Token', csrf)
        }
      }
    }
    if (typeof cfgReq.retryOn401 === 'undefined') cfgReq.retryOn401 = true
    return cfgReq
  })

  let isRefreshing = false
  let waiters: Array<(t: string) => void> = []
  const notifyWaiters = (t: string) => {
    waiters.forEach((cb) => cb(t))
    waiters = []
  }

  api.interceptors.response.use(
    (r: any) => r,
    async (error: AxiosError) => {
      const resp = error.response
      const cfgRes = (error.config || {}) as Cfg

      const hadToken = !!getToken()
      if (resp?.status === 401 && cfgRes.retryOn401 && !cfgRes._retry && hadToken) {
        cfgRes._retry = true

        if (isRefreshing) {
          const newTok = await new Promise<string>((resolve) => waiters.push(resolve))
          ;(cfgRes.headers as any).Authorization = `Bearer ${newTok}`
          ;(cfgRes.headers as any).set?.('Authorization', `Bearer ${newTok}`)
          return api(cfgRes)
        }

        isRefreshing = true
        try {
          const refreshRes = await api.post<{ access_token: string }>(cfg.refreshPath, undefined, {
            skipAuth: true,
            retryOn401: false,
          } as any)
          const newToken = refreshRes.data?.access_token
          if (!newToken) throw new Error('No access_token')
          setToken(newToken)
          notifyWaiters(newToken)
          ;(cfgRes.headers as any).Authorization = `Bearer ${newToken}`
          ;(cfgRes.headers as any).set?.('Authorization', `Bearer ${newToken}`)
          return api(cfgRes)
        } catch (e) {
          clearToken()
          waiters = []
          throw e
        } finally {
          isRefreshing = false
        }
      }

      if (resp?.status === 403 && !cfgRes._retryCsrf) {
        try {
          cfgRes._retryCsrf = true
          await api.get(cfg.csrfPath, { skipAuth: true } as any)
          return api(cfgRes)
        } catch (e) {}
      }

      return Promise.reject(error)
    }
  )

  return api
}
