/**
 * Hook genérico para operaciones CRUD
 * Elimina duplicación de lógica de estado y operaciones básicas
 */
import { useState, useCallback, useEffect, useRef } from 'react'
import type { ZodSchema } from 'zod'

export interface CRUDState<T> {
  items: T[]
  loading: boolean
  error: string | null
  pagination: {
    page: number
    perPage: number
    total: number
    pages: number
  }
}

export interface CRUDActions<T> {
  fetchItems: (params?: FetchParams) => Promise<void>
  createItem: (item: Partial<T>) => Promise<T | null>
  updateItem: (id: string, item: Partial<T>) => Promise<T | null>
  deleteItem: (id: string) => Promise<boolean>
  refreshItems: () => Promise<void>
  setItems: (items: T[]) => void
  setError: (error: string | null) => void
}

export interface FetchParams {
  page?: number
  perPage?: number
  sortBy?: string
  order?: 'asc' | 'desc'
  filters?: Record<string, any>
}

export interface UseCRUDConfig<T> {
  endpoint: string
  schema: ZodSchema<T>
  defaultPerPage?: number
  onSuccess?: (action: string, data: any) => void
  onError?: (error: string) => void
}

export function useCRUD<T = any>(config: UseCRUDConfig<T>): CRUDState<T> & CRUDActions<T> {
  const { endpoint, schema, defaultPerPage = 20, onSuccess, onError } = config

  const [state, setState] = useState<CRUDState<T>>({
    items: [],
    loading: false,
    error: null,
    pagination: {
      page: 1,
      perPage: defaultPerPage,
      total: 0,
      pages: 0
    }
  })

  // Refs para race condition protection
  const requestCounter = useRef(0)
  const abortControllers = useRef<Map<number, AbortController>>(new Map())

  const updateState = useCallback((updates: Partial<CRUDState<T>>) => {
    setState(prev => ({ ...prev, ...updates }))
  }, [])

  const handleSuccess = useCallback((action: string, data: any) => {
    onSuccess?.(action, data)
  }, [onSuccess])

  const handleError = useCallback((error: string) => {
    updateState({ error })
    onError?.(error)
  }, [updateState, onError])

  // Cleanup function para cancelar requests pendientes
  const cleanupRequest = useCallback((requestId: number) => {
    const controller = abortControllers.current.get(requestId)
    if (controller) {
      controller.abort()
      abortControllers.current.delete(requestId)
    }
  }, [])

  // Cleanup en unmount
  useEffect(() => {
    return () => {
      // Cancelar todos los requests pendientes
      abortControllers.current.forEach(controller => controller.abort())
      abortControllers.current.clear()
    }
  }, [])

  const fetchItems = useCallback(async (params: FetchParams = {}) => {
    try {
      updateState({ loading: true, error: null })
      
      const queryParams = new URLSearchParams({
        page: String(params.page || state.pagination.page),
        per_page: String(params.perPage || state.pagination.perPage),
        ...(params.sortBy && { sort_by: params.sortBy }),
        ...(params.order && { order: params.order }),
        ...(params.filters && Object.entries(params.filters).reduce((acc, [key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            acc[key] = String(value)
          }
          return acc
        }, {} as Record<string, string>))
      })

      const response = await fetch(`${endpoint}?${queryParams}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      
      // Validar respuesta con schema
      const validatedItems = Array.isArray(data.items) 
        ? data.items.map(item => schema.parse(item))
        : []

      updateState({
        items: validatedItems,
        loading: false,
        pagination: {
          page: data.page || 1,
          perPage: data.per_page || defaultPerPage,
          total: data.total || 0,
          pages: data.pages || 0
        }
      })

      handleSuccess('fetch', { items: validatedItems, total: data.total })
    } catch (error) {
      handleError(error instanceof Error ? error.message : 'Error fetching items')
      updateState({ loading: false })
    }
  }, [endpoint, schema, defaultPerPage, state.pagination.page, state.pagination.perPage, updateState, handleSuccess, handleError])

  const createItem = useCallback(async (item: Partial<T>): Promise<T | null> => {
    try {
      updateState({ loading: true, error: null })
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const createdItem = await response.json()
      const validatedItem = schema.parse(createdItem)
      
      updateState(prev => ({
        items: [...prev.items, validatedItem],
        loading: false
      }))

      handleSuccess('create', validatedItem)
      return validatedItem
    } catch (error) {
      handleError(error instanceof Error ? error.message : 'Error creating item')
      updateState({ loading: false })
      return null
    }
  }, [endpoint, schema, updateState, handleSuccess, handleError])

  const updateItem = useCallback(async (id: string, item: Partial<T>): Promise<T | null> => {
    try {
      updateState({ loading: true, error: null })
      
      const response = await fetch(`${endpoint}/${id}`, {
        method: 'PUT' ,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const updatedItem = await response.json()
      const validatedItem = schema.parse(updatedItem)
      
      updateState(prev => ({
        items: prev.items.map(i => 
          (i as any).id === id ? validatedItem : i
        ),
        loading: false
      }))

      handleSuccess('update', validatedItem)
      return validatedItem
    } catch (error) {
      handleError(error instanceof Error ? error.message : 'Error updating item')
      updateState({ loading: false })
      return null
    }
  }, [endpoint, schema, updateState, handleSuccess, handleError])

  const deleteItem = useCallback(async (id: string): Promise<boolean> => {
    try {
      updateState({ loading: true, error: null })
      
      const response = await fetch(`${endpoint}/${id}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      updateState(prev => ({
        items: prev.items.filter(i => (i as any).id !== id),
        loading: false
      }))

      handleSuccess('delete', { id })
      return true
    } catch (error) {
      handleError(error instanceof Error ? error.message : 'Error deleting item')
      updateState({ loading: false })
      return false
    }
  }, [endpoint, updateState, handleSuccess, handleError])

  const refreshItems = useCallback(async () => {
    await fetchItems()
  }, [fetchItems])

  const setItems = useCallback((items: T[]) => {
    updateState({ items })
  }, [updateState])

  const setError = useCallback((error: string | null) => {
    updateState({ error })
  }, [updateState])

  // Cargar datos iniciales
  useEffect(() => {
    fetchItems()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    ...state,
    fetchItems,
    createItem,
    updateItem,
    deleteItem,
    refreshItems,
    setItems,
    setError
  }
}
