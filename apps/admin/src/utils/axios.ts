// src/utils/axios.ts
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

/** Base URL: usa VITE_BACKEND_URL si existe, si no VITE_API_URL, si no '/api' */
const API_BASE = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || '/api'

/** Keys de token (principal y fallback) */
const TOKEN_KEY = 'access_token_admin'
const FALLBACK_KEY = 'access_token' // por si algo del código viejo la usa

/** Endpoints a excluir de Authorization y de CSRF si lo gestionas aparte */
const AUTH_EXEMPT_SUFFIXES = [
  '/v1/admin/auth/login',
  '/v1/auth/login',
  '/api/login',
  '/v1/auth/refresh',
  '/api/refresh',
  '/v1/auth/logout',
  '/api/logout',
]

/** Helpers de token */
const getToken = (): string | null =>
  sessionStorage.getItem(TOKEN_KEY) ||
  sessionStorage.getItem(FALLBACK_KEY) ||
  localStorage.getItem(TOKEN_KEY) ||
  localStorage.getItem(FALLBACK_KEY)

const setToken = (t: string) => {
  sessionStorage.setItem(TOKEN_KEY, t)
}

const clearToken = () => {
  sessionStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(FALLBACK_KEY)
}

const redirectToLogin = () => {
  if (location.pathname !== '/login') location.href = '/login'
}

/** Crea la instancia */
const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // para enviar cookie del refresh
})

/** Extras que colgamos del config */
type Extra = { _retry?: boolean; retryOn401?: boolean; skipAuth?: boolean }
type Cfg = InternalAxiosRequestConfig & Extra

/* ------------------ REQUEST: añade Authorization salvo login/refresh ------------------ */
api.interceptors.request.use((config) => {
  const cfg = config as Cfg
  const url = cfg.url || ''
  const exempt = cfg.skipAuth || AUTH_EXEMPT_SUFFIXES.some((s) => url.endsWith(s))

  if (!exempt) {
    const tok = getToken()
    if (tok) {
      // Añade sin reemplazar el objeto headers (Axios v1 tipa AxiosHeaders)
      ;(cfg.headers as any).Authorization = `Bearer ${tok}`
      ;(cfg.headers as any).set?.('Authorization', `Bearer ${tok}`)
    }
  }

  if (typeof cfg.retryOn401 === 'undefined') cfg.retryOn401 = true
  return cfg
})

/* ------------------ RESPONSE: 401 → refresh (deduplicado) ------------------ */
let isRefreshing = false
let waiters: Array<(t: string) => void> = []
const notifyWaiters = (t: string) => {
  waiters.forEach((cb) => cb(t))
  waiters = []
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const resp = error.response
    const cfg = (error.config || {}) as Cfg

    // Si 401 y vamos a reintentar con refresh
    if (resp?.status === 401 && cfg.retryOn401 && !cfg._retry) {
      cfg._retry = true

      if (isRefreshing) {
        // Espera a que termine el refresh en curso
        const newTok = await new Promise<string>((resolve) => waiters.push(resolve))
        ;(cfg.headers as any).Authorization = `Bearer ${newTok}`
        ;(cfg.headers as any).set?.('Authorization', `Bearer ${newTok}`)
        return api(cfg)
      }

      isRefreshing = true
      try {
        // Refresh SIN Authorization; sólo cookie
        const refreshRes = await api.post<{ access_token: string }>(
          '/v1/auth/refresh',
          undefined,
          { skipAuth: true, retryOn401: false } as any
        )
        const newToken = refreshRes.data?.access_token
        if (!newToken) throw new Error('No access_token')

        setToken(newToken)
        notifyWaiters(newToken)

        ;(cfg.headers as any).Authorization = `Bearer ${newToken}`
        ;(cfg.headers as any).set?.('Authorization', `Bearer ${newToken}`)
        return api(cfg)
      } catch (e) {
        clearToken()
        waiters = []
        redirectToLogin()
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }

    // Otros 401 (sin refresh permitido o ya reintentado)
    if (resp?.status === 401) {
      clearToken()
      redirectToLogin()
    }

    return Promise.reject(error)
  }
)

export default api
