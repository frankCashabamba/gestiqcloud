/**
 * useBusinessCategories Hook
 *
 * Hook React para cargar y cachear categorías de negocio desde BD.
 * Reemplaza datos hardcodeados en componentes.
 *
 * Uso:
 * ```tsx
 * const { categories, loading, error } = useBusinessCategories()
 *
 * if (loading) return <div>Cargando...</div>
 * if (error) return <div>Error: {error}</div>
 *
 * return (
 *   <select>
 *     {categories.map(cat => (
 *       <option key={cat.code} value={cat.code}>{cat.name}</option>
 *     ))}
 *   </select>
 * )
 * ```
 */

import { useEffect, useState } from 'react'
import {
  BusinessCategory,
  getBusinessCategories,
} from '../services/businessCategoriesApi'

interface UseBusinessCategoriesState {
  categories: BusinessCategory[]
  loading: boolean
  error: string | null
}

// Cache para evitar múltiples requests
const categoryCache: {
  data: BusinessCategory[] | null
  timestamp: number | null
} = {
  data: null,
  timestamp: null,
}

const CACHE_TTL = 5 * 60 * 1000 // 5 minutos

/**
 * Hook que carga categorías de negocio desde API.
 *
 * Soporta:
 * - Caching automático (5 minutos)
 * - Manejo de errores
 * - Loading state
 *
 * @returns {UseBusinessCategoriesState} Estado del hook
 */
export function useBusinessCategories(): UseBusinessCategoriesState {
  const [state, setState] = useState<UseBusinessCategoriesState>({
    categories: [],
    loading: true,
    error: null,
  })

  useEffect(() => {
    const loadCategories = async () => {
      // Verificar cache
      const now = Date.now()
      if (
        categoryCache.data &&
        categoryCache.timestamp &&
        now - categoryCache.timestamp < CACHE_TTL
      ) {
        setState({
          categories: categoryCache.data,
          loading: false,
          error: null,
        })
        return
      }

      // Cargar desde API
      setState(prev => ({ ...prev, loading: true }))

      try {
        const categories = await getBusinessCategories()

        // Guardar en cache
        categoryCache.data = categories
        categoryCache.timestamp = Date.now()

        setState({
          categories,
          loading: false,
          error: null,
        })
      } catch (err: any) {
        const errorMessage =
          err?.message || 'Error cargando categorías de negocio'

        console.error('[useBusinessCategories]', errorMessage)

        setState({
          categories: [],
          loading: false,
          error: errorMessage,
        })
      }
    }

    loadCategories()
  }, [])

  return state
}

/**
 * Hook alternativo para cargar una categoría específica
 */
export function useBusinessCategoryByCode(code: string | null | undefined) {
  const [category, setCategory] = useState<BusinessCategory | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!code) {
      setCategory(null)
      return
    }

    const loadCategory = async () => {
      setLoading(true)
      setError(null)

      try {
        const { getByCode } = await import(
          '../services/businessCategoriesApi'
        )
        const result = await getByCode(code)

        setCategory(result)
      } catch (err: any) {
        setError(err?.message || 'Error cargando categoría')
      } finally {
        setLoading(false)
      }
    }

    loadCategory()
  }, [code])

  return { category, loading, error }
}

/**
 * Limpiar cache manualmente (si es necesario)
 */
export function clearBusinessCategoriesCache() {
  categoryCache.data = null
  categoryCache.timestamp = null
}
