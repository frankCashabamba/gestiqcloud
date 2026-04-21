/**
 * UI Hooks - Hooks genéricos reutilizables para gestión de estado y CRUD
 */

export { useCRUD } from './useCRUD'
export { useSimpleFetch } from './useSimpleFetch'
export { useSimpleList } from './useSimpleList'
export { usePagination } from './usePagination'
export { useFilters } from './useFilters'
export { useAsyncState } from './useAsyncState'
export { useDebounce } from './useDebounce'

export type { CRUDState, CRUDActions } from './useCRUD'
export type { PaginationState, PaginationActions } from './usePagination'
export type { FilterState, FilterActions } from './useFilters'
export type { AsyncState } from './useAsyncState'
