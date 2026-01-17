/**
 * Storage keys centralizados
 * Todas las claves de localStorage/sessionStorage en un único lugar
 */

export const STORAGE_KEYS = {
  // Authentication
  AUTH: {
    TOKEN: 'access_token_tenant',
    FALLBACK_TOKEN: 'authToken',
  },

  // POS Module
  POS: {
    DRAFT_STATE: 'posDraftState',
  },

  // Importador Module
  IMPORTADOR: {
    SESSION_TOKEN: 'access_token_tenant', // mismo que AUTH.TOKEN
  },

  // Auth Context
  AUTH_CONTEXT: {
    TOKEN: 'access_token_tenant',
  },
} as const

/**
 * Convenience exports para acceso simple
 */
export const TOKEN_KEY = STORAGE_KEYS.AUTH.TOKEN
export const POS_DRAFT_KEY = STORAGE_KEYS.POS.DRAFT_STATE
export const AUTH_TOKEN_KEY = STORAGE_KEYS.AUTH.TOKEN
