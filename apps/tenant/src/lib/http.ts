// lib/http.ts - Tenant HTTP client using shared core
import { HttpClient, type HttpOptions } from '@shared-lib/http-client'
import { env } from '../env'

export const API_URL = (env.apiUrl || '/api').replace(/\/+$/g, '')

export type { HttpOptions }
export { HttpError } from '@shared-lib/http-client'

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

const httpClient = new HttpClient({
  apiUrl: API_URL,
  csrfExemptSuffixes: ['/auth/login', '/auth/refresh', '/auth/logout'],
  noAuthHeaderSuffixes: ['/auth/login', '/auth/refresh', '/auth/logout'],
  authHandlers: {
    getToken: getStoredToken,
  },
})

export async function apiFetch<T = unknown>(path: string, options?: HttpOptions): Promise<T> {
  return httpClient.fetch<T>(path, options)
}
