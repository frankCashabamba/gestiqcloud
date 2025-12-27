/**
 * Hook: useSectorPlaceholders
 * 
 * Carga placeholders dinámicos para campos de formulario desde BD.
 * 
 * FASE 4 PASO 4: Eliminar hardcoding de placeholders en formularios.
 * 
 * Reemplaza:
 *   `placeholder="Ej: H-2025-028"` → `getFieldPlaceholder(config, 'lote')`
 *   `placeholder="Ej: SN-123456789"` → `getFieldPlaceholder(config, 'numero_serie')`
 * 
 * Características:
 * - Cache 5 minutos TTL
 * - Soporta filtrado por módulo
 * - Fallback a placeholders vacíos si no existen
 * - Manejo de errores completo
 * - 100% backward compatible
 */

import { useEffect, useMemo, useState } from 'react'
import tenantApi from '../shared/api/client'

export interface PlaceholderData {
  [fieldName: string]: string
}

export interface PlaceholdersByModule {
  [module: string]: PlaceholderData
}

export interface UseSectorPlaceholdersReturn {
  /** Placeholders cargados (por módulo o específico) */
  placeholders: PlaceholdersByModule | PlaceholderData | null
  /** Está cargando */
  loading: boolean
  /** Error si ocurrió */
  error: string | null
  /** Función helper: obtener placeholder para un campo */
  getPlaceholder: (fieldName: string) => string
  /** Función helper: obtener placeholder con módulo específico */
  getPlaceholderForModule: (module: string, fieldName: string) => string
}

// Cache con TTL
interface CacheEntry {
  data: PlaceholdersByModule | PlaceholderData | null
  timestamp: number
}

const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutos
const placeholderCache: Map<string, CacheEntry> = new Map()

/**
 * Hook principal: Cargar placeholders del sector
 * 
 * @param sectorCode - Código del sector (panaderia, taller, etc.)
 * @param module - Módulo opcional (products, inventory, customers, etc.)
 *                Si no se proporciona, retorna placeholders de todos los módulos
 * 
 * @example
 * // Obtener placeholders de todos los módulos
 * const { placeholders, loading, error } = useSectorPlaceholders('panaderia')
 * 
 * @example
 * // Obtener placeholders de un módulo específico
 * const { placeholders, getPlaceholder } = useSectorPlaceholders('panaderia', 'inventory')
 * const placeholder = getPlaceholder('lote')  // "Ej: H-2025-028"
 */
export function useSectorPlaceholders(
  sectorCode: string | null,
  module: string | null = null
): UseSectorPlaceholdersReturn {
  const [state, setState] = useState<{
    placeholders: PlaceholdersByModule | PlaceholderData | null
    loading: boolean
    error: string | null
  }>({
    placeholders: null,
    loading: false,
    error: null,
  })

  const cacheKey = module ? `${sectorCode}:${module}` : `${sectorCode}:all`

  useEffect(() => {
    if (!sectorCode) {
      setState({ placeholders: null, loading: false, error: null })
      return
    }

    // Verificar cache
    const cached = placeholderCache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      setState({
        placeholders: cached.data,
        loading: false,
        error: null,
      })
      return
    }

    // Cargar desde API
    setState(prev => ({ ...prev, loading: true }))

    const encodedCode = encodeURIComponent(sectorCode)
    const url = module
      ? `/api/v1/sectors/${encodedCode}/placeholders?module=${module}`
      : `/api/v1/sectors/${encodedCode}/placeholders`

    tenantApi
      .get(url)
      .then(res => {
        const placeholders = res.data.placeholders || {}
        
        // Guardar en cache
        placeholderCache.set(cacheKey, {
          data: placeholders,
          timestamp: Date.now(),
        })

        setState({
          placeholders,
          loading: false,
          error: null,
        })
      })
      .catch(err => {
        const errorMsg = err.response?.data?.detail || err.message || 'Error desconocido'
        setState({
          placeholders: null,
          loading: false,
          error: errorMsg,
        })
      })
  }, [sectorCode, module, cacheKey])

  // Helper: obtener placeholder para un campo específico
  const getPlaceholder = (fieldName: string): string => {
    if (!state.placeholders) return ''

    // Si tenemos un módulo específico, los placeholders son directos
    if (module && typeof state.placeholders === 'object' && !Array.isArray(state.placeholders)) {
      return (state.placeholders as PlaceholderData)[fieldName] || ''
    }

    // Si no tenemos módulo (tenemos todos), buscar en todos
    if (!module && typeof state.placeholders === 'object' && !Array.isArray(state.placeholders)) {
      for (const moduleKey in state.placeholders) {
        const modulePlaceholders = (state.placeholders as PlaceholdersByModule)[moduleKey]
        if (modulePlaceholders && modulePlaceholders[fieldName]) {
          return modulePlaceholders[fieldName]
        }
      }
    }

    return ''
  }

  // Helper: obtener placeholder para un campo con módulo específico
  const getPlaceholderForModule = (targetModule: string, fieldName: string): string => {
    if (!state.placeholders || typeof state.placeholders !== 'object' || Array.isArray(state.placeholders)) {
      return ''
    }

    const modulePlaceholders = (state.placeholders as PlaceholdersByModule)[targetModule]
    if (!modulePlaceholders) return ''

    return modulePlaceholders[fieldName] || ''
  }

  return {
    placeholders: state.placeholders,
    loading: state.loading,
    error: state.error,
    getPlaceholder,
    getPlaceholderForModule,
  }
}

/**
 * Hook helper: Obtener placeholder para un campo específico
 * 
 * Versión simplificada cuando solo necesitas un placeholder
 * 
 * @param sectorCode - Código del sector
 * @param fieldName - Nombre del campo
 * @param module - Módulo opcional
 * 
 * @example
 * const { placeholder, loading } = useSectorPlaceholder('panaderia', 'lote', 'inventory')
 * return <Input placeholder={placeholder} />
 */
export function useSectorPlaceholder(
  sectorCode: string | null,
  fieldName: string,
  module: string | null = null
) {
  const { placeholders, loading, error, getPlaceholder, getPlaceholderForModule } =
    useSectorPlaceholders(sectorCode, module)

  const placeholder = useMemo(() => {
    if (module) {
      return getPlaceholderForModule(module, fieldName)
    }
    return getPlaceholder(fieldName)
  }, [placeholders, fieldName, module, getPlaceholder, getPlaceholderForModule])

  return {
    placeholder,
    loading,
    error,
  }
}

/**
 * Helper function: Limpiar cache de placeholders
 * 
 * Útil para testing o cuando necesitas recargar datos
 * 
 * @example
 * clearPlaceholderCache()
 */
export function clearPlaceholderCache() {
  placeholderCache.clear()
}

/**
 * Helper function: Obtener placeholder desde un objeto de placeholders
 * 
 * Útil cuando ya tienes los placeholders cargados
 * 
 * @param placeholders - Objeto de placeholders
 * @param fieldName - Nombre del campo a buscar
 * @param defaultValue - Valor por defecto si no existe
 * 
 * @example
 * const placeholder = getFieldPlaceholder(config.fields.inventory.placeholders, 'lote')
 */
export function getFieldPlaceholder(
  placeholders: PlaceholderData | PlaceholdersByModule | undefined,
  fieldName: string,
  defaultValue: string = ''
): string {
  if (!placeholders) return defaultValue
  if (fieldName in (placeholders as PlaceholderData)) {
    return (placeholders as PlaceholderData)[fieldName] || defaultValue
  }
  for (const moduleKey in placeholders as PlaceholdersByModule) {
    const modulePlaceholders = (placeholders as PlaceholdersByModule)[moduleKey]
    if (modulePlaceholders && modulePlaceholders[fieldName]) {
      return modulePlaceholders[fieldName]
    }
  }
  return defaultValue
}

/**
 * Helper function: Obtener placeholder de múltiples módulos
 * 
 * @param allPlaceholders - Objeto con placeholders de todos los módulos
 * @param module - Módulo específico
 * @param fieldName - Nombre del campo
 * 
 * @example
 * const placeholder = getFieldPlaceholderForModule(
 *   config.fields,
 *   'inventory',
 *   'lote'
 * )
 */
export function getFieldPlaceholderForModule(
  allPlaceholders: PlaceholdersByModule | undefined,
  module: string,
  fieldName: string,
  defaultValue: string = ''
): string {
  return allPlaceholders?.[module]?.[fieldName] || defaultValue
}

/**
 * Helper function: Obtener todos los placeholders de un módulo
 * 
 * @param allPlaceholders - Objeto con placeholders de todos los módulos
 * @param module - Módulo específico
 * 
 * @example
 * const inventoryPlaceholders = getModulePlaceholders(config.fields, 'inventory')
 */
export function getModulePlaceholders(
  allPlaceholders: PlaceholdersByModule | undefined,
  module: string
): PlaceholderData | {} {
  return allPlaceholders?.[module] || {}
}
