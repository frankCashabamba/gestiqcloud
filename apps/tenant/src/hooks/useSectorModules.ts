/**
 * Hook para validar disponibilidad de módulos según sector
 * FASE: Multi-sector module visibility control
 *
 * No hardcoded sector logic - fully dynamic and configurable
 */

import { useMemo } from 'react'
import { useTenant } from './useTenant'
import { useTranslation } from 'react-i18next'

export interface ModuleInfo {
  id: string
  name: string
  icon: string
  sectors?: string[] | null
  countries: string[]
  required: boolean
  default_enabled: boolean
  dependencies: string[]
}

export interface ModuleRestriction {
  isAllowed: boolean
  reason?: string
  sectors?: string[] | null
}

/**
 * Hook para verificar si un módulo está disponible para el sector actual
 */
export function useSectorModules() {
  const { t } = useTranslation()
  const { tenant } = useTenant()

  // Get sector from tenant (no hardcode)
  const sector = useMemo(() => {
    return tenant?.sector_code?.toLowerCase() || null
  }, [tenant?.sector_code])

  /**
   * Valida si un módulo está disponible para el sector actual
   *
   * @param module - Información del módulo
   * @returns Restricción indicando si está permitido y por qué no si es negado
   */
  const isModuleAllowedInSector = (module: ModuleInfo): ModuleRestriction => {
    // Si no hay sectores especificados, está disponible para todos
    if (!module.sectors) {
      return {
        isAllowed: true,
      }
    }

    // Si no tenemos sector del tenant, denegar por precaución
    if (!sector) {
      return {
        isAllowed: false,
        reason: t('errors.sectorNotDefined'),
        sectors: module.sectors,
      }
    }

    // Verificar si el sector actual está en la lista de sectores permitidos
    const isAllowed = module.sectors.includes(sector)

    if (!isAllowed) {
      return {
        isAllowed: false,
        reason: t('errors.moduleNotAvailableForSector', {
          sector: sector,
          availableSectors: module.sectors.join(', '),
        }),
        sectors: module.sectors,
      }
    }

    return {
      isAllowed: true,
      sectors: module.sectors,
    }
  }

  /**
   * Obtiene descripción legible de los sectores permitidos
   */
  const getSectorLabels = (sectors: string[] | null | undefined): string => {
    if (!sectors) {
      return t('common.all')
    }

    // Traducir nombres de sectores
    const sectorLabels = sectors.map((s) => {
      // Mapeo dinámico de códigos de sector a etiquetas i18n
      const sectorKey = `sectors.${s}`
      const translated = t(sectorKey)
      // Si no está traducido, retornar el código en mayúscula
      return translated === sectorKey ? s.toUpperCase() : translated
    })

    return sectorLabels.join(', ')
  }

  return {
    sector,
    isModuleAllowedInSector,
    getSectorLabels,
  }
}

/**
 * Hook para filtrar módulos disponibles en el sector actual
 */
export function useAvailableModulesForSector(
  modules: ModuleInfo[]
): ModuleInfo[] {
  const { isModuleAllowedInSector } = useSectorModules()

  return useMemo(() => {
    return modules.filter((module) => {
      const restriction = isModuleAllowedInSector(module)
      return restriction.isAllowed
    })
  }, [modules, isModuleAllowedInSector])
}
