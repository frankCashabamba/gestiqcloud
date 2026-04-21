/**
 * useSimpleFetch - Hook simplificado para casos básicos
 * Sin sobreingeniería de race conditions para operaciones simples
 */

import { useState, useCallback, useEffect } from 'react'

export interface SimpleFetchState<T> {
  items: T[]
  loading: boolean
  error: string | null
}

export interface SimpleFetchConfig<T> {
  endpoint: string
  onSuccess?: (items: T[]) => void
  onError?: (error: string) => void
}

export function useSimpleFetch<T = any>(config: SimpleFetchConfig<T>) {
  const { endpoint, onSuccess, onError } = config

  const [state, setState] = useState<SimpleFetchState<T>>({
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

  // Auto-fetch al montar
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
