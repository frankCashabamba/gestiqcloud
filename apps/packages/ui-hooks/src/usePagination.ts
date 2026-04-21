/**
 * Hook genérico para manejo de paginación
 */
import { useState, useCallback } from 'react'

export interface PaginationState {
  page: number
  perPage: number
  total: number
  pages: number
}

export interface PaginationActions {
  setPage: (page: number) => void
  setPerPage: (perPage: number) => void
  nextPage: () => void
  prevPage: () => void
  firstPage: () => void
  lastPage: () => void
  goToPage: (page: number) => void
  setTotal: (total: number) => void
}

export interface UsePaginationConfig {
  initialPage?: number
  initialPerPage?: number
  total?: number
}

export function usePagination(config: UsePaginationConfig = {}): PaginationState & PaginationActions {
  const { initialPage = 1, initialPerPage = 20, total: initialTotal = 0 } = config

  const [state, setState] = useState<PaginationState>({
    page: initialPage,
    perPage: initialPerPage,
    total: initialTotal,
    pages: Math.ceil(initialTotal / initialPerPage) || 1
  })

  const setPage = useCallback((page: number) => {
    setState(prev => ({ ...prev, page: Math.max(1, Math.min(page, prev.pages)) }))
  }, [])

  const setPerPage = useCallback((perPage: number) => {
    setState(prev => {
      const newPerPage = Math.max(1, perPage)
      const newPages = Math.ceil(prev.total / newPerPage) || 1
      const newPage = Math.min(prev.page, newPages)
      return { ...prev, perPage: newPerPage, pages: newPages, page: newPage }
    })
  }, [])

  const nextPage = useCallback(() => {
    setPage(state.page + 1)
  }, [state.page, setPage])

  const prevPage = useCallback(() => {
    setPage(state.page - 1)
  }, [state.page, setPage])

  const firstPage = useCallback(() => {
    setPage(1)
  }, [setPage])

  const lastPage = useCallback(() => {
    setPage(state.pages)
  }, [state.pages, setPage])

  const goToPage = useCallback((page: number) => {
    setPage(page)
  }, [setPage])

  const setTotal = useCallback((total: number) => {
    setState(prev => {
      const newPages = Math.ceil(total / prev.perPage) || 1
      const newPage = Math.min(prev.page, newPages)
      return { ...prev, total, pages: newPages, page: newPage }
    })
  }, [])

  return {
    ...state,
    setPage,
    setPerPage,
    nextPage,
    prevPage,
    firstPage,
    lastPage,
    goToPage,
    setTotal
  }
}
