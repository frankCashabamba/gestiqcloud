/**
 * Advanced CRUD hook for catalog entities with bulk operations and optimistic updates
 * This extends useCatalogCRUD with additional enterprise features
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type {
  UUID,
  CatalogCreateRequest,
  CatalogUpdateRequest,
  PaginatedResponse
} from '@packages/api-types'

// Import existing hooks
import { usePagination } from './usePagination'
import { useAsyncState } from './useAsyncState'

export interface UseAdvancedCatalogCRUDOptions<T> {
  // API functions
  list: (tenantId: string, filters: any) => Promise<PaginatedResponse<T>>
  get: (tenantId: string, id: UUID) => Promise<T>
  create: (tenantId: string, data: CatalogCreateRequest) => Promise<T>
  update: (tenantId: string, id: UUID, data: CatalogUpdateRequest) => Promise<T>
  delete: (tenantId: string, id: UUID) => Promise<void>

  // Bulk operations
  bulkCreate?: (tenantId: string, items: CatalogCreateRequest[]) => Promise<T[]>
  bulkUpdate?: (tenantId: string, updates: { id: UUID; data: CatalogUpdateRequest }[]) => Promise<T[]>
  bulkDelete?: (tenantId: string, ids: UUID[]) => Promise<void>

  // Configuration
  tenantId: string
  initialFilters?: any
  autoLoad?: boolean
  enableOptimisticUpdates?: boolean
  cacheTimeout?: number
}

export interface UseAdvancedCatalogCRUDResult<T> {
  // Basic CRUD (inherited from useCatalogCRUD)
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

  // Basic actions
  loadItems: (filters?: any) => Promise<void>
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

  // Advanced features
  bulkCreate: (items: CatalogCreateRequest[]) => Promise<T[]>
  bulkUpdate: (updates: { id: UUID; data: CatalogUpdateRequest }[]) => Promise<T[]>
  bulkDelete: (ids: UUID[]) => Promise<void>

  // Optimistic updates
  optimisticCreate: (data: CatalogCreateRequest) => T
  optimisticUpdate: (id: UUID, data: CatalogUpdateRequest) => T
  optimisticDelete: (id: UUID) => void
  rollbackOptimistic: (id: UUID) => void

  // Caching
  clearCache: () => void
  refreshCache: () => Promise<void>

  // Utility
  refresh: () => Promise<void>
  clearSelection: () => void
  setFilters: (filters: any) => void

  // Selection
  selectedItems: T[]
  toggleSelection: (id: UUID) => void
  selectAll: () => void
  clearSelection: () => void
  deleteSelected: () => Promise<void>
}

export function useAdvancedCatalogCRUD<T extends { id: UUID }>(
  options: UseAdvancedCatalogCRUDOptions<T>
): UseAdvancedCatalogCRUDResult<T> {
  const {
    list,
    get,
    create,
    update,
    delete: deleteItem,
    bulkCreate,
    bulkUpdate,
    bulkDelete,
    tenantId,
    initialFilters = {},
    autoLoad = true,
    enableOptimisticUpdates = false,
    cacheTimeout = 300000 // 5 minutes
  } = options

  // State
  const [items, setItems] = useState<T[]>([])
  const [selectedItem, setSelectedItem] = useState<T | null>(null)
  const [selectedItems, setSelectedItems] = useState<T[]>([])
  const [filters, setFilters] = useState(initialFilters)
  const [optimisticUpdates, setOptimisticUpdates] = useState<Map<UUID, T>>(new Map())

  // Cache
  const cacheRef = useRef<Map<string, { data: PaginatedResponse<T>; timestamp: number }>>(new Map())

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
  const bulkState = useAsyncState()

  // Cache helpers
  const getCacheKey = useCallback((filters: any) => {
    return JSON.stringify({ tenantId, filters, page: pagination.page, perPage: pagination.perPage })
  }, [tenantId, pagination.page, pagination.perPage])

  const isCacheValid = useCallback((timestamp: number) => {
    return Date.now() - timestamp < cacheTimeout
  }, [cacheTimeout])

  const getCachedData = useCallback((filters: any) => {
    const key = getCacheKey(filters)
    const cached = cacheRef.current.get(key)
    if (cached && isCacheValid(cached.timestamp)) {
      return cached.data
    }
    return null
  }, [getCacheKey, isCacheValid])

  const setCachedData = useCallback((filters: any, data: PaginatedResponse<T>) => {
    const key = getCacheKey(filters)
    cacheRef.current.set(key, {
      data,
      timestamp: Date.now()
    })
  }, [getCacheKey])

  // Optimistic update helpers
  const createOptimisticItem = useCallback((data: CatalogCreateRequest): T => {
    const optimisticId = crypto.randomUUID() as UUID
    const optimisticItem: T = {
      id: optimisticId,
      tenant_id: tenantId,
      name: data.name || '',
      code: data.code,
      description: data.description,
      is_active: data.is_active ?? true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      ...data
    } as T

    setOptimisticUpdates(prev => new Map(prev).set(optimisticId, optimisticItem))
    setItems(prev => [...prev, optimisticItem])

    return optimisticItem
  }, [tenantId])

  const updateOptimisticItem = useCallback((id: UUID, data: CatalogUpdateRequest): T => {
    const existingItem = items.find(item => item.id === id)
    if (!existingItem) return existingItem as T

    const optimisticItem: T = {
      ...existingItem,
      ...data,
      updated_at: new Date().toISOString()
    } as T

    setOptimisticUpdates(prev => new Map(prev).set(id, optimisticItem))
    setItems(prev => prev.map(item =>
      item.id === id ? optimisticItem : item
    ))

    return optimisticItem
  }, [items])

  const deleteOptimisticItem = useCallback((id: UUID) => {
    setOptimisticUpdates(prev => {
      const newMap = new Map(prev)
      newMap.delete(id)
      return newMap
    })
    setItems(prev => prev.filter(item => item.id !== id))

    if (selectedItem?.id === id) {
      setSelectedItem(null)
    }
    setSelectedItems(prev => prev.filter(item => item.id !== id))
  }, [selectedItem])

  const rollbackOptimisticUpdate = useCallback((id: UUID) => {
    setOptimisticUpdates(prev => {
      const newMap = new Map(prev)
      newMap.delete(id)
      return newMap
    })
    // Note: In a real implementation, you would reload the data from server
    // For this example, we'll just trigger a refresh
    setTimeout(() => {
      loadItems()
    }, 100)
  }, [])

  // Load items with caching
  const loadItems = useCallback(async (newFilters?: any) => {
    const finalFilters = { ...filters, ...newFilters }
    setFilters(finalFilters)

    // Check cache first
    const cachedData = getCachedData(finalFilters)
    if (cachedData) {
      setItems(cachedData.items)
      pagination.setTotal(cachedData.total)
      pagination.setPage(cachedData.page)
      pagination.setPerPage(cachedData.per_page)
      return
    }

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

      // Cache the response
      setCachedData(finalFilters, response)

      loadingState.setLoading(false)
    } catch (error) {
      loadingState.setError(error instanceof Error ? error.message : 'Failed to load items')
    }
  }, [tenantId, filters, list, pagination, getCachedData, setCachedData])

  // Basic CRUD operations
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

  const deleteItemCallback = useCallback(async (id: UUID) => {
    deleteState.setLoading(true)
    try {
      await deleteItem(tenantId, id)
      setItems(prev => prev.filter(item => item.id !== id))
      if (selectedItem?.id === id) {
        setSelectedItem(null)
      }
      if (selectedItems.some(item => item.id === id)) {
        setSelectedItems(prev => prev.filter(item => item.id !== id))
      }
      deleteState.setLoading(false)
    } catch (error) {
      deleteState.setError(error instanceof Error ? error.message : 'Failed to delete item')
      throw error
    }
  }, [tenantId, deleteItem, selectedItem, selectedItems])

  // Bulk operations
  const bulkCreateItems = useCallback(async (itemsToCreate: CatalogCreateRequest[]) => {
    if (!bulkCreate) {
      throw new Error('Bulk create not supported')
    }

    bulkState.setLoading(true)
    try {
      const newItems = await bulkCreate(tenantId, itemsToCreate)
      setItems(prev => [...prev, ...newItems])
      bulkState.setLoading(false)
      return newItems
    } catch (error) {
      bulkState.setError(error instanceof Error ? error.message : 'Failed to bulk create items')
      throw error
    }
  }, [tenantId, bulkCreate])

  const bulkUpdateItems = useCallback(async (updates: { id: UUID; data: CatalogUpdateRequest }[]) => {
    if (!bulkUpdate) {
      throw new Error('Bulk update not supported')
    }

    bulkState.setLoading(true)
    try {
      const updatedItems = await bulkUpdate(tenantId, updates)
      setItems(prev => prev.map(item => {
        const update = updates.find(u => u.id === item.id)
        return update ? { ...item, ...update.data } as T : item
      }))
      bulkState.setLoading(false)
      return updatedItems
    } catch (error) {
      bulkState.setError(error instanceof Error ? error.message : 'Failed to bulk update items')
      throw error
    }
  }, [tenantId, bulkUpdate])

  const bulkDeleteItems = useCallback(async (ids: UUID[]) => {
    if (!bulkDelete) {
      throw new Error('Bulk delete not supported')
    }

    bulkState.setLoading(true)
    try {
      await bulkDelete(tenantId, ids)
      setItems(prev => prev.filter(item => !ids.includes(item.id)))
      setSelectedItems(prev => prev.filter(item => !ids.includes(item.id)))
      if (selectedItem && ids.includes(selectedItem.id)) {
        setSelectedItem(null)
      }
      bulkState.setLoading(false)
    } catch (error) {
      bulkState.setError(error instanceof Error ? error.message : 'Failed to bulk delete items')
      throw error
    }
  }, [tenantId, bulkDelete, selectedItem])

  // Selection management
  const toggleSelection = useCallback((id: UUID) => {
    setSelectedItems(prev => {
      const isSelected = prev.some(item => item.id === id)
      if (isSelected) {
        return prev.filter(item => item.id !== id)
      } else {
        const item = items.find(i => i.id === id)
        return item ? [...prev, item] : prev
      }
    })
  }, [items])

  const selectAll = useCallback(() => {
    setSelectedItems(items)
  }, [items])

  const deleteSelected = useCallback(async () => {
    if (selectedItems.length === 0) return

    try {
      if (bulkDelete) {
        await bulkDeleteItems(selectedItems.map(item => item.id))
      } else {
        // Fallback to individual deletes
        await Promise.all(selectedItems.map(item => deleteItemCallback(item.id)))
      }
    } catch (error) {
      console.error('Failed to delete selected items:', error)
    }
  }, [selectedItems, bulkDelete, bulkDeleteItems, deleteItemCallback])

  // Cache management
  const clearCache = useCallback(() => {
    cacheRef.current.clear()
  }, [])

  const refreshCache = useCallback(async () => {
    clearCache()
    await loadItems()
  }, [clearCache, loadItems])

  // Utility
  const refresh = useCallback(async () => {
    await loadItems()
  }, [loadItems])

  const clearSelection = useCallback(() => {
    setSelectedItem(null)
    setSelectedItems([])
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
    selectedItems,
    loading: loadingState.loading || bulkState.loading,
    error: loadingState.error || createState.error || updateState.error || deleteState.error || bulkState.error,

    // Pagination
    pagination: {
      page: pagination.page,
      perPage: pagination.perPage,
      total: pagination.total,
      pages: pagination.pages
    },

    // Basic actions
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

    // Advanced features
    bulkCreate: bulkCreateItems,
    bulkUpdate: bulkUpdateItems,
    bulkDelete: bulkDeleteItems,

    // Optimistic updates
    optimisticCreate: enableOptimisticUpdates ? createOptimisticItem : undefined,
    optimisticUpdate: enableOptimisticUpdates ? updateOptimisticItem : undefined,
    optimisticDelete: enableOptimisticUpdates ? deleteOptimisticItem : undefined,
    rollbackOptimistic: enableOptimisticUpdates ? rollbackOptimisticUpdate : undefined,

    // Caching
    clearCache,
    refreshCache,

    // Utility
    refresh,
    clearSelection,
    setFilters,

    // Selection
    toggleSelection,
    selectAll,
    deleteSelected
  }
}

// Example usage:
/*
import { useAdvancedCatalogCRUD } from '@packages/ui-hooks'
import { listBusinessTypes, getBusinessType, createBusinessType, updateBusinessType, deleteBusinessType, bulkCreateBusinessTypes } from '../services/businessTypes'
import type { BusinessType } from '@packages/api-types'

function AdvancedBusinessTypesPage() {
  const catalog = useAdvancedCatalogCRUD<BusinessType>({
    list: listBusinessTypes,
    get: getBusinessType,
    create: createBusinessType,
    update: updateBusinessType,
    delete: deleteBusinessType,
    bulkCreate: bulkCreateBusinessTypes,
    tenantId: 'tenant-123',
    initialFilters: { is_active: true },
    enableOptimisticUpdates: true,
    cacheTimeout: 600000 // 10 minutes
  })

  const handleBulkCreate = async () => {
    const newTypes = [
      { name: 'Type A', code: 'TYPE_A' },
      { name: 'Type B', code: 'TYPE_B' },
      { name: 'Type C', code: 'TYPE_C' }
    ]

    try {
      await catalog.bulkCreate(newTypes)
      console.log('Bulk created successfully')
    } catch (error) {
      console.error('Bulk create failed:', error)
    }
  }

  const handleOptimisticCreate = () => {
    const newType = catalog.optimisticCreate({ name: 'New Type', code: 'NEW_TYPE' })
    console.log('Optimistic item created:', newType)
    // Later, you can rollback with: catalog.rollbackOptimistic(newType.id)
  }

  const handleDeleteSelected = async () => {
    try {
      await catalog.deleteSelected()
      console.log('Selected items deleted')
    } catch (error) {
      console.error('Failed to delete selected:', error)
    }
  }

  return (
    <div>
      <button onClick={() => catalog.loadItems()}>Refresh</button>
      <button onClick={handleBulkCreate}>Bulk Create</button>
      <button onClick={handleOptimisticCreate}>Optimistic Create</button>
      <button onClick={() => catalog.clearCache()}>Clear Cache</button>

      <div>
        <h3>Items ({catalog.items.length})</h3>
        <div>
          <input
            type="checkbox"
            onChange={catalog.selectAll}
            checked={catalog.selectedItems.length === catalog.items.length}
          />
          Select All ({catalog.selectedItems.length} selected)
        </div>

        <ul>
          {catalog.items.map(item => (
            <li key={item.id}>
              <input
                type="checkbox"
                checked={catalog.selectedItems.some(selected => selected.id === item.id)}
                onChange={() => catalog.toggleSelection(item.id)}
              />
              {item.name}
              <button onClick={() => catalog.loadItem(item.id)}>Edit</button>
              <button onClick={() => catalog.deleteItem(item.id)}>Delete</button>
            </li>
          ))}
        </ul>

        {catalog.selectedItems.length > 0 && (
          <button onClick={handleDeleteSelected}>
            Delete Selected ({catalog.selectedItems.length})
          </button>
        )}
      </div>

      <PaginationControls pagination={catalog.pagination} />
    </div>
  )
}
*/
