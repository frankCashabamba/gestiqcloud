/**
 * Permissionsache
 *
 * Almacena permisos en sessionStorage con TTL.
 * Usado por PermissionsContext para evitar fetch innecesarios.
 */

export type PermissionDict = Record<string, Record<string, boolean>>

interface CacheEntry {
  data: PermissionDict
  timestamp: number
}

const CACHE_KEY = 'gestiqcloud_permissions_cache'
const DEFAULT_TTL_MS = 5 * 60 * 1000 // 5 minutos

export const permissionsCache = {
  /**
   * Obtener permisos del caché
   */
  get(): PermissionDict | null {
    try {
      const stored = sessionStorage.getItem(CACHE_KEY)
      if (!stored) return null

      const entry: CacheEntry = JSON.parse(stored)
      const now = Date.now()
      const age = now - entry.timestamp

      if (age > DEFAULT_TTL_MS) {
        // Expirado
        sessionStorage.removeItem(CACHE_KEY)
        return null
      }

      return entry.data
    } catch {
      return null
    }
  },

  /**
   * Guardar permisos en caché
   */
  set(data: PermissionDict): void {
    try {
      const entry: CacheEntry = {
        data,
        timestamp: Date.now(),
      }
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(entry))
    } catch {
      // Silenciar: sessionStorage puede estar lleno o deshabilitado
    }
  },

  /**
   * Limpiar caché (ej: al logout)
   */
  clear(): void {
    try {
      sessionStorage.removeItem(CACHE_KEY)
    } catch {
      // Silenciar
    }
  },

  /**
   * Verificar si caché es válido
   */
  isValid(): boolean {
    return this.get() !== null
  },

  /**
   * Obtener edad del caché en ms
   */
  getAge(): number | null {
    try {
      const stored = sessionStorage.getItem(CACHE_KEY)
      if (!stored) return null

      const entry: CacheEntry = JSON.parse(stored)
      return Date.now() - entry.timestamp
    } catch {
      return null
    }
  },
}
