/**
 * API Constants - Centralizadas
 * Rutas y versiones de API
 */

/**
 * API version
 * En futuras migraciones, cambiar aquí en un solo lugar
 */
export const API_VERSION = 'v1'

/**
 * API path prefixes
 */
export const API_PATHS = {
  // Base paths
  BASE: `/api/${API_VERSION}`,
  TENANT: `/api/${API_VERSION}/tenant`,
  ADMIN: `/api/${API_VERSION}/admin`,

  // Authentication
  AUTH: {
    LOGIN: `/api/${API_VERSION}/tenant/auth/login`,
    LOGOUT: `/api/${API_VERSION}/tenant/auth/logout`,
    REFRESH: `/api/${API_VERSION}/tenant/auth/refresh`,
    ME: `/api/${API_VERSION}/me/tenant`,
  },

  // Tenant modules
  POS: {
    REGISTERS: `/api/${API_VERSION}/tenant/pos/registers`,
    RECEIPTS: `/api/${API_VERSION}/tenant/pos/receipts`,
  },

  // Inventario
  INVENTARIO: {
    WAREHOUSES: `/api/${API_VERSION}/tenant/inventario/warehouses`,
    PRODUCTOS: `/api/${API_VERSION}/tenant/inventario/productos`,
  },
} as const
