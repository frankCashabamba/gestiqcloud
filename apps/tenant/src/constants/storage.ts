/**
 * Storage keys centralizados
 * Todas las claves de localStorage/sessionStorage en un único lugar
 *
 * Token storage hierarchy (see AuthContext.setAuthToken):
 *  - sessionStorage[AUTH.TOKEN]          => runtime source of truth (cleared on tab close).
 *  - localStorage [AUTH.FALLBACK_TOKEN]  => recovery fallback, kept in sync with sessionStorage.
 *  - IndexedDB    (offlineAuth snapshot) => offline-mode snapshot, refreshed only via
 *                                           saveOfflineSessionSnapshot when an online
 *                                           profile load succeeds.
 */

const AUTH_TOKEN_SESSION_KEY = 'access_token_tenant'
const AUTH_TOKEN_FALLBACK_KEY = 'authToken'

export const STORAGE_KEYS = {
  // Authentication
  AUTH: {
    TOKEN: AUTH_TOKEN_SESSION_KEY,
    FALLBACK_TOKEN: AUTH_TOKEN_FALLBACK_KEY,
  },

  // POS Module
  POS: {
    DRAFT_STATE: 'posDraftState',
  },

  // Importador Module
  IMPORTADOR: {
    // Reuse the constant so we cannot drift from AUTH.TOKEN.
    SESSION_TOKEN: AUTH_TOKEN_SESSION_KEY,
  },

  // Auth Context
  AUTH_CONTEXT: {
    TOKEN: AUTH_TOKEN_SESSION_KEY,
  },
} as const

/**
 * Convenience exports para acceso simple
 *
 * - TOKEN_KEY: clave usada en sessionStorage (fuente de verdad runtime)
 * - AUTH_TOKEN_KEY: alias histórico de TOKEN_KEY; mantenido por compatibilidad
 * - AUTH_FALLBACK_TOKEN_KEY: clave usada en localStorage como recovery fallback
 */
export const TOKEN_KEY = STORAGE_KEYS.AUTH.TOKEN
export const POS_DRAFT_KEY = STORAGE_KEYS.POS.DRAFT_STATE
export const AUTH_TOKEN_KEY = STORAGE_KEYS.AUTH.TOKEN
export const AUTH_FALLBACK_TOKEN_KEY = STORAGE_KEYS.AUTH.FALLBACK_TOKEN
