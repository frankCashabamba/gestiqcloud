/**
 * Enhanced CRUD hook for catalog entities using centralized types
 * This combines useCRUD, usePagination, and useAsyncState for complete catalog management
 */

import { useState, useCallback, useEffect } from 'react'
import type {
  UUID,
  CatalogFilters,
  CatalogCreateRequest,
  CatalogUpdateRequest,
  PaginatedResponse
} from '@packages/api-types'

// Import existing hooks
import { usePagination } from './usePagination'
import { useAsyncState } from './useAsyncState'

export interface UseCatalogCRUDOptions<T> {
  // API functions
  list: (tenantId: string, filters: CatalogFilters) => Promise<PaginatedResponse<T>>
  get: (tenantId: string, id: UUID) => Promise<T>
  create: (tenantId: string, data: CatalogCreateRequest) => Promise<T>
  update: (tenantId: string, id: UUID, data: CatalogUpdateRequest) => Promise<T>
  delete: (tenantId: string, id: UUID) => Promise<void>

  // Configuration
  tenantId: string
  initialFilters?: CatalogFilters
  autoLoad?: boolean
}

export interface UseCatalogCRUDResult<T> {
  // Data
  items: T[]
  selectedItem: T | null
  loading: boolean
  error: string | null

  // Pagination
  pagination: {
    page: number
    perPage: number
    total: number
    pages: number
  }

  // Actions
  loadItems: (filters?: CatalogFilters) => Promise<void>
  loadItem: (id: UUID) => Promise<void>
  createItem: (data: CatalogCreateRequest) => Promise<T>
  updateItem: (id: UUID, data: CatalogUpdateRequest) => Promise<T>
  deleteItem: (id: UUID) => Promise<void>

  // Pagination actions
  setPage: (page: number) => void
  setPerPage: (perPage: number) => void
  nextPage: () => void
  prevPage: () => void
  firstPage: () => void
  lastPage: () => void

  // UI state
  isCreating: boolean
  isUpdating: boolean
  isDeleting: boolean

  // Utility
  refresh: () => Promise<void>
  clearSelection: () => void
  setFilters: (filters: CatalogFilters) => void
}

export function useCatalogCRUD<T extends { id: UUID }>(
  options: UseCatalogCRUDOptions<T>
): UseCatalogCRUDResult<T> {
  const {
    list,
    get,
    create,
    update,
    delete: deleteItem,
    tenantId,
    initialFilters = {},
    autoLoad = true
  } = options

  // State
  const [items, setItems] = useState<T[]>([])
  const [selectedItem, setSelectedItem] = useState<T | null>(null)
  const [filters, setFilters] = useState<CatalogFilters>(initialFilters)

  // Pagination
  const pagination = usePagination({
    initialPage: initialFilters.page || 1,
    initialPerPage: initialFilters.per_page || 20
  })

  // Async states
  const loadingState = useAsyncState()
  const createState = useAsyncState()
  const updateState = useAsyncState()
  const deleteState = useAsyncState()

  // Load items
  const loadItems = useCallback(async (newFilters?: CatalogFilters) => {
    const finalFilters = { ...filters, ...newFilters }
    setFilters(finalFilters)

    loadingState.setLoading(true)
    try {
      const response = await list(tenantId, {
        ...finalFilters,
        page: pagination.page,
        per_page: pagination.perPage
      })

      setItems(response.items)
      pagination.setTotal(response.total)
      pagination.setPage(response.page)
      pagination.setPerPage(response.per_page)

      loadingState.setLoading(false)
    } catch (error) {
      loadingState.setError(error instanceof Error ? error.message : 'Failed to load items')
    }
  }, [tenantId, filters, list, pagination])

  // Load single item
  const loadItem = useCallback(async (id: UUID) => {
    loadingState.setLoading(true)
    try {
      const item = await get(tenantId, id)
      setSelectedItem(item)
      loadingState.setLoading(false)
      return item
    } catch (error) {
      loadingState.setError(error instanceof Error ? error.message : 'Failed to load item')
      throw error
    }
  }, [tenantId, get])

  // Create item
  const createItem = useCallback(async (data: CatalogCreateRequest) => {
    createState.setLoading(true)
    try {
      const newItem = await create(tenantId, data)
      setItems(prev => [...prev, newItem])
      createState.setLoading(false)
      return newItem
    } catch (error) {
      createState.setError(error instanceof Error ? error.message : 'Failed to create item')
      throw error
    }
  }, [tenantId, create])

  // Update item
  const updateItem = useCallback(async (id: UUID, data: CatalogUpdateRequest) => {
    updateState.setLoading(true)
    try {
      const updatedItem = await update(tenantId, id, data)
      setItems(prev => prev.map(item =>
        item.id === id ? updatedItem : item
      ))
      setSelectedItem(updatedItem)
      updateState.setLoading(false)
      return updatedItem
    } catch (error) {
      updateState.setError(error instanceof Error ? error.message : 'Failed to update item')
      throw error
    }
  }, [tenantId, update])

  // Delete item
  const deleteItemCallback = useCallback(async (id: UUID) => {
    deleteState.setLoading(true)
    try {
      await deleteItem(tenantId, id)
      setItems(prev => prev.filter(item => item.id !== id))
      if (selectedItem?.id === id) {
        setSelectedItem(null)
      }
      deleteState.setLoading(false)
    } catch (error) {
      deleteState.setError(error instanceof Error ? error.message : 'Failed to delete item')
      throw error
    }
  }, [tenantId, deleteItem, selectedItem])

  // Refresh
  const refresh = useCallback(async () => {
    await loadItems()
  }, [loadItems])

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedItem(null)
  }, [])

  // Auto-load on mount
  useEffect(() => {
    if (autoLoad) {
      loadItems()
    }
  }, [autoLoad, loadItems])

  // Update pagination when filters change
  useEffect(() => {
    if (filters.page !== pagination.page) {
      pagination.setPage(filters.page || 1)
    }
    if (filters.per_page !== pagination.perPage) {
      pagination.setPerPage(filters.per_page || 20)
    }
  }, [filters, pagination])

  return {
    // Data
    items,
    selectedItem,
    loading: loadingState.loading,
    error: loadingState.error || createState.error || updateState.error || deleteState.error,

    // Pagination
    pagination: {
      page: pagination.page,
      perPage: pagination.perPage,
      total: pagination.total,
      pages: pagination.pages
    },

    // Actions
    loadItems,
    loadItem,
    createItem,
    updateItem,
    deleteItem: deleteItemCallback,

    // Pagination actions
    setPage: pagination.setPage,
    setPerPage: pagination.setPerPage,
    nextPage: pagination.nextPage,
    prevPage: pagination.prevPage,
    firstPage: pagination.firstPage,
    lastPage: pagination.lastPage,

    // UI state
    isCreating: createState.loading,
    isUpdating: updateState.loading,
    isDeleting: deleteState.loading,

    // Utility
    refresh,
    clearSelection,
    setFilters
  }
}

// Example usage:
/*
import { useCatalogCRUD } from '@packages/ui-hooks'
import { listBusinessTypes, getBusinessType, createBusinessType, updateBusinessType, deleteBusinessType } from '../services/catalogs'
import type { BusinessType } from '@packages/api-types'

function BusinessTypesPage() {
  const catalog = useCatalogCRUD<BusinessType>({
    list: listBusinessTypes,
    get: getBusinessType,
    create: createBusinessType,
    update: updateBusinessType,
    delete: deleteBusinessType,
    tenantId: 'tenant-123',
    initialFilters: { is_active: true }
  })

  if (catalog.loading) return <div>Loading...</div>
  if (catalog.error) return <div>Error: {catalog.error}</div>

  return (
    <div>
      <button onClick={() => catalog.loadItems()}>Refresh</button>
      <button onClick={() => catalog.setFilters({ search: 'test' })}>Search</button>

      <ul>
        {catalog.items.map(item => (
          <li key={item.id}>
            {item.name}
            <button onClick={() => catalog.loadItem(item.id)}>Edit</button>
            <button onClick={() => catalog.deleteItem(item.id)}>Delete</button>
          </li>
        ))}
      </ul>

      <PaginationControls pagination={catalog.pagination} />
    </div>
  )
}
*/
