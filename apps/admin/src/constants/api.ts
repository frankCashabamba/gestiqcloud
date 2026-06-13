/**
 * API Constants - Centralizadas
 * URLs base y rutas de API
 */

/**
 * API base URL = ORIGIN del backend (p.ej. http://localhost:8000 o
 * https://api.gestiqcloud.com), SIN sufijo /api ni /v1. El prefijo canónico
 * `/api/v1/*` va en cada ruta. Alineado con apps/admin/src/shared/api/client.ts.
 */
function resolveApiBase(rawBase?: string): string {
  const base = (rawBase || '').replace(/\/+$/g, '')
  // Defensa: si el env incluyera por error /api, /v1 o /api/v1 al final, se quita.
  return base.replace(/\/(api\/v1|api|v1)$/i, '')
}

export const API_BASE = resolveApiBase(import.meta.env.VITE_API_URL)

/**
 * API endpoint paths (prefijo canónico /api/v1)
 */
export const API_ENDPOINTS = {
  INCIDENTS: {
    LIST: `${API_BASE}/api/v1/admin/incidents`,
    GET: (id: string) => `${API_BASE}/api/v1/admin/incidents/${id}`,
    UPDATE: (id: string) => `${API_BASE}/api/v1/admin/incidents/${id}`,
  },
  LOGS: {
    LIST: `${API_BASE}/api/v1/admin/logs`,
    EXPORT: `${API_BASE}/api/v1/admin/logs/export`,
  },
  AUTH: {
    LOGIN: `${API_BASE}/api/v1/admin/auth/login`,
    LOGOUT: `${API_BASE}/api/v1/admin/auth/logout`,
  },
} as const
