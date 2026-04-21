/**
 * useSimpleList - Hook optimizado para listas simples
 * Elimina overhead de useCRUD para casos básicos
 */

import { useState, useCallback, useEffect } from 'react'

export interface SimpleListState<T> {
  items: T[]
  loading: boolean
  error: string | null
}

export interface SimpleListConfig<T> {
  endpoint: string
  onSuccess?: (items: T[]) => void
  onError?: (error: string) => void
}

export function useSimpleList<T = any>(config: SimpleListConfig<T>) {
  const { endpoint, onSuccess, onError } = config

  const [state, setState] = useState<SimpleListState<T>>({
    items: [],
    loading: false,
    error: null
  })

  const fetchItems = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))

      const response = await fetch(endpoint)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      const items = Array.isArray(data) ? data : (data.items || [])

      setState({ items, loading: false, error: null })
      onSuccess?.(items)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido'
      setState(prev => ({ ...prev, loading: false, error: errorMsg }))
      onError?.(errorMsg)
    }
  }, [endpoint, onSuccess, onError])

  const refresh = useCallback(() => {
    fetchItems()
  }, [fetchItems])

  const setItems = useCallback((items: T[]) => {
    setState(prev => ({ ...prev, items }))
  }, [])

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }))
  }, [])

  // Auto-fetch al montar - sin dependencias que causen re-renders
  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  return {
    ...state,
    refresh,
    setItems,
    setError
  }
}
