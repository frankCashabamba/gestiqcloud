/**
 * Service para obtener módulos disponibles filtrados por sector
 * FASE: Multi-sector module availability
 * No hardcodes - totalmente dinámico desde backend
 */

import { apiClient } from './api'

export interface ModuleInfo {
  id: string
  name: string
  icon: string
  category: string
  description: string
  required: boolean
  default_enabled: boolean
  dependencies: string[]
  countries: string[]
  sectors?: string[] | null
}

export interface GetModulesResponse {
  sector: string | null
  modules: ModuleInfo[]
  total: number
}

const CACHE_TTL_MS = 60000 // 1 minute

interface CacheEntry {
  data: GetModulesResponse
  timestamp: number
}

const moduleCache = new Map<string, CacheEntry>()

/**
 * Obtiene módulos disponibles para un sector específico
 * @param sector - Código del sector (ej: 'retail', 'bakery', 'workshop')
 * @param country - Código ISO del país (ej: 'ES', 'EC')
 * @param useCache - Si usar cache (default: true)
 */
export async function getSectorModules(
  sector?: string,
  country?: string,
  useCache = true
): Promise<GetModulesResponse> {
  // Generar clave de cache
  const cacheKey = `${sector || 'all'}:${country || 'all'}`

  // Verificar cache
  if (useCache) {
    const cached = moduleCache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return cached.data
    }
  }

  try {
    // Construir query params dinámicamente
    const params = new URLSearchParams()
    if (sector) {
      params.append('sector', sector)
    }
    if (country) {
      params.append('country', country)
    }

    const response = await apiClient.get<GetModulesResponse>(
      `/api/v1/modules/sector${params.toString() ? `?${params}` : ''}`
    )

    // Guardar en cache
    moduleCache.set(cacheKey, {
      data: response.data,
      timestamp: Date.now(),
    })

    return response.data
  } catch (error) {
    console.error('Error getting sector modules:', error)
    throw error
  }
}

/**
 * Obtiene módulos disponibles para el sector actual del tenant
 * (el endpoint debe obtener el sector del contexto del request)
 */
export async function getTenantModules(
  country?: string
): Promise<GetModulesResponse> {
  // Llamar sin sector para que el backend lo obtenga del context
  return getSectorModules(undefined, country)
}

/**
 * Valida si un módulo está disponible en un sector
 */
export function isModuleAvailableInSector(
  module: ModuleInfo,
  sector?: string
): boolean {
  // Si el módulo no tiene restricción de sector, está disponible
  if (!module.sectors) {
    return true
  }

  // Si no tenemos sector, denegar por precaución
  if (!sector) {
    return false
  }

  // Verificar si el sector está en la lista
  return module.sectors.includes(sector)
}

/**
 * Limpia el cache de módulos
 */
export function clearModuleCache(): void {
  moduleCache.clear()
}

/**
 * Obtiene etiqueta legible para un sector
 */
export function getSectorLabel(sector: string): string {
  const sectorLabels: Record<string, string> = {
    retail: 'Retail',
    bakery: 'Bakery',
    workshop: 'Workshop',
    panaderia: 'Bakery',
    taller: 'Workshop',
  }

  return sectorLabels[sector.toLowerCase()] || sector.toUpperCase()
}
