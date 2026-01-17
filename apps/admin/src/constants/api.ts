/**
 * API Constants - Centralizadas
 * URLs base y rutas de API
 */

/**
 * API base URL - recuperada de env var VITE_API_URL
 * En desarrollo: /v1 (proxy local)
 * En producción: https://api.gestiqcloud.com/api/v1 (vía reverse proxy)
 */
export const API_BASE = import.meta.env.VITE_API_URL || '/v1'

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
