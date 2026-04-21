/**
 * Hook genérico para manejo de filtros
 */
import { useState, useCallback } from 'react'

export interface FilterState {
  filters: Record<string, any>
  search: string
  activeFilters: string[]
}

export interface FilterActions {
  setFilter: (key: string, value: any) => void
  removeFilter: (key: string) => void
  clearFilters: () => void
  setSearch: (search: string) => void
  clearSearch: () => void
  getFilterParams: () => Record<string, any>
  hasActiveFilters: () => boolean
}

export interface UseFiltersConfig {
  initialFilters?: Record<string, any>
  initialSearch?: string
}

export function useFilters(config: UseFiltersConfig = {}): FilterState & FilterActions {
  const { initialFilters = {}, initialSearch = '' } = config

  const [state, setState] = useState<FilterState>({
    filters: initialFilters,
    search: initialSearch,
    activeFilters: Object.keys(initialFilters).filter(key => initialFilters[key] !== undefined && initialFilters[key] !== null && initialFilters[key] !== '')
  })

  const setFilter = useCallback((key: string, value: any) => {
    setState(prev => {
      const newFilters = { ...prev.filters, [key]: value }
      const newActiveFilters = Object.keys(newFilters).filter(k =>
        newFilters[k] !== undefined && newFilters[k] !== null && newFilters[k] !== ''
      )
      return {
        ...prev,
        filters: newFilters,
        activeFilters: newActiveFilters
      }
    })
  }, [])

  const removeFilter = useCallback((key: string) => {
    setState(prev => {
      const newFilters = { ...prev.filters }
      delete newFilters[key]
      const newActiveFilters = Object.keys(newFilters).filter(k =>
        newFilters[k] !== undefined && newFilters[k] !== null && newFilters[k] !== ''
      )
      return {
        ...prev,
        filters: newFilters,
        activeFilters: newActiveFilters
      }
    })
  }, [])

  const clearFilters = useCallback(() => {
    setState(prev => ({
      ...prev,
      filters: {},
      activeFilters: []
    }))
  }, [])

  const setSearch = useCallback((search: string) => {
    setState(prev => ({ ...prev, search }))
  }, [])

  const clearSearch = useCallback(() => {
    setState(prev => ({ ...prev, search: '' }))
  }, [])

  const getFilterParams = useCallback(() => {
    const params: Record<string, any> = {}

    // Agregar filtros activos
    Object.entries(state.filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params[key] = value
      }
    })

    // Agregar búsqueda si existe
    if (state.search.trim()) {
      params.search = state.search.trim()
    }

    return params
  }, [state.filters, state.search])

  const hasActiveFilters = useCallback(() => {
    return state.activeFilters.length > 0 || state.search.trim() !== ''
  }, [state.activeFilters, state.search])

  return {
    ...state,
    setFilter,
    removeFilter,
    clearFilters,
    setSearch,
    clearSearch,
    getFilterParams,
    hasActiveFilters
  }
}
