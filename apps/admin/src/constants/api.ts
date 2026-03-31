/**
 * API Constants - Centralizadas
 * URLs base y rutas de API
 */

/**
 * API base URL - recuperada de env var VITE_API_URL
 * En desarrollo: /v1 (proxy local)
 * En producción: https://api.gestiqcloud.com/api/v1 (vía reverse proxy)
 */
function resolveApiBase(rawBase?: string): string {
  const base = (rawBase || '/v1').replace(/\/+$/g, '')
  if (base === '' || base === '/v1') return '/v1'
  if (base.endsWith('/api/v1')) return base
  if (base.endsWith('/v1')) return base
  if (base.endsWith('/api')) return `${base}/v1`
  return `${base}/v1`
}

export const API_BASE = resolveApiBase(import.meta.env.VITE_API_URL)

/**
 * API endpoint paths
 */
export const API_ENDPOINTS = {
  INCIDENTS: {
    LIST: `${API_BASE}/admin/incidents`,
    GET: (id: string) => `${API_BASE}/admin/incidents/${id}`,
    UPDATE: (id: string) => `${API_BASE}/admin/incidents/${id}`,
  },
  LOGS: {
    LIST: `${API_BASE}/admin/logs`,
    EXPORT: `${API_BASE}/admin/logs/export`,
  },
  AUTH: {
    LOGIN: `${API_BASE}/admin/auth/login`,
    LOGOUT: `${API_BASE}/admin/auth/logout`,
  },
} as const
